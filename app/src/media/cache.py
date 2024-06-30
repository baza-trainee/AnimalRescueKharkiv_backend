import uuid
from dataclasses import dataclass
from time import time
from typing import Dict, List


@dataclass
class MediaCacheRecord:
    """Type for a meria cache record wrapper to store bytes with timestamp"""
    key: uuid.UUID
    value: bytes
    timestamp: float

    @property
    def size(self) -> int:
        """Retrun size of the record's bytes value"""
        return len(self.value)

class MediaCache:
    """Media cache type that stores MediaCacheRecord objects"""
    def __init__(self, media_cache_size: int, media_cache_record_limit:int) -> None:
        """Initializes an instance of MediaCache with specified size and limit for cache records"""
        self.media_cache_size = media_cache_size
        self.media_cache_record_limit = media_cache_record_limit
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
            if new_record.size <= self.media_cache_record_limit:
                num = 0
                while new_record.size + self.__current_size > self.media_cache_size:
                    self.__scavange_cache(num)
                    num += 1
                self.__add(new_record=new_record)

    def get(self, key:uuid.UUID) -> bytes | None:
        """Gets byte value from the cache by the passed key"""
        if key in self.__cache:
            record:MediaCacheRecord = self.__cache[key]
            return record.value
        return None

    def __add(self, new_record: MediaCacheRecord) -> None:
        self.__cache[new_record.key] = new_record
        self.__current_size += new_record.size
        if new_record.timestamp not in self.__cache_index:
            self.__cache_index[new_record.timestamp] = []
        self.__cache_index[new_record.timestamp].append(new_record.key)

    def __scavange_cache(self, level: int = 0) -> None:
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
