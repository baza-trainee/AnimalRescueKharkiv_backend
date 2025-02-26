import logging
from typing import TYPE_CHECKING, Dict, List

import uvicorn
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.encoders import jsonable_encoder
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.authorization.service import authorization_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.permissions.models import Permission
from src.permissions.repository import permissions_repository
from src.roles.repository import roles_repository
from src.roles.schemas import RoleBase, RoleResponse, RoleUpdate
from src.services.cache import Cache
from src.users.models import User

if TYPE_CHECKING:
    from src.permissions.schemas import PermissionBase
    from src.roles.models import Role

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.roles_prefix, tags=["roles"])
roles_router_cache: Cache = Cache(owner=router, all_prefix="roles", ttl=settings.default_cache_ttl)


@router.get("/",  response_model=List[RoleResponse],
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_roles(name: str = Query(default=None),
                           domain: str = Query(default=None),
                           _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["system:admin"]),
                           db: AsyncSession = Depends(get_db)) -> List[RoleResponse]:
    """Retrieves all roles with optional filtering. Returns list of role objects"""
    cache_key = roles_router_cache.get_all_records_cache_key_with_params(
        name,
        domain,
    )
    roles: List[RoleResponse] = await roles_router_cache.get(key=cache_key)
    if not roles:
        roles = await roles_repository.read_roles(
                                                            name=name,
                                                            domain=domain,
                                                            db=db)
        roles = [RoleResponse.model_validate(role) for role in roles]
        if roles:
            await roles_router_cache.set(key=cache_key, value=roles)
    if not roles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.role_not_found)
    return roles


@router.get("/{domain}",  response_model=List[RoleResponse],
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_domain_roles(domain: str,
                           name: str = Query(default=None),
                           _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["security:administer"]),
                           db: AsyncSession = Depends(get_db)) -> List[RoleResponse]:
    """Retrieves all roles with optional filtering. Returns list of role objects"""
    cache_key = roles_router_cache.get_all_records_cache_key_with_params(
        name,
        domain,
    )
    roles: List[RoleResponse] = await roles_router_cache.get(key=cache_key)
    if not roles:
        roles = await roles_repository.read_roles(
                                                            name=name,
                                                            domain=domain,
                                                            db=db)
        roles = [RoleResponse.model_validate(role) for role in roles]
        if roles:
            await roles_router_cache.set(key=cache_key, value=roles)
    if not roles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.role_not_found)
    return roles


@router.post("/", response_model=List[RoleResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_roles(models: List[RoleBase],
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                            scopes=[settings.super_user_permission]),
                    ) -> List[RoleResponse]:
    """Creates new roles. Returns list of created role objects"""
    roles: List[Role] = []
    try:
        roles = [
                    role
                    for model in models
                    if (role := await roles_repository
                        .create_role(model=model, db=db))
                    is not None
                ]
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)
    await roles_router_cache.invalidate_all_keys()
    return roles


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def delete_roles(models: List[RoleBase],
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                            scopes=[settings.super_user_permission]),
                    ) -> None:
    """Deletes roles"""
    roles_to_delete = [
                    role
                    for model in models
                    if (role := await roles_repository
                        .read_role(model=model, db=db))
                    is not None
                    ]
    if not roles_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.role_not_found)
    for role_to_delete in roles_to_delete:
        await roles_repository.delete_role(role=role_to_delete, db=db)
    await roles_router_cache.invalidate_all_keys()


async def __validate_permissions(model: RoleUpdate, db: AsyncSession) -> Dict[str, List[Permission]]:
    invalid_permissions: Dict[str, List[PermissionBase]] = {}
    valid_permissions: Dict[str, List[Permission]] = {}
    if model.assign:
        assign: List[Permission] = await permissions_repository.read_permissions(models=model.assign, db=db)
        valid_permissions ["assign"] = assign
        invalid_permissions["assign"] = list(filter(lambda pm:
                       not list(filter(lambda p: p.entity == pm.entity and p.operation == pm.operation, assign))
                       , model.assign))
    if model.unassign:
        unassign: List[Permission] = await permissions_repository.read_permissions(models=model.unassign, db=db)
        valid_permissions ["unassign"] = unassign
        invalid_permissions["unassign"] = list(filter(lambda pm:
                       not list(filter(lambda p: p.entity == pm.entity and p.operation == pm.operation, unassign))
                       , model.unassign))

    if any(invalid_permissions.get(key) for key in ("assign", "unassign")):
        response: dict = {
            "Invalid permissions": invalid_permissions,
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=jsonable_encoder(response))
    return valid_permissions


@router.patch("/{domain}/{role_name}", response_model=RoleResponse, status_code=status.HTTP_200_OK,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def update_role(domain: str, role_name: str, body: RoleUpdate,
                                                          db: AsyncSession = Depends(get_db),
                            _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["security:administer"]),
                    ) -> RoleResponse:
    """Updates permissions for role. Returns updated role object"""
    role:RoleResponse = None

    try:
        role_model = RoleBase(name=role_name, domain=domain)
        role = await roles_repository.read_role(model=role_model, db=db)

        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.role_not_found)

        if body.title:
            role = await roles_repository.update_title(role=role, title=body.title, db=db)

        permissions: Dict[str, List[Permission]] = await __validate_permissions(model=body, db=db)

        if "assign" in permissions:
            for permission in permissions["assign"]:
                if permission:
                    role = await roles_repository.assign_permission(role=role, permission=permission, db=db)

        if "unassign" in permissions:
            for permission in permissions["unassign"]:
                if permission:
                    role = await roles_repository.unassign_permission(role=role, permission=permission, db=db)

    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)

    await roles_router_cache.invalidate_all_keys()
    return role
