import asyncio
import logging
import os
import signal
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator

import uvicorn
import uvicorn.logging
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from init_manager import DataInitializer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, close_all_sessions
from src.auth.managers import token_manager
from src.configuration.db import SessionLocal, engine, get_db
from src.configuration.redis import redis_client_async
from src.configuration.settings import settings
from src.scheduler import Scheduler
from utils import get_app_routers

logger = logging.getLogger(uvicorn.logging.__name__)
logger.setLevel(level=settings.logging_level)

origins = settings.cors_origins.split("|")



def __init_routes(initialized_app: FastAPI) -> None:
    api_prefix = settings.api_prefix
    router:APIRouter
    for router in get_app_routers():
        initialized_app.include_router(router, prefix=api_prefix)
        logger.info(f"Router '{api_prefix}{router.prefix}' added")

async def __init_data() -> None:
    async with SessionLocal() as session:
        initializer = DataInitializer(db_session=session)
        await initializer.run()


def __init_scheduled_jobs(scheduler: Scheduler) -> None:
    scheduler.schedule_job(token_manager.delete_expired_tokens)


@asynccontextmanager
async def lifespan(initialized_app: FastAPI) -> AsyncGenerator[None, Any]:
    """..."""
    #startup initialization goes here
    scheduler: Scheduler = Scheduler(frequency=settings.scheduler_frequency, loop=asyncio.get_event_loop())
    logger.info("FastAPI applicaiton started...")
    await FastAPILimiter.init(redis_client_async)
    __init_routes(initialized_app=initialized_app)
    await __init_data()
    __init_scheduled_jobs(scheduler=scheduler)
    executor = ThreadPoolExecutor(max_workers=2)
    executor.submit(scheduler.start)

    yield

    #shutdown logic goes here
    scheduler.stop()
    executor.shutdown()
    await close_all_sessions()
    await engine.dispose()
    await redis_client_async.close(close_connection_pool=True)
    await FastAPILimiter.close()
    logger.info("FastAPI application shutdown")


app = FastAPI(lifespan=lifespan)



app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict:
    """..."""
    return {"message": "Welcome!"}


@app.get("/healthcheck")
async def healthchecker(db: AsyncSession = Depends(get_db)) -> dict:
    """..."""
    try:
        # Make request
        result = await db.execute(text("SELECT 1"))
        result = result.fetchone()
        if result is None:
            function_name = traceback.extract_stack(None, 2)[1][2]
            add_log = f"\n500:\t{datetime.now()}\tError connecting to the database.\t{function_name}"
            logger.error(add_log)
            raise HTTPException(status_code=500, detail="Database is not configured properly.")

        function_name = traceback.extract_stack(None, 2)[1][2]
        add_log = f"\n000:\t{datetime.now()}\tService is healthy and running\t{function_name}"
        logger.info(add_log)

        return {"message": "Service is healthy and running"} # noqa: TRY300

    except Exception as e:
        function_name = traceback.extract_stack(None, 2)[1][2]
        add_log = f"\n000:\t{datetime.now()}\tError connecting to the database.: {e}\t{function_name}"
        logger.error(add_log)
        raise HTTPException(status_code=500, detail="Database is not configured properly.")


def handle_signals() -> int:
    """Determines the appropriate signal to send for process termination based on the operating system."""
    if sys.platform == "win32":
        signal_name = signal.SIGBREAK
    else:
        signal_name = signal.SIGINT
    return signal_name


if __name__ == "__main__":
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        os.kill(os.getpid(), handle_signals())
