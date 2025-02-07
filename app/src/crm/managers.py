import logging
from datetime import datetime, timedelta, timezone

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.db import SessionLocal
from src.configuration.settings import settings
from src.crm.models import EditingLock
from src.singleton import SingletonMeta
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)

class EditingLockManager(metaclass=SingletonMeta):
    async def delete_expired_editing_locks(self) -> None:
        """Deletes expired editing locks from database"""
        async with SessionLocal() as db:
            statement = select(EditingLock)
            delta: timedelta = timedelta(minutes=settings.crm_editing_lock_expire_minutes)
            earliest_valid_created_at = datetime.now(timezone.utc).astimezone() - delta
            statement = statement.filter(EditingLock.created_at < earliest_valid_created_at)
            result = await db.execute(statement)
            locks = result.unique().scalars().all()
            count = len(locks)
            for lock in locks:
                await db.delete(lock)
            await db.commit()
            if count:
                logger.info(f"{self.__class__.__name__}: {count} editing locks successfully deleted")
            else:
                logger.info(f"{self.__class__.__name__}: No editing locks to delete")


editing_lock_manager: EditingLockManager = EditingLockManager()
