import logging
import uuid
from dataclasses import dataclass
from time import time
from typing import Dict, List

import uvicorn
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)

@dataclass
class MediaCacheRecord:
    key: uuid.UUID
    value: bytes
    timestamp: float

    @property
    def size(self) -> int:
        """Retrun size of the record's bytes value"""
        return len(self.value)

class MediaCache(metaclass=SingletonMeta):
    def __init__(self, media_cache_size: int, media_cache_record_limit:int) -> None:
        """Initializes an instance of MediaCache with specified size and limit for cache records"""
        self.media_cache_size = media_cache_size
        self.media_cache_record_limit = media_cache_record_limit
        logger.info(f"Cache created: 'MediaCache' (max size: {self.media_cache_size},"
                    f" record size limit: {self.media_cache_record_limit}) ")
        self.__cache: Dict[uuid.UUID, MediaCacheRecord] = {}
        self.__cache_index: Dict[float, List[uuid.UUID]] = {}
        self.__current_size = 0
        self.__full_cleanup_scavanging_level = 3

    def add(self, key:uuid.UUID, value: bytes) -> None:
        """Creates MediaCacheRecord out of the passed key-value pair and adds it into the cache"""
        if key not in self.__cache:
            new_record = MediaCacheRecord (
                key=key,
                value=value,
                timestamp=time(),
            )
            if (new_record.size <= self.media_cache_record_limit
                and new_record.size <= self.media_cache_size):
                num = 0
                while (new_record.size + self.__current_size > self.media_cache_size
                       and num <= self.__full_cleanup_scavanging_level):
                    logger.debug(f"Media Cache: Scavenging with level {num} executed")
                    self.__scavenge_cache(num)
                    num += 1
                self.__add(new_record=new_record)
                logger.debug(f"Media Cache: NEW RECORD for {key} added")

    def get(self, key:uuid.UUID) -> bytes | None:
        """Gets byte value from the cache by the passed key"""
        if key in self.__cache:
            record:MediaCacheRecord = self.__cache[key]
            logger.debug(f"Media Cache: HIT - record for {key} found")
            return record.value
        logger.debug(f"Media Cache: MISS - no record for {key} found")
        return None

    def delete(self, key: uuid.UUID) -> None:
        """Deletes byte value from the cache by the passed key"""
        if key in self.__cache:
            record = self.__cache.pop(key)
            if record.timestamp in self.__cache_index:
                index_record = self.__cache_index[record.timestamp]
                if len(index_record) > 1:
                    index_record.remove(key)
                else:
                    self.__cache_index.pop(record.timestamp)

    def __add(self, new_record: MediaCacheRecord) -> None:
        self.__cache[new_record.key] = new_record
        self.__current_size += new_record.size
        if new_record.timestamp not in self.__cache_index:
            self.__cache_index[new_record.timestamp] = []
        self.__cache_index[new_record.timestamp].append(new_record.key)

    def __scavenge_cache(self, level: int = 0) -> None:
        timestamps:list[float] = list(self.__cache_index.keys())
        timestamps.sort()
        count = len(timestamps)
        if level >= self.__full_cleanup_scavanging_level:
            self.__cache.clear()
            self.__cache_index.clear()
            self.__current_size = 0
            return
        num = 3
        num += level
        count_to_delete = int(count / 10 * num)
        for index in range(count_to_delete):
            timestamp = timestamps[index]
            if timestamp in self.__cache_index:
                keys = self.__cache_index.pop(timestamp)
                for key in keys:
                    if key in self.__cache:
                        value:MediaCacheRecord = self.__cache.pop(key)
                        self.__current_size -= value.size
