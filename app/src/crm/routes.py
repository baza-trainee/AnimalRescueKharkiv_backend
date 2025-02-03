import logging
from typing import Awaitable, Callable, List
from uuid import UUID

import uvicorn
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.encoders import jsonable_encoder
from fastapi_limiter.depends import RateLimiter
from pydantic import PastDate, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from src.authorization.service import authorization_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.crm.models import AnimalType, Gender, Location
from src.crm.repository import animals_repository
from src.crm.schemas import (
    AnimalCreate,
    AnimalResponse,
    AnimalState,
    AnimalTypeCreate,
    AnimalTypeResponse,
    BaseModel,
    LocationCreate,
    LocationResponse,
    Sorting,
)
from src.exceptions.exceptions import RETURN_MSG
from src.media.models import MediaAsset
from src.services.cache import Cache
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.crm_prefix, tags=["crm"])
animals_router_cache: Cache = Cache(owner=router, all_prefix="animals", ttl=settings.default_cache_ttl)
animal_types_router_cache: Cache = Cache(owner=router, all_prefix="animal_types", ttl=settings.default_cache_ttl)
locations_router_cache: Cache = Cache(owner=router, all_prefix="locations", ttl=settings.default_cache_ttl)

@router.get(settings.animals_prefix,  response_model=List[AnimalResponse])
async def read_animals( query: str  | None = Query(default=None,
                                description="Search query with names or IDs. Default: None"),
                        arrival_date: PastDate | None = Query(default=None,
                                                              description="Arrival date. Default: None"),
                        city: str | None = Query(default=None,
                                description="City of collection. Default: None"),
                        animal_types: List[UUID] | None = Query(default=None,
                                description="List of animal type IDs. Default: None"),
                        gender: Gender | None = Query(default=None,
                                description="Animal gender ('male', 'female'). Default: 'male'"),
                        current_locations: List[UUID] | None = Query(default=None,
                                description="List of location IDs. Default: None"),
                        animal_state: AnimalState | None = Query(default=AnimalState.active,
                                description="State of animal ('active', 'dead', 'adopted'). Default: 'active'"),
                        is_microchpped: bool | None = Query(default=None,
                                description="Is microchppied? Default: True"),
                        microchpping_date: PastDate | None = Query(default=None,
                                description="Microchipping date. Default: None"),
                        is_sterilized: bool | None = Query(default=None,
                                description="Is sterilized? Default: True"),
                        sterilization_date: PastDate | None = Query(default=None,
                                description="Sterilization date. Default: None"),
                        is_vaccinated: bool | None = Query(default=None,
                                description="Is vaccinated? Default: True"),
                        vaccination_date: PastDate | None = Query(default=None,
                                description="Vaccination date. Default: None"),
                        skip: int | None = Query(default=0, ge=0,
                                description="Records to skip in response"),
                        limit: int | None = Query(default=20, ge=1, le=50,
                                description="Records per response to show"),
                        sorting: Sorting = Depends(),
                        db: AsyncSession = Depends(get_db)) -> List[AnimalResponse]:
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
        if animals:
            await animals_router_cache.set(key=cache_key, value=animals)
    if not animals:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
    return animals


@router.get(settings.animals_prefix + "/{animal_id}",  response_model=AnimalResponse)
async def read_animal(animal_id: int,
                        db: AsyncSession = Depends(get_db)) -> AnimalResponse:
    """Retrieves an animal by id. Returns the retrieved animal object"""
    cache_key = animals_router_cache.get_cache_key(str(animal_id))
    animal: AnimalResponse = await animals_router_cache.get(key=cache_key)
    if not animal:
        animal = await animals_repository.read_animal(animal_id=animal_id, db=db)
        animal = AnimalResponse.model_validate(animal)
        if animal:
            await animals_router_cache.set(key=cache_key, value=animal)
    if not animal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
    return animal


