from dataclasses import dataclass
from time import time
from typing import Dict
import uuid

@dataclass
class MediaCacheRecord:
    key: uuid.UUID
    value: bytes
    timestamp: float
    
    @property
    def size(self) -> int:
        return len(self.value)    

class MediaCache:
    def __init__(self, media_cache_size: int, media_cache_record_limit:int) -> None:
        self.media_cache_size = media_cache_size
        self.media_cache_record_limit = media_cache_record_limit
        self.__cache = {}
        self.__cache_index = {}
        self.__current_size = 0
    
    def add(self, key:uuid.UUID, value: bytes) -> None:
        if key not in self.__cache.keys():
            new_record = MediaCacheRecord (
                key=key,
                value=value,
                timestamp=time()
            )
            if new_record.size <= self.media_cache_record_limit:
                num = 0               
                while new_record.size + self.__current_size > self.media_cache_size:
                    self.__scavange_cache(num)
                    num += 1
                self.__add(new_record=new_record)

    def get(self, key:uuid.UUID) -> bytes | None:
        if key in self.__cache.keys():
            record:MediaCacheRecord = self.__cache[key]           
            return record.value
        return None
    
    def __add(self, new_record: MediaCacheRecord) -> None:
        self.__cache[new_record.key] = new_record
        self.__current_size += new_record.size
        if new_record.timestamp not in self.__cache_index.keys():
            self.__cache_index[new_record.timestamp] = []
        self.__cache_index[new_record.timestamp].append(new_record.key)

    def __scavange_cache(self, level=0):
        timestamps:list[float] = self.__cache_index.keys()
        timestamps.sort()
        count = len(timestamps)
        if level >= 3:
            self.__cache.clear()
            self.__cache_index.clear()
            self.__current_size = 0
            return            
        num = 3
        num += level
        count_to_delete = count / 10 * num
        for index in range(0, count_to_delete):
            timestamp = timestamps[index]
            try:
                keys = self.__cache_index.pop(timestamp)
                for key in keys:
                    try:
                        value:MediaCacheRecord = self.__cache.pop(key)                                                
                        self.__current_size -= value.size
                    except KeyError:
                        continue                
            except KeyError:
                continue        

                        