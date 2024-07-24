import base64
import io
import logging
import uuid
from datetime import datetime
from typing import BinaryIO

import uvicorn
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.settings import settings
from src.permissions.models import Permission
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)

class PermissionsRepository (metaclass=SingletonMeta):
    async def create_permission(self, access_right:str, db: AsyncSession) -> Permission:
        """Creates permission definition with passed access right name. Returns the created permission definition"""
        permission = Permission(access_right=access_right)
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission

    async def read_permission(self, access_right: str, db: AsyncSession) -> Permission | None:
        """Reads a permission by its access right name from database. Returns the retrieved permission"""
        statement = select(Permission)
        statement = statement.filter_by(access_right=access_right)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def read_permissions(self, db: AsyncSession) -> list[Permission]:
        """Reads all permissions from database. Returns the retrieved collection of permissions"""
        statement = select(Permission)
        result = await db.execute(statement)
        permissions = result.scalars().all()
        return list(permissions)

    async def remove_permission(self, permission: Permission, db: AsyncSession) -> Permission | None:
        """Deletes a permission by its access right name from database. Returns the deleted permission"""
        if permission:
            await db.delete(permission)
            await db.commit()
        return permission


permissions_repository:PermissionsRepository = PermissionsRepository()
