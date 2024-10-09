import asyncio
import logging
from time import sleep
from typing import Any, Awaitable, Callable, List, Tuple

import uvicorn
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)


class Scheduler(metaclass=SingletonMeta):
    def __init__(self, frequency: int, loop: asyncio.AbstractEventLoop) -> None:
        """Initializes scheduler instance"""
        self.__frequency = frequency
        self.__is_running: bool = False
        self.__jobs: List[Tuple[Callable[[Any, Any], Awaitable[Any]], Tuple]] = []
        self.__loop = loop

    def schedule_job(self, job: Callable[[Any, Any], Awaitable[Any]], *args) -> None:
        """Shedules a job by adding it to the list along with its arguments"""
        self.__jobs.append((job, args))
        logger.info(f"Job scheduled: {job.__name__}")

    def __run_job(self, job: Callable,  *args) -> None:
        try:
            logger.info(f"Job running: {job.__name__}")
            if asyncio.iscoroutinefunction(job):
                asyncio.run_coroutine_threadsafe(coro=job(*args), loop=self.__loop)
            else:
                asyncio.run_coroutine_threadsafe(coro=self.__loop.run_in_executor(None, job, *args), loop=self.__loop)
        except Exception as e:
                logger.error(f"Job '{job.__name__}' failed with exception: {e}")

    def start(self) -> None:
        """Initiates and repeatedly runs scheduled jobs according to the specified frequency"""
        self.__is_running = True
        logger.info("Scheduler started")
        while self.__is_running:
            for _ in range(self.__frequency):
                if self.__is_running:
                    sleep(1)
                else:
                    break
            if self.__is_running:
                for job, args in self.__jobs:
                    self.__run_job(job, *args)


    def stop(self) -> None:
        """Stops all running jobs"""
        self.__is_running = False
        logger.info("Scheduler shutdown")
