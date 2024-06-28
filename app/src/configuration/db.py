# mypy: ignore-errors
import redis
import redis.asyncio as redis_async
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.configuration.settings import settings

SQLALCHEMY_DATABASE_URL = settings.sqlalchemy_database_url
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = async_sessionmaker(autocommit=False, autoflush=True, bind=engine)

# Dependency
async def get_db(): # noqa: ANN201
    """..."""
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.aclose()
