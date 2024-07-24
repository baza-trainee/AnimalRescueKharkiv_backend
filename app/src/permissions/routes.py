import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, List

import uvicorn
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.permissions.repository import permissions_repository
from src.permissions.schemas import PermissionResponse

if TYPE_CHECKING:
    from src.permissions.models import Permission

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.permissions_prefix, tags=["permissions"])

@router.get("/{access_right}", response_model=PermissionResponse)
async def read_permission(access_right: str,
                        db: AsyncSession = Depends(get_db),
                    ) -> PermissionResponse:
    """Retrieves permission by its access right name. Returns PermissionResponse"""
    persmission: Permission = await permissions_repository.read_permission(access_right=access_right, db=db)
    if persmission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return persmission

@router.get("/",  response_model=List[PermissionResponse])
async def read_permissions(db: AsyncSession = Depends(get_db)) -> List[PermissionResponse]:
    """Retrieves all permissions. Returns list of permission objects"""
    permissions: List[PermissionResponse] = await permissions_repository.read_permissions(db=db)
    if not permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No permissions found")
    return permissions


@router.post("/", response_model=List[PermissionResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_permissions(access_rights: List[str],
                        db: AsyncSession = Depends(get_db),
                    ) -> List[PermissionResponse]:
    """Creates new permissions based on list of passed access right names. Returns list of created permission objects"""
    permissions: List[PermissionResponse] = []
    try:
        permissions = [
                        permission
                        for access_right in access_rights
                        if (permission := await permissions_repository
                            .create_permission(access_right=access_right, db=db))
                        is not None
                    ]
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    return permissions


@router.delete("/{access_right}", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def remove_media_asset(access_rights: List[str],
                        db: AsyncSession = Depends(get_db),
                    ) -> None:
    """Deletes a permissions based on list of passed access right names"""
    permissions_to_delete = [
                        permission
                        for access_right in access_rights
                        if (permission := await permissions_repository
                            .read_permission(access_right=access_right, db=db))
                        is not None
                    ]
    if not permissions_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permissions not found")
    for permission_to_delete in permissions_to_delete:
        await permissions_repository.remove_permission(permission=permission_to_delete, db=db)
