import functools
import json
import logging
import os
from hashlib import sha256
from pathlib import Path
from typing import Callable, ClassVar

import uvicorn
from init_model import InitData
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.settings import settings
from src.crm.repository import animals_repository
from src.crm.schemas import AnimalTypeBase, LocationBase
from src.permissions.repository import permissions_repository
from src.permissions.schemas import PermissionBase
from src.roles.repository import roles_repository
from src.roles.schemas import RoleBase, RoleUpdate
from src.users.repository import users_repository
from src.users.schemas import UserCreate, UserUpdate

logger = logging.getLogger(uvicorn.logging.__name__)

class AutoInitializer:
    _initializers: ClassVar[dict] = {}
    @classmethod
    def data_init(cls, index: int) -> Callable:
        """Decorator to save initializer methods in a private dictionary."""
        def decorator(method: Callable) -> Callable:
            @functools.wraps(method)
            def wrapper(self: object, *args, **kwargs) -> None:
                return method(self, *args, **kwargs)

            if not hasattr(cls, "_initializers"):
                cls._initializers = {}
            init_index = index
            if index in cls._initializers:
                init_index = max(cls._initializers.keys()) + 1
            cls._initializers[init_index] = wrapper
            return wrapper

        return decorator

class DataInitializer(AutoInitializer):
    def __init__(self, db_session: AsyncSession, base_path: Path = Path(__file__).parent / "init_data") -> None:
        """Creates instance of DataInitializer"""
        self.db = db_session
        self.base_path = base_path

    def __load_json(self, filename: str) -> dict | None:
        path = self.base_path / filename
        if path.exists():
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        return None

    @AutoInitializer.data_init(index=1)
    async def __init_permissions(self) -> None:
        permissions_data = self.__load_json("permissions.json")
        if permissions_data:
            for perm in permissions_data:
                perm_obj = PermissionBase(**perm)
                existing = await permissions_repository.read_permission(perm_obj, self.db)
                if not existing:
                    await permissions_repository.create_permission(perm_obj, self.db)
                elif perm_obj.title:
                    await permissions_repository.update_title(existing, perm_obj.title, self.db)

    @AutoInitializer.data_init(index=2)
    async def __init_roles(self) -> None:
        roles_data = self.__load_json("roles.json")
        if roles_data:
            for role_model in roles_data:
                role_obj = RoleBase(**role_model)
                existing = await roles_repository.read_role(role_obj, self.db)
                if not existing:
                    existing = await roles_repository.create_role(role_obj, self.db)
                role_update = RoleUpdate(**role_model)
                if role_update and role_update.assign:
                    if role_update.title:
                        existing = await roles_repository.update_title(existing, role_update.title, self.db)
                    permissions = await permissions_repository.read_permissions(role_update.assign, self.db)
                    for permission in permissions:
                        if permission and (not existing.permissions or
                                           all(p.id != permission.id for p in existing.permissions)):
                            existing = await roles_repository.assign_permission(existing, permission, self.db)

    @AutoInitializer.data_init(index=3)
    async def __init_users(self) -> None:
        users_data = self.__load_json("users.json")
        if users_data:
            for user in users_data:
                user_obj = UserCreate(**user)
                existing = await users_repository.read_user(user_obj, self.db)
                if not existing:
                    existing = await users_repository.create_user(user_obj, self.db)
                elif user_obj.first_name or user_obj.last_name or user_obj.phone:
                    existing  = await users_repository.update_user(existing, UserUpdate(**user), self.db)
                if user_obj.role and user_obj.role.name and user_obj.role.domain:
                    role = await roles_repository.read_role(user_obj.role, self.db)
                    if role and (not existing.role or existing.role.id != role.id):
                        existing = await users_repository.assign_role_to_user(existing, role, self.db)

    @AutoInitializer.data_init(index=4)
    async def __init_super_user(self) -> None:
        role_obj = RoleBase(
            domain=settings.super_user_domain,
            name=settings.super_user_role,
        )
        role = await roles_repository.read_role(role_obj, self.db)
        if not role:
            role = await roles_repository.create_role(role_obj, self.db)
        user_obj = UserCreate(
            domain=settings.super_user_domain,
            email=settings.super_user_mail,
            password=settings.super_user_password,
        )
        existing = await users_repository.read_user(user_obj, self.db)
        if not existing:
            existing = await users_repository.create_user(user_obj, self.db)
            existing.role_id = role.id
            self.db.add(existing)
            await self.db.commit()
            await self.db.refresh(existing)
            return
        if (existing.password != user_obj.password
            or existing.email != user_obj.email
            or existing.role_id != role.id):
            existing.password = user_obj.password
            existing.email = user_obj.email
            existing.role_id = role.id
            self.db.add(existing)
            await self.db.commit()
            await self.db.refresh(existing)

    @AutoInitializer.data_init(index=5)
    async def __init_locations(self) -> None:
        locations_data = self.__load_json("locations.json")
        locations = await animals_repository.read_locations(self.db)
        location_names = [loc.name.lower() for loc in locations]
        if locations_data:
            for location in locations_data:
                location_obj = LocationBase(**location)
                if location_obj.name.lower() not in location_names:
                    await animals_repository.create_location(location_obj, self.db)

    @AutoInitializer.data_init(index=6)
    async def __init_animal_types(self) -> None:
        animal_types_data = self.__load_json("animal_types.json")
        animal_types = await animals_repository.read_animal_types(self.db)
        animal_type_names = [at.name.lower() for at in animal_types]
        if animal_types_data:
            for animal_type in animal_types_data:
                animal_type_obj = AnimalTypeBase(**animal_type)
                if animal_type_obj.name.lower() not in animal_type_names:
                    await animals_repository.create_animal_type(animal_type_obj, self.db)

    async def __run_initializers(self) -> None:
        for initializer in sorted(self._initializers.items()):
            name = initializer[1].__name__.removeprefix("__")
            logger.info(f"{name} executed")
            try:
                await initializer[1](self)
            except Exception:
                logger.exception(f"{name} failed with error:\n")

    async def run(self) -> None:
        """Executes the data initialization process"""
        logger.info(f"{self.__class__.__name__} started")
        statement = select(InitData).where(InitData.id == 1)
        init_data = (await self.db.execute(statement)).scalar_one_or_none()
        new_hash = self.__calculate_combined_checksum(self.base_path)
        if not init_data:
           init_data = InitData()

        if not init_data.data_hash or new_hash != init_data.data_hash:
           init_data.data_hash = new_hash
           self.db.add(init_data)
           await self.db.commit()
           await self.__run_initializers()
        else:
            logger.info(f"{self.__class__.__name__} no changes to initialize")
        logger.info(f"{self.__class__.__name__} completed")

    def __calculate_combined_checksum(self, directory_path: Path) -> str:
        hasher = sha256()

        file_paths = sorted(f for f in directory_path.iterdir() if f.is_file() and f.suffix.lower() == ".json")

        for file_path in file_paths:
            with file_path.open("rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)

        return hasher.hexdigest()
