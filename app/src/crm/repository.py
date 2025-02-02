import logging
import re
import uuid
from datetime import date
from typing import List, TypeVar
from uuid import UUID

import uvicorn
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy.sql import ColumnElement, ColumnExpressionArgument
from sqlalchemy.sql.elements import UnaryExpression
from src.configuration.settings import settings
from src.crm.models import Animal, AnimalLocation, AnimalType, Diagnosis, Gender, Location, Procedure, Vaccination
from src.crm.schemas import (
    AnimalCreate,
    AnimalLocationCreate,
    AnimalState,
    AnimalTypeCreate,
    DiagnosisCreate,
    LocationCreate,
    ProcedureCreate,
    VaccinationCreate,
)
from src.exceptions.exceptions import RETURN_MSG
from src.media.models import MediaAsset
from src.permissions.models import Permission
from src.singleton import SingletonMeta
from src.users.models import User

_T = TypeVar("_T")

logger = logging.getLogger(uvicorn.logging.__name__)


class AnimalsRepository(metaclass=SingletonMeta):
    async def create_location(self, model: LocationCreate, db: AsyncSession) -> Location:
        """Creates a location definition. Returns the created location definition"""
        location = Location(name=model.name)
        db.add(location)
        await db.commit()
        await db.refresh(location)
        return location

    async def create_animal_type(self, model: AnimalTypeCreate, db: AsyncSession) -> AnimalType:
        """Creates an animal type definition. Returns the created animal type definition"""
        animal_type = AnimalType(name=model.name)
        db.add(animal_type)
        await db.commit()
        await db.refresh(animal_type)
        return animal_type

    async def add_vaccination_to_animal(self,
                                        model: VaccinationCreate,
                                        animal: Animal,
                                        user: User,
                                        db: AsyncSession) -> Animal:
        """Adds a vaccination to animal. Returns the updated animal"""
        user = await db.merge(user)
        vaccination = Vaccination(is_vaccinated=model.is_vaccinated,
                                  vaccine_type=model.vaccine_type,
                                  date=model.date,
                                  comment=model.comment)
        animal.vaccinations.append(vaccination)
        animal.updated_by = user
        await db.commit()
        await db.refresh(animal)
        return animal

    async def add_diagnosis_to_animal(self,
                                      model: DiagnosisCreate,
                                      animal: Animal,
                                      user: User,
                                      db: AsyncSession) -> Animal:
        """Adds a diagnosis to animal. Returns the updated animal"""
        user = await db.merge(user)
        diagnosis = Diagnosis(name=model.name,
                                  date=model.date,
                                  comment=model.comment)
        animal.diagnoses.append(diagnosis)
        animal.updated_by = user
        await db.commit()
        await db.refresh(animal)
        return animal

    async def add_procedure_to_animal(self,
                                      model: ProcedureCreate,
                                      animal: Animal,
                                      user: User,
                                      db: AsyncSession) -> Animal:
        """Adds a procedure to animal. Returns the updated animal"""
        user = await db.merge(user)
        procedure = Procedure(name=model.name,
                                  date=model.date,
                                  comment=model.comment)
        animal.procedures.append(procedure)
        animal.updated_by = user
        await db.commit()
        await db.refresh(animal)
        return animal

    async def add_media_to_animal(self,
                                  media: MediaAsset,
                                  animal: Animal,
                                  user: User,
                                  db: AsyncSession) -> Animal:
        """Adds a media to animal. Returns the updated animal"""
        user = await db.merge(user)
        animal.media.append(media)
        animal.updated_by = user
        await db.commit()
        await db.refresh(animal)
        return animal

    async def set_animal_type(self,
                              animal_type: AnimalType,
                              animal: Animal,
                              user: User,
                              db: AsyncSession) -> Animal:
        """Sets the animal type. Returns the updated animal"""
        user = await db.merge(user)
        animal.general__animal_type = animal_type
        animal.updated_by = user
        await db.commit()
        await db.refresh(animal)
        return animal

    async def add_animal_location(self,
                                  model:AnimalLocationCreate,
                                  location:Location,
                                  animal: Animal,
                                  user: User,
                                  db: AsyncSession) -> Animal:
        """Adds the animal location. Returns the updated animal"""
        user = await db.merge(user)
        animal_location = AnimalLocation(animal=animal,
                                         location=location,
                                         date_from=model.date_from,
                                         date_to=model.date_to)
        animal.locations.append(animal_location)
        animal.updated_by = user
        await db.commit()
        await db.refresh(animal)
        return animal

    async def create_animal(self,
                            model: AnimalCreate,
                            user: User,
                            db: AsyncSession) -> Animal:
        """Creates an animal definition. Returns the created animal definition"""
        user = await db.merge(user)
        animal = Animal(name=model.name,
                        origin__arrival_date=model.origin__arrival_date,
                        origin__city=model.origin__city,
                        origin__address=model.origin__address,
                        general__gender=model.general__gender,
                        general__weight=model.general__weight,
                        general__age=model.general__age,
                        general__specials=model.general__specials,
                        owner__info=model.owner__info,
                        comment__text=model.comment__text,
                        adoption__country=model.adoption__country,
                        adoption__city=model.adoption__city,
                        adoption__date=model.adoption__date,
                        adoption__comment=model.adoption__comment,
                        death__dead=model.death__dead,
                        death__date=model.death__date,
                        death__comment=model.death__comment,
                        sterilization__done=model.sterilization__done,
                        sterilization__date=model.sterilization__date,
                        sterilization__comment=model.sterilization__comment,
                        microchipping__done=model.microchipping__done,
                        microchipping__date=model.microchipping__date,
                        microchipping__comment=model.microchipping__comment,
                        created_by=user,
                        updated_by=user)
        db.add(animal)
        await db.commit()
        await db.refresh(animal)
        return animal

    async def read_animal(self, animal_id: int, db: AsyncSession) -> Animal | None:
        """Reads an animal by id. Returns the retrieved animal"""
        statement = select(Animal)
        statement = statement.filter_by(id=animal_id)
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    def __get_name_id_condition(self, query: str) -> ColumnElement[bool] | None:
        terms = re.split(r"[;,|\s]+", query)
        ids: List[int] = []
        names: List[str] = []
        for term in terms:
            if term.isdigit():
                ids.append(int(term))
            else:
                names.append(term.lower())

        expression: List[ColumnExpressionArgument[bool]] = []
        if ids:
            expression.append(Animal.id.in_(ids))
        if names:
            expression.append(func.lower(Animal.name).in_(names))
        return or_(*expression)

    def __get_order_expression(self, sort: str) -> UnaryExpression[_T]:
        if "|" not in sort:
            raise ValueError(RETURN_MSG.crm_illegal_sort)
        field, direction = sort.split("|", 1)
        match direction.lower():
            case "asc":
                return asc(getattr(Animal, field))
            case "desc":
                return desc(getattr(Animal, field))
        return desc(Animal.created_at)

    async def read_animals(self, #noqa: C901, PLR0912
                            db: AsyncSession,
                            query: str | None = None,
                            arrival_date: date | None = None,
                            city: str | None = None,
                            animal_types: List[UUID] | None = None,
                            gender: Gender | None = None,
                            current_locations: List[UUID] | None = None,
                            animal_state: AnimalState | None = None,
                            is_microchpped: bool | None = None,
                            microchpping_date: date | None = None,
                            is_sterilized: bool | None = None,
                            sterilization_date: date | None = None,
                            is_vaccinated: bool | None = None,
                            vaccination_date: date | None = None,
                            skip: int = 0,
                            limit: int = 20,
                            sort: str | None = "created_at|desc") -> List[Animal]:
        """Reads animals with optional filtering. Returns the retrieved animals"""
        statement = select(Animal)
        if query is not None:
            condition: ColumnElement[bool] | None = self.__get_name_id_condition(query=query)
            if condition is not None:
                statement = statement.filter(condition)
        if arrival_date is not None:
            statement = statement.filter_by(origin__arrival_date = arrival_date)
        if city is not None:
            statement = statement.filter_by(origin__city = city)
        if animal_types is not None:
            statement = statement.filter(Animal.general__animal_type_id.in_(animal_types))
        if gender is not None:
            statement = statement.filter_by(general__gender = gender)
        if current_locations is not None:
             statement = statement.filter(Animal.locations.any(Location.id.in_(current_locations)))
        if animal_state is not None:
            match animal_state:
                case AnimalState.active:
                    statement = statement.filter(and_(Animal.death__dead == False, #noqa: E712
                                                      Animal.adoption__date is None))
                case AnimalState.dead:
                    statement = statement.filter(Animal.death__dead == True) #noqa: E712
                case AnimalState.adopted:
                    statement = statement.filter(Animal.adoption__date is not None)
        if is_microchpped is not None:
            statement = statement.filter_by(microchipping__done = is_microchpped)
        if microchpping_date is not None:
            statement = statement.filter(Animal.microchipping__date == microchpping_date)
        if is_sterilized is not None:
            statement = statement.filter_by(sterilization__done = is_sterilized)
        if sterilization_date is not None:
            statement = statement.filter(Animal.sterilization__date == sterilization_date)
        if is_vaccinated is not None:
            match is_vaccinated:
                case True:
                    statement = statement.filter(Animal.vaccinations.any())
                case False:
                    statement = statement.filter(~Animal.vaccinations.any())
        if vaccination_date is not None:
            statement = statement.filter(Animal.vaccinations.any(Vaccination.date == vaccination_date))
        statement = statement.offset(skip).limit(limit)
        if sort:
            statement = statement.order_by(self.__get_order_expression(sort=sort))
        result = await db.execute(statement)
        animals = result.unique().scalars().all()
        return list(animals)

    async def read_animal_type(self, animal_type_id: uuid.UUID, db: AsyncSession) -> AnimalType | None:
        """Reads an animal type by id. Returns the retrieved animal type"""
        statement = select(AnimalType)
        statement = statement.filter_by(id=animal_type_id)
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def read_animal_types(self, db: AsyncSession) -> List[AnimalType]:
        """Reads all animal types. Returns the retrieved animal types"""
        statement = select(AnimalType)
        result = await db.execute(statement)
        return result.unique().scalars().all()

    async def read_location(self, location_id: uuid.UUID, db: AsyncSession) -> Location | None:
        """Reads a location by id. Returns the retrieved location"""
        statement = select(Location)
        statement = statement.filter_by(id=location_id)
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def read_locations(self, db: AsyncSession) -> List[Location]:
        """Reads all locations. Returns the retrieved locations"""
        statement = select(Location)
        result = await db.execute(statement)
        return result.unique().scalars().all()

    async def delete_animal(self, animal:Animal, db: AsyncSession) -> Animal:
        """Delets animal card"""
        if animal:
            await db.delete(animal)
            await db.commit()
        return animal



animals_repository:AnimalsRepository = AnimalsRepository()
