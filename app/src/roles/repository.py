import logging

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.settings import settings
from src.roles.models import Role
from src.roles.schemas import RoleBase
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)


class RolesRepository (metaclass=SingletonMeta):
    async def create_role(self, model: RoleBase, db: AsyncSession) -> Role:
        """Creates a role definition. Returns the created role definition"""
        role = Role(name=model.name.lower(), domain=model.domain.lower())
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role

    async def read_role(self, model: RoleBase, db: AsyncSession) -> Role | None:
        """Reads a role by name and domain. Returns the retrieved role"""
        statement = select(Role)
        statement = statement.filter_by(name=model.name.lower(), domain=model.domain.lower())
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def read_roles(self, name:str, domain:str, db: AsyncSession) -> list[Role]:
        """Reads all roles with optional filtering. Returns the retrieved collection of roles"""
        statement = select(Role)
        if name:
            statement = statement.filter_by(name=name.lower())
        if domain:
            statement = statement.filter_by(domain=domain.lower())
        result = await db.execute(statement)
        roles = result.scalars().all()
        return list(roles)

    async def delete_role(self, role: Role, db: AsyncSession) -> Role | None:
        """Deletes a role from database. Returns the deleted role"""
        if role:
            await db.delete(role)
            await db.commit()
        return role


roles_repository:RolesRepository = RolesRepository()
