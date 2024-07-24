from typing import Any, AsyncGenerator

import redis.asyncio  #type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.configuration.settings import settings

SQLALCHEMY_DATABASE_URL = settings.sqlalchemy_database_url
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

# Dependency
async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """..."""
    async with SessionLocal() as db:
        yield db
