import logging
from typing import TYPE_CHECKING, List

import uvicorn
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.permissions.repository import permissions_repository
from src.permissions.schemas import PermissionBase, PermissionResponse
from src.services.cache import Cache

if TYPE_CHECKING:
    from src.permissions.models import Permission

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.permissions_prefix, tags=["permissions"])
permissions_router_cache: Cache = Cache(owner=router, all_prefix="permissions", ttl=settings.default_cache_ttl)

@router.get("/",  response_model=List[PermissionResponse])
async def read_permissions(entity: str = Query(default=None),
                           operation: str = Query(default=None),
                           db: AsyncSession = Depends(get_db)) -> List[PermissionResponse]:
    """Retrieves all permissions with optional filtering. Returns list of permission objects"""
    cache_key = permissions_router_cache.get_all_records_cache_key_with_params(
        entity,
        operation,
    )
    permissions: List[PermissionResponse] = await permissions_router_cache.get(key=cache_key)
    if not permissions:
        permissions = await permissions_repository.read_permissions(
                                                                            entity=entity,
                                                                            operation=operation,
                                                                            db=db)
        permission_responses = [PermissionResponse.model_validate(permission) for permission in permissions]
        await permissions_router_cache.set(key=cache_key, value=permission_responses)
    if not permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.perm_not_found)
    return permissions


@router.post("/", response_model=List[PermissionResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_permissions(models: List[PermissionBase],
                        db: AsyncSession = Depends(get_db),
                    ) -> List[PermissionResponse]:
    """Creates new permissions. Returns list of created permission objects"""
    permissions: List[PermissionResponse] = []
    try:
        permissions = [
                        permission
                        for model in models
                        if (permission := await permissions_repository
                            .create_permission(model=model, db=db))
                        is not None
                    ]
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)
    await permissions_router_cache.invalidate_all_keys()
    return permissions


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def remove_permissions(models: List[PermissionBase],
                        db: AsyncSession = Depends(get_db),
                    ) -> None:
    """Deletes permissions"""
    permissions_to_delete = [
                        permission
                        for model in models
                        if (permission := await permissions_repository
                            .read_permission(model=model, db=db))
                        is not None
                    ]
    if not permissions_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.perm_not_found)
    for permission_to_delete in permissions_to_delete:
        await permissions_repository.remove_permission(permission=permission_to_delete, db=db)
    await permissions_router_cache.invalidate_all_keys()
