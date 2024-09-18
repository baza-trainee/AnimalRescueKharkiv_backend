import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from src.permissions.schemas import PermissionBase
from src.permissions.repository import permissions_repository
from src.roles.schemas import RoleBase
from src.roles.repository import roles_repository
from src.users.schemas import UserCreate
from src.users.repository import users_repository

class DataInitializer:
    def __init__(self, db_session: AsyncSession, base_path: Path = Path(__file__).parent / 'init_data'):
        self.db = db_session
        self.base_path = base_path

    def load_json(self, filename: str):
        path = self.base_path / filename
        if path.exists():
            with open(path, 'r') as file:
                return json.load(file)
        return

    async def init_permissions(self):
        permissions_data = self.load_json('permissions.json')
        if permissions_data:
            for perm in permissions_data:
                perm_obj = PermissionBase(**perm)
                existing = await permissions_repository.read_permission(perm_obj, self.db)
                if not existing:
                    await permissions_repository.create_permission(perm_obj, self.db)

    async def init_roles(self):
        roles_data = self.load_json('roles.json')
        if roles_data:
            for role in roles_data:
                role_obj = RoleBase(**role)
                existing = await roles_repository.read_role(role_obj, self.db)
                if not existing:
                    await roles_repository.create_role(role_obj, self.db)

    async def init_users(self):
        users_data = self.load_json('users.json')
        if users_data:
            for user in users_data:
                user_obj = UserCreate(**user)
                existing = await users_repository.read_user(user_obj, self.db)
                if not existing:
                    await users_repository.create_user(user_obj, self.db)

    async def run(self):
        await self.init_permissions()
        await self.init_roles()
        await self.init_users()
