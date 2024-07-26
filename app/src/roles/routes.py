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
from src.roles.repository import roles_repository
from src.roles.schemas import RoleBase, RoleResponse

if TYPE_CHECKING:
    from src.roles.models import Role

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.roles_prefix, tags=["roles"])


@router.get("/",  response_model=List[RoleResponse])
async def read_roles(name: str = Query(default=None),
                           domain: str = Query(default=None),
                           db: AsyncSession = Depends(get_db)) -> List[RoleResponse]:
    """Retrieves all roles with optional filtering. Returns list of role objects"""
    roles: List[RoleResponse] = await roles_repository.read_roles(
                                                            name=name,
                                                            domain=domain,
                                                            db=db)
    if not roles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No roles found")
    return roles


@router.post("/", response_model=List[RoleResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_roles(models: List[RoleBase],
                        db: AsyncSession = Depends(get_db),
                    ) -> List[RoleResponse]:
    """Creates new roles. Returns list of created role objects"""
    roles: List[RoleResponse] = []
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
    return roles


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def delete_role(models: List[RoleBase],
                        db: AsyncSession = Depends(get_db),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roles not found")
    for role_to_delete in roles_to_delete:
        await roles_repository.delete_role(role=role_to_delete, db=db)
