import logging

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.settings import settings
from src.permissions.models import Permission
from src.roles.models import Role
from src.roles.schemas import RoleBase
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)


class RolesRepository (metaclass=SingletonMeta):
    async def create_role(self, model: RoleBase, db: AsyncSession) -> Role:
        """Creates a role definition. Returns the created role definition"""
        permissions: list[Permission] = []
        role = Role(name=model.name.lower(), domain=model.domain.lower(), permissions = permissions)
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role

    async def read_role(self, model: RoleBase, db: AsyncSession) -> Role | None:
        """Reads a role by name and domain. Returns the retrieved role"""
        statement = select(Role)
        statement = statement.filter_by(name=model.name.lower(), domain=model.domain.lower())
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def read_roles(self, name:str, domain:str, db: AsyncSession) -> list[Role]:
        """Reads all roles with optional filtering. Returns the retrieved collection of roles"""
        statement = select(Role)
        if name:
            statement = statement.filter_by(name=name.lower())
        if domain:
            statement = statement.filter_by(domain=domain.lower())
        result = await db.execute(statement)
        roles = result.unique().scalars().all()
        return list(roles)

    async def delete_role(self, role: Role, db: AsyncSession) -> Role | None:
        """Deletes a role from database. Returns the deleted role"""
        if role:
            await db.delete(role)
            await db.commit()
        return role

    async def assign_permission(self, role:Role, permission:Permission, db: AsyncSession) -> Role:
        """Assigns one permission to the role"""
        if permission not in role.permissions:
            role.permissions.append(permission)
            db.add(role)
            await db.commit()
            await db.refresh(role)
        return role

    async def unassign_permission(self, role:Role, permission:Permission, db: AsyncSession) -> Role:
        """Unassigns one permission from the role"""
        if permission in role.permissions:
            role.permissions.remove(permission)
            db.add(role)
            await db.commit()
            await db.refresh(role)
        return role


roles_repository:RolesRepository = RolesRepository()
