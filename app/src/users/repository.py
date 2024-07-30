import logging

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.roles.models import Role
from src.singleton import SingletonMeta
from src.users.models import User
from src.users.schemas import UserBase, UserCreate, UserResponse

logger = logging.getLogger(uvicorn.logging.__name__)


class UsersRepository(metaclass=SingletonMeta):
    async def create_user(self, model: UserCreate, db: AsyncSession) -> User:
        """Creates a new user. Returns created user"""
        user = User(username=model.username.lower(),
                    email=model.email,
                    domain=model.domain.lower(),
                    password=model.password,
                    role=model.role)
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
        """Reads all users with optional filtering. Returns the retrieved collection of users"""
        statement = select(User)
        if username:
            statement = statement.filter_by(name=username.lower())
        if domain:
            statement = statement.filter_by(domain=domain.lower())
        result = await db.execute(statement)
        users = result.unique().scalars().all()
        return list(users)


    async def update_user_email(self, user: User, email: str, db: AsyncSession) -> User:
        """Updates a user email in db. Returns updated user"""
        user.email = email.lower()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


    async def update_user_password(self, user: User, password: str, db: AsyncSession) -> User:
        """Updates a user password in db. Returns updated user"""
        user.password = password
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


    async def update_user_role(self, user: User, role: Role, db: AsyncSession) -> User:
        """Updates a user role in db. Returns updated user"""
        user.role = role
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


    async def delete_user(self, user: User, db: AsyncSession) -> User | None:
        """Deletes a user from db. Returns the deleted user"""
        if user:
            await db.delete(user)
            await db.commit()
        return user
