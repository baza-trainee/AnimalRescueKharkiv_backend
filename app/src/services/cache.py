import logging
import pickle
import uuid
from typing import Optional

import uvicorn
from src.configuration.redis import redis_client_async
from src.configuration.settings import settings
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)

class Cache(metaclass=SingletonMeta):
    def __init__(self, owner:object, all_prefix: str, ttl: Optional[int] = None) -> None:
        """Initializes cache instance"""
        self.__client = redis_client_async
        self.__owner = owner
        self.__all_prefix = all_prefix
        self.__all_cache_keys: set[str] = set()
        self.__ttl = ttl or 15*60

    @property
    def all_cache_keys(self) -> set[str]:
        """Returns set of cache keys for all records"""
        return self.__all_cache_keys

    async def get(self, key:str) -> object | None:
        """Gets cache record by uniquekey"""
        if self.__client:
            result = await self.__client.get(key)
            if result:
                logger.debug(f"Redis Cache: HIT - record for {key} found")
                return pickle.loads(result) #noqa:S301
            logger.debug(f"Redis Cache: MISS - no record for {key} found")
        return None

    async def set(self, key:str, value:object) -> None:
        """Sets cache record by unique key"""
        if self.__client:
            value = pickle.dumps(value)
            await self.__client.set(key, value)
            await self.__client.expire(key, self.__ttl)
            logger.debug(f"Redis Cache: NEW RECORD with {key} added")

    def get_cache_key(self, key: uuid.UUID | str ) -> str:
        """Generates and returns cache key"""
        k = str(key.hex) if isinstance(key, uuid.UUID) else key
        return f"{id(self.__owner)}_{k}"

    def get_all_records_cache_key_with_params(self, *args) -> str:
        """Generates and returns cache key for all records"""
        key = hash(args)
        cache_key = self.get_cache_key(f"all_{self.__all_prefix}_{key}")
        self.__all_cache_keys.add(cache_key)
        return cache_key

    async def invalidate_key(self, key: str) -> None:
        """Invalidates specific cache record by its key"""
        if self.__client:
            await self.__client.delete(key)
            logger.debug(f"Redis Cache: record with {key} invalidated")

    async def invalidate_all_keys(self) -> None:
        """Invalidates cache records for all keys"""
        if self.__client:
            for cahce_key in self.__all_cache_keys:
                await self.__client.delete(cahce_key)
                logger.debug(f"Redis Cache: record with {cahce_key} invalidated")
