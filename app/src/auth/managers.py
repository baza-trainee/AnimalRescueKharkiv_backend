import logging
from datetime import datetime, timezone

import uvicorn
from sqlalchemy import delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.models import SecurityToken, TokenType
from src.configuration.db import SessionLocal
from src.singleton import SingletonMeta
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)


class TokenManager(metaclass=SingletonMeta):
    async def write_token(
            self,
            token: str,
            token_type: TokenType,
            expire_on: datetime,
            db: AsyncSession,
            user: User = None,
    ) -> SecurityToken:
        """Writes a security token into database. Returns the written security token"""
        token_record = SecurityToken(token=token, token_type=token_type, expire_on=expire_on)
        if user:
            token_record.user_id=user.id
        db.add(token_record)
        await db.commit()
        await db.refresh(token_record)
        return token_record

    async def read_token(
            self, token: str,
            token_type: TokenType,
            db: AsyncSession,
    ) -> SecurityToken | None:
        """Reads a security token from database. Returns the retrieved security token"""
        statement = select(SecurityToken)
        statement = statement.filter_by(token=token, token_type=token_type)
        statement = statement.order_by(desc(SecurityToken.created_at))
        statement = statement.limit(1)
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def read_token_by_id(
            self,
            token_id: str,
            db: AsyncSession,
    ) -> SecurityToken | None:
        """Reads a security token by id from database. Returns the retrieved security token"""
        statement = select(SecurityToken)
        statement = statement.filter_by(id=token_id)
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def delete_token(
            self,
            token: SecurityToken,
            db: AsyncSession,
    ) -> SecurityToken | None:
        """Deletes a security token from database. Returns the deleted security token"""
        if token:
            await db.delete(token)
            await db.commit()
        return token

    async def delete_expired_tokens(self) -> None:
        """Deletes expired security tokens from database"""
        async with SessionLocal() as db:
            statement = delete(SecurityToken).where(SecurityToken.expire_on < datetime.now(timezone.utc).astimezone())
            result = await db.execute(statement)
            await db.commit()
            if result.rowcount:
                logger.info(f"{self.__class__.__name__}: {result.rowcount} security tokens successfully deleted")
            else:
                logger.info(f"{self.__class__.__name__}: No security tokens to delete")

    async def delete_all_tokens_for_user(
            self,
            user: User,
            db: AsyncSession,
    ) -> int:
        """Deletes all security tokens for the given user"""
        statement = delete(SecurityToken).where(SecurityToken.user_id == user.id)
        result = await db.execute(statement)
        await db.commit()
        return result.rowcount



token_manager: TokenManager = TokenManager()
