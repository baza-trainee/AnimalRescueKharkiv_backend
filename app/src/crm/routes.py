import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, List, Optional, Type
from uuid import UUID

import uvicorn
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Security, status
from fastapi.encoders import jsonable_encoder
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from src.authorization.service import authorization_service
from src.base_schemas import Sorting
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.crm.models import Animal, AnimalType, Gender, Location
from src.crm.repository import animals_repository
from src.crm.schemas import (
    AnimalCreate,
    AnimalResponse,
    AnimalState,
    AnimalTypeBase,
    AnimalTypeResponse,
    BaseModel,
    EditingLockResponse,
    LocationBase,
    LocationResponse,
    NamedSection,
    PastOrPresentDate,
)
from src.crm.stats.routes import stats_router_cache
from src.crm.strategies import update_handler
from src.exceptions.exceptions import RETURN_MSG
from src.media.models import MediaAsset
from src.services.cache import Cache
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.crm_prefix, tags=["crm"])
animals_router_cache: Cache = Cache(owner=router, all_prefix="animals", ttl=settings.default_cache_ttl)
animal_types_router_cache: Cache = Cache(owner=router, all_prefix="animal_types", ttl=settings.default_cache_ttl)
locations_router_cache: Cache = Cache(owner=router, all_prefix="locations", ttl=settings.default_cache_ttl)

@router.get(settings.animals_prefix,  response_model=List[AnimalResponse],
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_animals( query: str  | None = Query(default=None,
                                description="Search query with names or IDs. Default: None"),
                        arrival_date: PastOrPresentDate | None = Query(default=None,
                                                              description="Arrival date. Default: None"),
                        city: str | None = Query(default=None,
                                description="City of collection. Default: None"),
                        animal_types: List[int] | None = Query(default=None,
                                description="List of animal type IDs. Default: None"),
                        gender: Gender | None = Query(default=None,
                                description="Animal gender ('male', 'female'). Default: 'None'"),
                        current_locations: List[int] | None = Query(default=None,
                                description="List of location IDs. Default: None"),
                        animal_state: AnimalState | None = Query(default=AnimalState.active,
                                description="State of animal ('active', 'dead', 'adopted'). Default: 'active'"),
                        is_microchpped: bool | None = Query(default=None,
                                description="Is microchppied? Default: None"),
                        microchpping_date: PastOrPresentDate | None = Query(default=None,
                                description="Microchipping date. Default: None"),
                        is_sterilized: bool | None = Query(default=None,
                                description="Is sterilized? Default: None"),
                        sterilization_date: PastOrPresentDate | None = Query(default=None,
                                description="Sterilization date. Default: None"),
                        is_vaccinated: bool | None = Query(default=None,
                                description="Is vaccinated? Default: None"),
                        vaccination_date: PastOrPresentDate | None = Query(default=None,
                                description="Vaccination date. Default: None"),
                        skip: int | None = Query(default=0, ge=0,
                                description="Records to skip in response"),
                        limit: int | None = Query(default=20, ge=1, le=50,
                                description="Records per response to show"),
                        sorting: Sorting = Depends(),
                        db: AsyncSession = Depends(get_db),
                        current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["crm:read"]),
                        ) -> List[AnimalResponse]:
    """Retrieves an animal by id. Returns the retrieved animal object"""
    cache_key = animals_router_cache.get_all_records_cache_key_with_params(
        query,
        arrival_date,
        city,
        animal_types,
        gender,
        current_locations,
        animal_state,
        is_microchpped,
        microchpping_date,
        is_sterilized,
        sterilization_date,
        is_vaccinated,
        vaccination_date,
        skip,
        limit,
        sorting.sort,
    )
    animals: List[AnimalResponse] = await animals_router_cache.get(key=cache_key)
    if not animals:
        try:
            animals = await animals_repository.read_animals(
                query=query,
                arrival_date=arrival_date,
                city=city,
                animal_types=animal_types,
                gender=gender,
                current_locations=current_locations,
                animal_state=animal_state,
                is_microchpped=is_microchpped,
                microchpping_date=microchpping_date,
                is_sterilized=is_sterilized,
                sterilization_date=sterilization_date,
                is_vaccinated=is_vaccinated,
                vaccination_date=vaccination_date,
                skip=skip,
                limit=limit,
                sort=sorting.sort,
                db=db)
            animals = [AnimalResponse.model_validate(animal) for animal in animals]
        except Exception as err:
            logger.exception("An error occured:\n")
            raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if animals:
            await animals_router_cache.set(key=cache_key, value=animals)
    if not animals:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
    for animal in animals:
        animal.authorize_model_attributes(role=current_user.role)
    return animals


@router.get(settings.animals_prefix + "/{animal_id}",  response_model=AnimalResponse,
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_animal(animal_id: int,
                        db: AsyncSession = Depends(get_db),
                        current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["crm:read"]),
                     ) -> AnimalResponse:
    """Retrieves an animal by id. Returns the retrieved animal object"""
    animal: AnimalResponse | None = None
    try:
        cache_key = animals_router_cache.get_cache_key(str(animal_id))
        animal = await animals_router_cache.get(key=cache_key)
        if not animal:
            animal = await animals_repository.read_animal(animal_id=animal_id, db=db)
            animal = AnimalResponse.model_validate(animal)
            if animal:
                await animals_router_cache.set(key=cache_key, value=animal)
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not animal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
    animal.authorize_model_attributes(role=current_user.role)
    return animal


