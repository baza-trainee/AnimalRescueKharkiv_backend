from abc import ABCMeta
from typing import Any, ClassVar


class SingletonMeta(ABCMeta):

    _instances: ClassVar = {}

    def __call__(cls, *args, **kwargs) -> (object | None):
        """Creates a singleton instance of a type"""
        if cls.__module__.startswith("src."):
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]
        return None
