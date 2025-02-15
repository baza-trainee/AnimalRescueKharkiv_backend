import logging
import uuid
from datetime import datetime
from random import randint
from typing import TYPE_CHECKING, Any, List

import uvicorn
from fastapi import APIRouter, Depends, File, HTTPException, Query, Security, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.authorization.service import authorization_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG

# from src.media.repository import media_repository
# from src.media.schemas import MediaAssetResponse
from src.services.cache import Cache
from src.users.models import User

# if TYPE_CHECKING:
#     from src.media.models import MediaAsset

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.stats_prefix, tags=["stats"])
stats_router_cache: Cache = Cache(owner=router, all_prefix="stats", ttl=settings.default_cache_ttl)


@router.get("/countries")
async def read_countries_stats(
    _current_user: User = Security(authorization_service.authorize_user, scopes=["crm:read"]),
    ) -> JSONResponse:
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
       "data": data,
    }

    return response


@router.get("/departments")
async def read_departments_stats(
    _current_user: User = Security(authorization_service.authorize_user, scopes=["crm:read"]),
    ) -> JSONResponse:
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
        "data": data,
    }

    return response