@router.get("/locations",  response_model=List[LocationResponse],
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_locations(db: AsyncSession = Depends(get_db),
                         _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["crm:read"]),
                        ) -> List[LocationResponse]:
    """Retrieves location definitions. Returns the retrieved locations"""
    locations: List[LocationResponse] = []
    try:
        cache_key = locations_router_cache.get_all_records_cache_key_with_params()
        locations = await locations_router_cache.get(key=cache_key)
        if not locations:
            locations = await animals_repository.read_locations(db=db)
            locations = [LocationResponse.model_validate(location) for location in locations]
            if locations:
                await locations_router_cache.set(key=cache_key, value=locations)
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not locations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_location_not_found)
    return locations


@router.post("/locations", response_model=List[LocationResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_locations(models: List[LocationBase],
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["locations:write"]),
                    ) -> List[LocationResponse]:
    """Creates a new location definition. Returns the created location object"""
    locations: List[Location]
    try:
        locations = [
            location
            for model in models
            if (location := await animals_repository
                .create_location(model=model, db=db))
            is not None
        ]

    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    await locations_router_cache.invalidate_all_keys()
    return locations


@router.get("/animal_types",  response_model=List[AnimalTypeResponse],
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_animal_types(db: AsyncSession = Depends(get_db),
                            _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["crm:read"]),
                            ) -> List[AnimalTypeResponse]:
    """Retrieves animal type definitions. Returns the retrieved animal types"""
    anymal_types: List[AnimalTypeResponse] = []
    try:
        cache_key = animal_types_router_cache.get_all_records_cache_key_with_params()
        anymal_types = await animal_types_router_cache.get(key=cache_key)
        if not anymal_types:
            anymal_types = await animals_repository.read_animal_types(db=db)
            anymal_types = [LocationResponse.model_validate(anymal_type) for anymal_type in anymal_types]
            if anymal_types:
                await animal_types_router_cache.set(key=cache_key, value=anymal_types)
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not anymal_types:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_type_not_found)
    return anymal_types


