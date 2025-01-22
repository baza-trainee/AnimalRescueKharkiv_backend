import logging
import uuid
from datetime import datetime
from random import randint
from typing import TYPE_CHECKING, Any, List

import uvicorn
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG

# from src.media.repository import media_repository
# from src.media.schemas import MediaAssetResponse
from src.services.cache import Cache

# if TYPE_CHECKING:
#     from src.media.models import MediaAsset

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.stats_prefix, tags=["stats"])
stats_router_cache: Cache = Cache(owner=router, all_prefix="stats", ttl=settings.default_cache_ttl)


@router.get("/countries")
async def read_countries_stats() -> JSONResponse:
    """Retrieves contries stats"""
    data = [randint(1, 100) for _ in range(7)] #noqa: S311

    response: dict[str, Any] = {
        "labels": [
        "Україна",
        "Польща",
        "Румунія",
        "Чехія",
        "Молдова",
        "Німеччина",
        "Італія ",
        "Англія",

        ],
        "datasets": [
        {
            "label": "Кількість тварин",
                "data": data,
            "backgroundColor": [
            "rgba(232, 193, 160, 1)",
            "rgba(232, 168, 56, 1)",
            "rgba(241, 225, 91, 1)",
            "rgba(97, 205, 187, 1)",
            "rgba(244, 117, 96, 1)",
            "rgba(232, 168, 56, 1)",
            "rgba(151, 227, 213, 1)",
            "rgba(244, 117, 96, 1)",
            ],
            "borderRadius": 6,
            "borderWidth": 1,
        },
        ],
    }

    return response


@router.get("/departments")
async def read_departments_stats() -> JSONResponse:
    """Retrieves departments stats"""
    data = [randint(20, 100) for _ in range(8)] #noqa: S311

    response: dict[str, Any] = {
        "labels": [
            "Клініка",
            "Іподром",
            "Есеніна",
            "Перетримка Зоя",
            "Перетримка Марина",
            "Бабаї",
            "Жихор",
            "Первомайськ",
        ],
        "datasets": [
        {
            "label": "Кількість тварин",
                "data": data,
            "backgroundColor": [
                "rgba(232, 193, 160, 1)",
                "rgba(232, 168, 56, 1)",
                "rgba(241, 225, 91, 1)",
                "rgba(97, 205, 187, 1)",
                "rgba(244, 117, 96, 1)",
                "rgba(232, 168, 56, 1)",
                "rgba(151, 227, 213, 1)",
                "rgba(244, 117, 96, 1)",
            ],
            "borderRadius": 6,
            "borderWidth": 1,
        },
        ],
    }

    return response
