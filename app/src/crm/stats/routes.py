import logging
from datetime import date
from typing import List, Optional, Tuple

import uvicorn
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.authorization.service import authorization_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.crm.stats.repository import stats_repository
from src.crm.stats.schemas import AnimalStatusStats, DateQuery, LabeledStats, PastOrPresentDate
from src.exceptions.exceptions import RETURN_MSG
from src.services.cache import Cache
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.crm_prefix+settings.stats_prefix, tags=["crm-stats"])
stats_router_cache: Cache = Cache(owner=router, all_prefix="stats", ttl=settings.default_cache_ttl)

def __serialize_date(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    return value

def __validate_query(
    from_date: Optional[PastOrPresentDate] = None,
    to_date: Optional[PastOrPresentDate] = None,
) -> DateQuery:
    """Custom validation function for query parameters."""
    try:
        return DateQuery(from_date=from_date, to_date=to_date)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            modified_error = error.copy()
            if "input" in modified_error:
                if isinstance(modified_error["input"], dict):
                    modified_error["input"] = {
                        k: __serialize_date(v) for k, v in modified_error["input"].items()
                    }
                elif isinstance(modified_error["input"], date):
                    modified_error["input"] = __serialize_date(modified_error["input"])

            if "ctx" in modified_error:
                if isinstance(modified_error["ctx"], dict) and "error" in modified_error["ctx"]:
                    modified_error["ctx"]["error"] = str(modified_error["ctx"]["error"])
                elif isinstance(modified_error["ctx"], ValueError):
                    modified_error["ctx"] = {"error": str(modified_error["ctx"])}
            if not modified_error["loc"]:
                modified_error["loc"] = ["query"]

            errors.append(modified_error)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

@router.get("/countries", response_model=LabeledStats,
            description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_adotpion_countries_stats(
    query: DateQuery = Depends(__validate_query),
    _current_user: User = Security(authorization_service.authorize_user, scopes=["crm:read"]),
    db: AsyncSession = Depends(get_db),
    ) -> LabeledStats:
    """Retrieves contries stats"""
    logger.info(query.from_date)
    cache_key = stats_router_cache.get_all_records_cache_key_with_params("countries",
                                                                         query.from_date,
                                                                         query.to_date)
    response: LabeledStats = await stats_router_cache.get(key=cache_key)
    if response:
        return response

    data: List[Tuple[str | None, int]] = await stats_repository.get_animal_count_by_adoption_country(
                                                                            from_date=query.from_date,
                                                                            to_date=query.to_date, db=db)
    logger.info(data)
    response = LabeledStats(
        labels=[country[0] for country in data if country[0]],
        data=[country[1] for country in data if country[0]],
    )
    if response.labels and response.data:
        await stats_router_cache.set(key=cache_key, value=response)
    return response


@router.get("/departments", response_model=LabeledStats,
            description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_departments_stats(
    _current_user: User = Security(authorization_service.authorize_user, scopes=["crm:read"]),
     db: AsyncSession = Depends(get_db),
    ) -> LabeledStats:
    """Retrieves departments stats"""
    cache_key = stats_router_cache.get_all_records_cache_key_with_params("departments")
    response: LabeledStats = await stats_router_cache.get(key=cache_key)
    if response:
        return response

    data: List[Tuple[str | None, int]] = await stats_repository.get_animal_count_by_current_location(db=db)

    response = LabeledStats(
        labels=[location[0] for location in data if location[0]],
        data=[location[1] for location in data if location[0]],
    )
    if response.labels and response.data:
        await stats_router_cache.set(key=cache_key, value=response)
    return response

@router.get("/animals", response_model=AnimalStatusStats,
            description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_animal_stats(
    query: DateQuery = Depends(__validate_query),
    _current_user: User = Security(authorization_service.authorize_user, scopes=["crm:read"]),
    db: AsyncSession = Depends(get_db),
    ) -> AnimalStatusStats:
    """Retrieves animal stats"""
    cache_key = stats_router_cache.get_all_records_cache_key_with_params("animals",
                                                                         query.from_date,
                                                                         query.to_date)
    response: AnimalStatusStats = await stats_router_cache.get(key=cache_key)
    if response:
        return response

    total:int = await stats_repository.get_total_animal_count(db=db)
    sterilized:int = await stats_repository.get_sterilized_animal_count(from_date=query.from_date,
                                                                    to_date=query.to_date,
                                                                    db=db)
    adopted:int = await stats_repository.get_adopted_animal_count(from_date=query.from_date,
                                                                    to_date=query.to_date,
                                                                    db=db)
    dead:int = await stats_repository.get_dead_animal_count(from_date=query.from_date,
                                                                    to_date=query.to_date,
                                                                    db=db)
    response = AnimalStatusStats(
        total=total,
        adopted=adopted,
        sterilized=sterilized,
        dead=dead,
    )

    if total or adopted or sterilized or dead:
        await stats_router_cache.set(key=cache_key, value=response)
    return response
