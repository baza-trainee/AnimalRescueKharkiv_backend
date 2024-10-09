import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.settings import settings
from src.permissions.repository import permissions_repository
from src.permissions.schemas import PermissionBase
from src.roles.repository import roles_repository
from src.roles.schemas import RoleBase
from src.users.repository import users_repository
from src.users.schemas import UserCreate


class DataInitializer:
    """A utility class to initialize data (permissions, roles, and users)
    from JSON files into the database. The class reads data from JSON
    files located in a specified directory and inserts the data into
    the database if the records don't already exist.

    Attributes:
    ----------
    db : AsyncSession
        A database session for executing asynchronous queries.
    base_path : Path
        The path where JSON files containing initial data are stored.
        Defaults to the 'init_data' directory located in the same folder
        as the script.
    """

    def __init__(self, db_session: AsyncSession, base_path: Path = Path(__file__).parent / "init_data") -> None:
        """Initializes the DataInitializer instance with a database session and
        an optional base path where the JSON files are located.

        Parameters
        ----------
        db_session : AsyncSession
            The asynchronous session to be used for database transactions.
        base_path : Path, optional
            The directory where the JSON files containing the initial data
            are stored. Defaults to the 'init_data' directory.
        """
        self.db = db_session
        self.base_path = base_path

    def __load_json(self, filename: str) -> dict | None:
        """Loads a JSON file and returns its contents as a dictionary.

        Parameters
        ----------
        filename : str
            The name of the JSON file to be loaded.

        Returns:
        -------
        dict | None
            A dictionary containing the data from the JSON file if the file
            exists, otherwise None.
        """
        path = self.base_path / filename
        if path.exists():
            with path.open() as file:
                return json.load(file)
        return None

    async def __init_permissions(self) -> None:
        """Initializes permissions by reading the 'permissions.json' file and
        adding permissions to the database if they don't already exist.

        The method iterates through the list of permissions in the file, checks
        if each permission exists in the database, and creates it if it doesn't.
        """
        permissions_data = self.__load_json("permissions.json")
        if permissions_data:
            for perm in permissions_data:
                perm_obj = PermissionBase(**perm)
                existing = await permissions_repository.read_permission(perm_obj, self.db)
                if not existing:
                    await permissions_repository.create_permission(perm_obj, self.db)

    async def __init_roles(self) -> None:
        """Initializes roles by reading the 'roles.json' file and adding roles to
        the database if they don't already exist.

        The method iterates through the list of roles in the file, checks if
        each role exists in the database, and creates it if it doesn't.
        """
        roles_data = self.__load_json("roles.json")
        if roles_data:
            for role in roles_data:
                role_obj = RoleBase(**role)
                existing = await roles_repository.read_role(role_obj, self.db)
                if not existing:
                    await roles_repository.create_role(role_obj, self.db)

    async def __init_users(self) -> None:
        """Initializes users by reading the 'users.json' file and adding users to
        the database if they don't already exist.

        The method iterates through the list of users in the file, checks if
        each user exists in the database, and creates them if they don't.
        """
        users_data = self.__load_json("users.json")
        if users_data:
            for user in users_data:
                user_obj = UserCreate(**user)
                existing = await users_repository.read_user(user_obj, self.db)
                if not existing:
                    await users_repository.create_user(user_obj, self.db)

    async def __init_super_user(self) -> None:
        """Initializes or updates the super user in the database.

        This method checks whether a super user with the predefined
        credentials exists in the database. If not, it creates a new
        super user. If the user already exists, it updates the user's
        information with the latest credentials from the settings.
        """
        role_obj = RoleBase(
            domain="system",
            name=settings.super_user_role,
        )
        role = await roles_repository.read_role(role_obj, self.db)
        if not role:
            role = await roles_repository.create_role(role_obj, self.db)
        user_obj = UserCreate(
            domain="system",
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

    async def run(self) -> None:
        """Executes the data initialization process for permissions, roles, and users.

        This method sequentially calls `init_permissions()`, `init_roles()`, and
        `init_users()` to initialize the database with the data from the respective
        JSON files.
        """
        await self.__init_permissions()
        await self.__init_roles()
        await self.__init_users()
        await self.__init_super_user()
