import logging
from datetime import datetime, timedelta, timezone  #UTC
from typing import List, Optional, Tuple

import uvicorn
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.managers import token_manager
from src.auth.models import SecurityToken, TokenType
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.singleton import SingletonMeta
from src.users.models import User
from src.users.repository import users_repository
from src.users.schemas import UserBase

logger = logging.getLogger(uvicorn.logging.__name__)


class Auth(metaclass=SingletonMeta):
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SECRET_KEY = settings.secret_key
    ALGORITHM = settings.algorithm
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}{settings.auth_prefix}/login")
    permissions_key = "permissions"

    async def create_access_token(
            self,
            user: User,
            refresh_id: str,
            db: AsyncSession,
    ) -> str:
        """Generates an access token for a given user by encoding their data and saves it to the database"""
        permissions = [str(p) for p in user.role.permissions]
        data = {
            "domain": user.domain,
            "sub": user.email,
            "role": user.role.name,
            "rid": refresh_id,
            self.permissions_key: permissions,
            }
        to_encode = data.copy()
        expire_on = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_mins)
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire_on, "scope": TokenType.access.name})
        encoded_access_token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

        token_record = await token_manager.write_token(token=encoded_access_token,
                                                       token_type=TokenType.access,
                                                       expire_on=expire_on,
                                                       user=user,
                                                       db=db)

        return token_record.token

    async def create_refresh_token(
            self,
            user: User,
            db: AsyncSession,
    ) -> Tuple[str, str]:
        """Generates a refresh token for a given user by encoding their data and saves it to the database"""
        permissions = [str(p) for p in user.role.permissions]
        data = {
            "domain": user.domain,
            "sub": user.email,
            "role": user.role.name,
            self.permissions_key: permissions,
            }
        to_encode = data.copy()
        expire_on = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire_on, "scope": TokenType.refresh.name})
        encoded_refresh_token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

        token_record = await token_manager.write_token(token=encoded_refresh_token,
                                                       token_type=TokenType.refresh,
                                                       expire_on=expire_on,
                                                       user=user,
                                                       db=db)

        return (token_record.token, str(token_record.id))

    async def create_email_token(
            self,
            token_type: TokenType,
            expiration_delta: timedelta,
            data: dict,
            db: AsyncSession,
            user: User = None,
    ) -> str:
        """Generates an email token for a given user by encoding their data and saves it to the database"""
        to_encode = data.copy()
        expire_on = datetime.now(timezone.utc) + expiration_delta
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire_on, "scope": token_type.name})
        token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

        token_record = await token_manager.write_token(token=token,
                                                       token_type=token_type,
                                                       expire_on=expire_on,
                                                       db=db,
                                                       user=user)

        return token_record.token

    async def get_access_token(
            self,
            token: str = Depends(oauth2_scheme),
            db: AsyncSession = Depends(get_db),
    ) -> SecurityToken:
        """Resolves a token record"""
        token_record = await self.validate_token(token=token, token_type=TokenType.access, db=db)
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=RETURN_MSG.token_credentials_error,
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload["scope"] == TokenType.access.name:
                email = payload["sub"]
                if email is None:
                    raise credentials_exception
            else:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        return token_record

    async def revoke_auth_tokens(
            self,
            access_token: str,
            db: AsyncSession,
    ) -> bool:
        """Invalidates an access token and its corresponding refresh token"""
        access_token_record = await token_manager.read_token(token=access_token, token_type=TokenType.access, db=db)

        if access_token_record:
            payload = self.get_payload_from_token(token=access_token_record.token)
            refresh_id = payload["rid"]
            refresh_token_record = await token_manager.read_token_by_id(token_id=refresh_id, db=db)
            access_token_record = await token_manager.delete_token(token=access_token_record, db=db)

            if refresh_token_record:
                refresh_token_record = await token_manager.delete_token(token=refresh_token_record, db=db)

            return True

        return False

    async def validate_token(
            self,
            token: str,
            token_type: TokenType,
            db: AsyncSession,
    ) -> SecurityToken:
        """Verifies the expiration of a security token"""
        try:
            token_record: SecurityToken = await token_manager.read_token(token=token, token_type=token_type, db=db)
            if token_record:
                payload = jwt.decode(token_record.token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
                expire = payload["exp"]
                if expire >= datetime.now(timezone.utc).timestamp():
                    return token_record
                if payload["scope"] != token_type.name:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.token_scope_invalid)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.token_invalid)
        except JWTError as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.token_invalid)

    async def validate_user_from_refresh_token(
            self,
            refresh_token: str,
            db: AsyncSession,
    ) -> Tuple[User, str]:
        """Validates user details from a refresh token"""
        refresh_token_record = await auth_service.validate_token(token=refresh_token,
                                                                 token_type=TokenType.refresh,
                                                                 db=db)

        payload = auth_service.get_payload_from_token(token=refresh_token_record.token)
        domain = payload["domain"]
        email = payload["sub"]
        role_name = payload["role"]
        refresh_id = str(refresh_token_record.id)

        if domain and email and role_name:
            user_model = UserBase(domain=domain, email=email)
            user = await users_repository.read_user(model=user_model, db=db)

            if user is None:
                await token_manager.delete_token(token=refresh_token_record, db=db)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.user_not_found % email)

            if role_name != user.role.name:
                await token_manager.delete_token(token=refresh_token_record, db=db)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.token_invalid)

            return (user, refresh_id)

        await token_manager.delete_token(token=refresh_token_record, db=db)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.token_invalid)

    def get_payload_from_token(self, token: str) -> dict:
        """Extracts payload from a given token"""
        try:
            return jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
        except JWTError as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.token_invalid)

    def get_permissions_from_token(self, token: str) -> List[str] | None:
        """Extracts list of permissions from payload"""
        payload = self.get_payload_from_token(token=token)

        if self.permissions_key in payload:
            return payload[self.permissions_key]
        return None


auth_service: Auth = Auth()
