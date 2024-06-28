# mypy: ignore-errors
import logging
import os
import signal
import traceback
from contextlib import asynccontextmanager
from datetime import datetime

import redis.asyncio as redis
import uvicorn
import uvicorn.logging
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.db import SessionLocal, engine, get_db
from src.configuration.redis import redis_client_async
from src.configuration.settings import settings
from utils import get_app_routers

logger = logging.getLogger(uvicorn.logging.__name__)

origins = settings.cors_origins.split("|")


@asynccontextmanager
async def lifespan(test: FastAPI): # noqa: ANN201, ARG001
    """..."""
    #startup initialization goes here
    logger.info("FastAPI applicaiton started...")
    await FastAPILimiter.init(redis_client_async)
    yield
    #shutdown logic goes here
    await SessionLocal.close_all()
    await engine.dispose()
    await redis_client_async.close(close_connection_pool=True)
    await FastAPILimiter.close()
    logger.info("FastAPI application shutdown")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict:
    """..."""
    return {"message": "Welcome!"}


@app.get("/api/healthcheck")
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



for router in get_app_routers():
    app.include_router(router, prefix="/api")


if __name__ == "__main__":
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        os.kill(os.getpid(), signal.SIGBREAK)
        os.kill(os.getpid(), signal.SIGTERM)
