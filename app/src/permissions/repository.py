import logging
from typing import List

import uvicorn
from sqlalchemy import ColumnExpressionArgument, Select, and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.settings import settings
from src.permissions.models import Permission
from src.permissions.schemas import PermissionBase
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)


class PermissionsRepository (metaclass=SingletonMeta):
    async def create_permission(self, model: PermissionBase, db: AsyncSession) -> Permission:
        """Creates a permission definition. Returns the created permission definition"""
        permission = Permission(entity=model.entity.lower(), operation=model.operation.lower())
        if model.title:
            permission.title = model.title
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission

    async def read_permission(self, model: PermissionBase, db: AsyncSession) -> Permission | None:
        """Reads a permission by entity and operation. Returns the retrieved permission"""
        statement = select(Permission)
        statement = statement.filter_by(entity=model.entity.lower(), operation=model.operation.lower())
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def search_permissions(self,
                               entity:str,
                               operation:str,
                               db: AsyncSession,
                               *, has_title: bool = True,
                              ) -> list[Permission]:
        """Searches all permissions with optional filtering. Returns the retrieved collection of permissions"""
        statement = select(Permission)
        if entity:
            statement = statement.filter_by(entity=entity.lower())
        if operation:
            statement = statement.filter_by(operation=operation.lower())
        if has_title:
            statement = statement.filter(Permission.title != None) #noqa: E711
        result = await db.execute(statement)
        permissions = result.unique().scalars().all()
        return list(permissions)

    async def read_permissions(self,
                               models: List[PermissionBase],
                               db: AsyncSession,
                              ) -> list[Permission]:
        """Reads all permissions base on models. Returns the retrieved collection of permissions"""
        statement = select(Permission)
        expression: List[ColumnExpressionArgument[bool]] = []
        if models:
            expression = [and_(Permission.entity == model.entity, Permission.operation == model.operation)
                          for model in models]
        if expression:
            statement = statement.filter(or_(*expression))
        result = await db.execute(statement)
        permissions = result.unique().scalars().all()
        return list(permissions)

    async def remove_permission(self, permission: Permission, db: AsyncSession) -> Permission | None:
        """Deletes a permission from database. Returns the deleted permission"""
        if permission:
            await db.delete(permission)
            await db.commit()
        return permission

    async def update_title(self, permission: Permission, title:str, db: AsyncSession) -> Permission:
        """Updates title of the permission"""
        if permission and title:
            permission.title = title
            db.add(permission)
            await db.commit()
            await db.refresh(permission)
        return permission


permissions_repository:PermissionsRepository = PermissionsRepository()