@router.post("/animal_types", response_model=List[AnimalTypeResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_animal_types(models: List[AnimalTypeBase],
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=[settings.super_user_permission]),
                    ) -> List[AnimalTypeResponse]:
    """Creates a new animal type definition. Returns the created animal type object"""
    animal_types: List[AnimalType]
    try:
        animal_types = [
            animal_type
            for model in models
            if (animal_type := await animals_repository
                .create_animal_type(model=model, db=db))
            is not None
        ]

    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    await animal_types_router_cache.invalidate_all_keys()
    return animal_types


@router.post(settings.animals_prefix, response_model=AnimalResponse, status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_animal(model: AnimalCreate,
                        db: AsyncSession = Depends(get_db),
                        current_user: User = Security(authorization_service.authorize_user, scopes=["animal:create"]),
                    ) -> AnimalResponse:
    """Creates a new animal. Returns the created animal object"""
    try:
        animal = await animals_repository.create_animal(model=model, user=current_user, db=db)

        animal_type = await animals_repository.read_animal_type(animal_type_id=model.general__animal_type.id, db=db)
        if not animal_type:
            raise HTTPException(detail=RETURN_MSG.crm_animal_type_not_found,
                            status_code=status.HTTP_400_BAD_REQUEST)
        animal = await animals_repository.set_animal_type(animal_type=animal_type,
                                                          animal=animal,
                                                          user=current_user,
                                                          db=db)
        animal = await update_handler.handle_update(section_name="locations",
                                                        model=animal,
                                                        update_model=model.locations,
                                                        user=current_user,
                                                        db=db)
        animal = await update_handler.handle_update(section_name="vaccinations",
                                                        model=animal,
                                                        update_model=model.vaccinations,
                                                        user=current_user,
                                                        db=db)
        animal = await update_handler.handle_update(section_name="diagnoses",
                                                        model=animal,
                                                        update_model=model.diagnoses,
                                                        user=current_user,
                                                        db=db)
        animal = await update_handler.handle_update(section_name="procedures",
                                                        model=animal,
                                                        update_model=model.procedures,
                                                        user=current_user,
                                                        db=db)
        animal = await update_handler.handle_update(section_name="media",
                                                        model=animal,
                                                        update_model=model.media,
                                                        user=current_user,
                                                        db=db)

    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    await animals_router_cache.invalidate_all_keys()
    await stats_router_cache.invalidate_all_keys()
    animal = AnimalResponse.model_validate(animal)
    animal.authorize_model_attributes(role=current_user.role)
    return animal


@router.delete(settings.animals_prefix + "/{animal_id}", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def delete_animal(animal_id: int,
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=[settings.super_user_permission]),
                    ) -> None:
    """Deletes the animal by ID"""
    try:
        animal = await animals_repository.read_animal(animal_id=animal_id, db=db)
        cache_key = animals_router_cache.get_cache_key(str(animal_id))
        if not animal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
        await animals_repository.delete_animal(animal=animal, db=db)
        await animals_router_cache.invalidate_key(key=cache_key)
        await animals_router_cache.invalidate_all_keys()
        await stats_router_cache.invalidate_all_keys()
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(settings.animals_prefix + "/{animal_id}/{section_name}",
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def update_animal_section(animal_id: int,
                                section_name: str,
                                body: dict = Body(),
                                db: AsyncSession = Depends(get_db),
                                current_user: User = Security(authorization_service.authorize_user_for_section,
                                                              scopes=["crm:read"], use_cache=False),
                                ) -> AnimalResponse:
    """Updates animal object baased on JSON body. Returns updated animal"""
    animal: Animal = None
    try:
        animal = await animals_repository.read_animal(animal_id=animal_id, db=db)
        if not animal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
        editing_lock = await animals_repository.read_editing_lock(animal_id=animal_id,
                                                                section_name=section_name,
                                                                db=db)
        exprire_delta: timedelta = timedelta(minutes=settings.crm_editing_lock_expire_minutes)
        if (not editing_lock
            or (editing_lock.user.id != current_user.id
                and editing_lock.created_at + exprire_delta < datetime.now(timezone.utc).astimezone())):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=RETURN_MSG.crm_lock_not_found % (section_name, current_user.email))
        if editing_lock.user.id != current_user.id:
            details: str = EditingLockResponse.model_validate(editing_lock).model_dump_json()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=details)
        await animals_repository.delete_editing_lock(editing_lock=editing_lock, db=db)
        section_model: BaseModel = None
        section_model_type: Optional[Type[BaseModel]] = NamedSection.get_section_by_name(section_name=section_name)
        if section_model_type:
            section_model = section_model_type.model_validate(body)
            if section_model:
                animal = await update_handler.handle_update(section_name=section_name,
                                                            model=animal,
                                                            update_model=section_model,
                                                            user=current_user,
                                                            db=db)
                cache_key = animals_router_cache.get_cache_key(str(animal_id))
                await animals_router_cache.invalidate_key(key=cache_key)
                await animals_router_cache.invalidate_all_keys()
                await stats_router_cache.invalidate_all_keys()
        animals_repository.delete_editing_lock(editing_lock=editing_lock, db=db)
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    animal = AnimalResponse.model_validate(animal)
    animal.authorize_model_attributes(role=current_user.role)
    return animal


@router.post(settings.animals_prefix + "/{animal_id}/{section_name}/lock",
             response_model=EditingLockResponse, status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def acquire_lock(animal_id: int,
                              section_name: str,
                              db: AsyncSession = Depends(get_db),
                              current_user: User = Security(authorization_service.authorize_user_for_section,
                                                              scopes=["crm:read"], use_cache=False),
                             ) -> EditingLockResponse:
    """Acquires lock on section for context user. Returns the acquired lock"""
    try:
        editing_lock = await animals_repository.read_editing_lock(animal_id=animal_id,
                                                              section_name=section_name,
                                                              db=db)
        exprire_delta:timedelta = timedelta(minutes=settings.crm_editing_lock_expire_minutes)
        if editing_lock:
            if (editing_lock.user.id != current_user.id
                    and editing_lock.created_at + exprire_delta >= datetime.now(timezone.utc).astimezone()):
                details: str = EditingLockResponse.model_validate(editing_lock).model_dump_json()
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=details)
            if (editing_lock.user.id == current_user.id
                    and editing_lock.created_at + exprire_delta >= datetime.now(timezone.utc).astimezone()):
                return editing_lock
            await animals_repository.delete_editing_lock(editing_lock=editing_lock, db=db)

        editing_lock = await animals_repository.create_editing_lock(animal_id=animal_id,
                                                                    section_name=section_name,
                                                                    user=current_user,
                                                                    db=db)
    except Exception:
        logger.exception("An error occured:\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=RETURN_MSG.crm_acquire_lock_failed % (section_name, current_user.email))
    return editing_lock

@router.delete(settings.animals_prefix + "/{animal_id}/{section_name}/lock", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def release_lock(animal_id: int,
                        section_name: str,
                        db: AsyncSession = Depends(get_db),
                        current_user: User = Security(authorization_service.authorize_user_for_section,
                                                        scopes=["crm:read"], use_cache=False),
                    ) -> None:
    """Deletes the animal by ID"""
    try:
        editing_lock = await animals_repository.read_editing_lock(animal_id=animal_id,
                                                                section_name=section_name,
                                                                db=db)
        if not editing_lock:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=RETURN_MSG.crm_lock_not_found % (section_name, current_user.email))
        if editing_lock.user.id != current_user.id:
            details: str = EditingLockResponse.model_validate(editing_lock).model_dump_json()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=details)
        await animals_repository.delete_editing_lock(editing_lock=editing_lock, db=db)
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("An error occured:\n")
        raise HTTPException(detail=jsonable_encoder(err.args), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