@router.get("/locations",  response_model=List[LocationResponse])
async def read_locations(db: AsyncSession = Depends(get_db)) -> List[LocationResponse]:
    """Retrieves location definitions. Returns the retrieved locations"""
    cache_key = locations_router_cache.get_all_records_cache_key_with_params()
    locations: List[LocationResponse] = await locations_router_cache.get(key=cache_key)
    if not locations:
        locations = await animals_repository.read_locations(db=db)
        locations = [LocationResponse.model_validate(location) for location in locations]
        if locations:
            await locations_router_cache.set(key=cache_key, value=locations)
    if not locations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_location_not_found)
    return locations


@router.post("/locations", response_model=List[LocationResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_locations(models: List[LocationCreate],
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user, scopes=["location:write"]),
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
    await locations_router_cache.invalidate_all_keys()
    return locations


@router.get("/animal_types",  response_model=List[AnimalTypeResponse])
async def read_animal_types(db: AsyncSession = Depends(get_db)) -> List[AnimalTypeResponse]:
    """Retrieves animal type definitions. Returns the retrieved animal types"""
    cache_key = animal_types_router_cache.get_all_records_cache_key_with_params()
    anymal_types: List[AnimalTypeResponse] = await animal_types_router_cache.get(key=cache_key)
    if not anymal_types:
        anymal_types = await animals_repository.read_animal_types(db=db)
        anymal_types = [LocationResponse.model_validate(anymal_type) for anymal_type in anymal_types]
        if anymal_types:
            await animal_types_router_cache.set(key=cache_key, value=anymal_types)
    if not anymal_types:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_type_not_found)
    return anymal_types


@router.post("/animal_types", response_model=List[AnimalTypeResponse], status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_animal_types(models: List[AnimalTypeCreate],
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user, scopes=["system:admin"]),
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
    await animal_types_router_cache.invalidate_all_keys()
    return animal_types


async def __add_references(model: DeclarativeBase,
                           references: List[BaseModel],
                           func: Callable[..., Awaitable[DeclarativeBase]],
                           user: User,
                           db: AsyncSession,
                           ) -> DeclarativeBase:
    if references:
        for ref_model in references:
            model = await func(
                model=ref_model,
                animal=model,
                user=user,
                db=db)
    return model

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
        if model.locations:
            for location_model in model.locations:
                location = await animals_repository.read_location(location_id=location_model.location.id, db=db)
                if location:
                    animal = await animals_repository.add_animal_location(model=location_model,
                                                                          location=location,
                                                                          animal=animal,
                                                                          user=current_user,
                                                                          db=db)
        animal = await __add_references(model=animal,
                                        references=model.vaccinations,
                                        func=animals_repository.add_vaccination_to_animal,
                                        user=current_user,
                                        db=db)
        animal = await __add_references(model=animal,
                                        references=model.diagnoses,
                                        func=animals_repository.add_diagnosis_to_animal,
                                        user=current_user,
                                        db=db)
        animal = await __add_references(model=animal,
                                        references=model.procedures,
                                        func=animals_repository.add_procedure_to_animal,
                                        user=current_user,
                                        db=db)
        animal = await __add_references(model=animal,
                                        references=model.media,
                                        func=animals_repository.add_media_to_animal,
                                        user=current_user,
                                        db=db)

    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)
    await animals_router_cache.invalidate_all_keys()
    return AnimalResponse.model_validate(animal)


@router.delete(settings.animals_prefix + "/{animal_id}", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def delete_animal(animal_id: int,
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user, scopes=["system:admin"]),
                    ) -> None:
    """Deletes the animal by ID"""
    animal = await animals_repository.read_animal(animal_id=animal_id, db=db)
    cache_key = animals_router_cache.get_cache_key(str(animal_id))
    if not animal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.crm_animal_not_found)
    await animals_repository.delete_animal(animal=animal, db=db)
    await animals_router_cache.invalidate_key(key=cache_key)
    await animals_router_cache.invalidate_all_keys()
