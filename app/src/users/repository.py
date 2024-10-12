import logging
from typing import TYPE_CHECKING

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.media.repository import media_repository
from src.roles.repository import roles_repository
from src.singleton import SingletonMeta
from src.users.models import User
from src.users.schemas import UserBase, UserCreate, UserPasswordNew, UserPasswordUpdate, UserUpdate

if TYPE_CHECKING:
    from src.roles.models import Role

logger = logging.getLogger(uvicorn.logging.__name__)


class UsersRepository(metaclass=SingletonMeta):
    async def create_user(self, model: UserCreate, db: AsyncSession) -> User:
        """Creates a new user. Returns the created user"""
        role: Role = None
        user = User(email=model.email.lower(),
                    domain=model.domain.lower(),
                    first_name=model.first_name,
                    last_name=model.last_name,
                    phone=model.phone,
                    password=model.password,
                    role=role)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def read_user(self, model: UserBase, db: AsyncSession) -> User | None:
        """Reads a user by email and domain. Returns the retrieved user"""
        statement = select(User).filter_by(
            email=model.email.lower(),
            domain=model.domain.lower(),
        )
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def read_users(self, email: str, domain: str, db: AsyncSession) -> list[User]:
        """Reads all users with optional filtering. Returns the retrieved user collection"""
        statement = select(User)
        if email:
            statement = statement.filter_by(email=email.lower())
        if domain:
            statement = statement.filter_by(domain=domain.lower())
        result = await db.execute(statement)
        users = result.unique().scalars().all()
        return list(users)

    async def update_user(self, user: User, new_data: UserUpdate, db: AsyncSession) -> User:
        """Update user data. Returns the updated user"""
        if new_data.first_name:
            user.first_name = new_data.first_name
        if new_data.last_name:
            user.last_name = new_data.last_name
        if new_data.phone:
            user.phone = new_data.phone
        if new_data.photo:
            photo = await media_repository.read_media_asset(media_asset_id=new_data.photo.id, db=db)
            if photo:
                user.photo.id = photo.id
        if new_data.role:
            role = await roles_repository.read_role(model=new_data.role, db=db)
            if role:
                user.role_id = role.id
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_password(self, user: User, update: UserPasswordUpdate, db: AsyncSession) -> User:
        """Changes the user's password to "new password" in the database
        after checking that the "entered password" matches the current user password
        """
        if user.password != update.password_old:
            msg = "The entered password does not match the old password."
            raise ValueError(msg)
        user.password = update.password_new
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def set_new_password(self, user: User, body: UserPasswordNew, db: AsyncSession) -> User:
        """Changes the user's password to "new password" in the database"""
        user.password = body.password_new
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
