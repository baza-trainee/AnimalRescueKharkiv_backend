import logging
from typing import TYPE_CHECKING, List

import uvicorn
from sqlalchemy import Select, and_, any_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import ColumnElement, ColumnExpressionArgument
from src.media.models import MediaAsset
from src.roles.models import Role
from src.singleton import SingletonMeta
from src.users.models import User
from src.users.schemas import UserBase, UserCreate, UserPasswordNew, UserPasswordUpdate, UserUpdate

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

    def __get_search_conditions(self, *terms) -> ColumnElement[bool] | None:
        if not terms:
            return None
        prefixes: List[str] = [prefix + "%" for prefix in terms]
        expression: List[ColumnExpressionArgument[bool]] = []
        expression.append(func.lower(User.email).ilike(any_(prefixes)))
        expression.append(func.lower(User.first_name).ilike(any_(prefixes)))
        expression.append(func.lower(User.last_name).ilike(any_(prefixes)))
        expression.append(User.role.has(Role.title.ilike(any_(prefixes))))
        return or_(*expression)

    async def search_users(self, *terms, domain:str, db: AsyncSession) -> list[User]:
        """Searches all users by terms. Returns the retrieved user collection"""
        statement = select(User)
        if domain:
            statement = statement.filter_by(domain=domain.lower())
        condition: ColumnElement[bool] | None = self.__get_search_conditions(*terms)
        if condition is not None:
            statement = statement.filter(condition)
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
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def assign_role_to_user(self, user: User, role: Role, db: AsyncSession) -> User:
        """Assigns role to user. Returns the updated user"""
        if role:
            user.role = role
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    async def assign_photo_to_user(self, user: User, photo: MediaAsset, db: AsyncSession) -> User:
        """Assigns photo to user. Returns the updated user"""
        if photo:
            user.photo = photo
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
