import logging
from typing import TYPE_CHECKING

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.roles.repository import roles_repository
from src.singleton import SingletonMeta
from src.users.models import User
from src.users.schemas import UserBase, UserCreate, UserUpdate

if TYPE_CHECKING:
    from src.roles.models import Role

logger = logging.getLogger(uvicorn.logging.__name__)


class UsersRepository(metaclass=SingletonMeta):
    async def create_user(self, model: UserCreate, db: AsyncSession) -> User:
        """Creates a new user. Returns the created user"""
        role: Role = None
        user = User(username=model.username.lower(),
                    email=model.email,
                    domain=model.domain.lower(),
                    password=model.password,
                    role=role)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


    async def read_user(self, model: UserBase, db: AsyncSession) -> User | None:
        """Reads a user by username and domain. Returns the retrieved user"""
        statement = select(User).filter_by(
            username=model.username.lower(),
            domain=model.domain.lower(),
        )
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()


    async def read_users(self, username: str, domain: str, db: AsyncSession) -> list[User]:
        """Reads all users with optional filtering. Returns the retrieved user collection"""
        statement = select(User)
        if username:
            statement = statement.filter_by(username=username.lower())
        if domain:
            statement = statement.filter_by(domain=domain.lower())
        result = await db.execute(statement)
        users = result.unique().scalars().all()
        return list(users)


    async def update_user(self, user: User, new_data: UserUpdate, db: AsyncSession) -> User:
        """Update user data. Returns the updated user"""
        if new_data.email:
            user.email = new_data.email
        if new_data.role:
            role = await roles_repository.read_role(model=new_data.role, db=db)
            if role:
                user.role_id = role.id
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


    async def delete_user(self, user: User, db: AsyncSession) -> User | None:
        """Removes a user from the database. Returns the removed user"""
        await db.delete(user)
        await db.commit()
        return user


users_repository: UsersRepository = UsersRepository()
