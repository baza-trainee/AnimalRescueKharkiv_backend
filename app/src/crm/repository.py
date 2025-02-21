import logging
import re
import uuid
from datetime import date
from typing import Any, Callable, List, Tuple, TypeVar
from uuid import UUID

import uvicorn
from sqlalchemy import Select, and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import ColumnElement, ColumnExpressionArgument
from sqlalchemy.sql.elements import UnaryExpression
from src.base_schemas import SORTING_VALIDATION_REGEX
from src.configuration.settings import settings
from src.crm.models import (
    Animal,
    AnimalLocation,
    AnimalType,
    Diagnosis,
    EditingLock,
    Gender,
    Location,
    Procedure,
    Vaccination,
)
from src.crm.schemas import (
    AnimalCreate,
    AnimalLocationBase,
    AnimalLocationUpdate,
    AnimalState,
    AnimalTypeBase,
    BaseModel,
    DiagnosisBase,
    DiagnosisUpdate,
    IntReferenceBase,
    LocationBase,
    ProcedureBase,
    ProcedureUpdate,
    UUIDReferenceBase,
    VaccinationBase,
    VaccinationUpdate,
)
from src.exceptions.exceptions import RETURN_MSG
from src.media.models import MediaAsset
from src.singleton import SingletonMeta
from src.users.models import User

_T = TypeVar("_T")

logger = logging.getLogger(uvicorn.logging.__name__)


class AnimalsRepository(metaclass=SingletonMeta):
    async def create_location(self, model: LocationBase, db: AsyncSession) -> Location:
        """Creates a location definition. Returns the created location definition"""
        location = Location(name=model.name)
        db.add(location)
        await db.commit()
        await db.refresh(location)
        return location

    async def create_animal_type(self, model: AnimalTypeBase, db: AsyncSession) -> AnimalType:
        """Creates an animal type definition. Returns the created animal type definition"""
        animal_type = AnimalType(name=model.name)
        db.add(animal_type)
        await db.commit()
        await db.refresh(animal_type)
        return animal_type

    async def add_vaccination_to_animal(self,
                                        model: VaccinationBase,
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
                                      model: DiagnosisBase,
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
                                      model: ProcedureBase,
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
                                  definition: MediaAsset,
                                  animal: Animal,
                                  user: User,
                                  db: AsyncSession) -> Animal:
        """Adds a media to animal. Returns the updated animal"""
        user = await db.merge(user)
        animal.media.append(definition)
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
                                  definition:Location,
                                  model:AnimalLocationBase,
                                  animal: Animal,
                                  user: User,
                                  db: AsyncSession) -> Animal:
        """Adds the animal location. Returns the updated animal"""
        user = await db.merge(user)
        animal_location = AnimalLocation(animal=animal,
                                         location=definition,
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
        if not re.match(SORTING_VALIDATION_REGEX, sort):
            raise ValueError(RETURN_MSG.illegal_sort)
        field, direction = sort.split("|", 1)
        match direction.lower():
            case "asc":
                return asc(getattr(Animal, field))
            case "desc":
                return desc(getattr(Animal, field))
        return desc(Animal.created_at)

    def __filter(self,
                       statement: Select[Tuple[DeclarativeBase]],
                       parameter: object | None,
                       expression: Callable[[Any], ColumnElement[bool]]) -> Select[Tuple[DeclarativeBase]]:
        if parameter is not None:
            statement = statement.filter(expression(parameter))
        return statement

    async def read_animals(self,
                            db: AsyncSession,
                            query: str | None = None,
                            arrival_date: date | None = None,
                            city: str | None = None,
                            animal_types: List[int] | None = None,
                            gender: Gender | None = None,
                            current_locations: List[int] | None = None,
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
        statement = self.__filter(statement, arrival_date, lambda x: Animal.origin__arrival_date == x)
        statement = self.__filter(statement, city, lambda x: Animal.origin__city == x)
        statement = self.__filter(statement, animal_types, lambda x: Animal.general__animal_type_id.in_(x))
        statement = self.__filter(statement, gender, lambda x: Animal.general__gender == x)
        statement = self.__filter(statement, current_locations,
                                  lambda x: func.max(Animal.locations).any_(Location.id.in_(x)))
        if animal_state is not None:
            match animal_state:
                case AnimalState.active:
                    statement = statement.filter(and_(Animal.death__dead == False, #noqa: E712
                                                      Animal.adoption__date == None)) #noqa: E711
                case AnimalState.dead:
                    statement = statement.filter(Animal.death__dead == True) #noqa: E712
                case AnimalState.adopted:
                    statement = statement.filter(Animal.adoption__date != None) #noqa: E711
        statement = self.__filter(statement, is_microchpped, lambda x: Animal.microchipping__done == x)
        statement = self.__filter(statement, microchpping_date, lambda x: Animal.microchipping__date == x)
        statement = self.__filter(statement, is_sterilized, lambda x: Animal.sterilization__done == x)
        statement = self.__filter(statement, sterilization_date, lambda x: Animal.sterilization__date == x)
        if is_vaccinated is not None:
            match is_vaccinated:
                case True:
                    statement = statement.filter(Animal.vaccinations.any())
                case False:
                    statement = statement.filter(~Animal.vaccinations.any())
        statement = self.__filter(statement, vaccination_date,
                                  lambda x: Animal.vaccinations.any(Vaccination.date == x))
        statement = statement.offset(skip).limit(limit)
        if sort:
            statement = statement.order_by(self.__get_order_expression(sort=sort))
        result = await db.execute(statement)
        animals = result.unique().scalars().all()
        return list(animals)

    async def read_animal_type(self, animal_type_id: int, db: AsyncSession) -> AnimalType | None:
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

    async def read_location(self, location_id: int, db: AsyncSession) -> Location | None:
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

    async def update_animal_fields(self,
                                   update_model: BaseModel,
                                   model: Animal,
                                   user: User,
                                   db: AsyncSession,
                                  ) -> Animal:
        """Updates simple animal fields. Returns the updated animal"""
        if model:
            user = await db.merge(user)
            for field_name in update_model.model_fields:
                field = getattr(update_model, field_name, None)
                if isinstance(field, UUIDReferenceBase):
                    continue
                if isinstance(field, IntReferenceBase):
                    setattr(model, f"{field_name}_id", field.id)
                else:
                    setattr(model, field_name, field)
            model.updated_by = user
            db.add(model)
            await db.commit()
            await db.refresh(model)
        return model

    async def update_animal_location(self,
                                     update_model: AnimalLocationUpdate,
                                     definition: Location,
                                     model: AnimalLocation,
                                     user: User,
                                     db: AsyncSession,
                                    ) -> Animal:
        """Updates animal location. Returns the updated animal"""
        if model:
            user = await db.merge(user)
            if update_model.date_from:
                model.date_from = update_model.date_from
            if update_model.date_to:
                model.date_to = update_model.date_to
            model.location = definition
            model.animal.updated_by = user
            db.add(model)
            await db.commit()
            await db.refresh(model)
        return model.animal

    async def update_vaccination(self,
                                 update_model: VaccinationUpdate,
                                 model: Vaccination,
                                 user: User,
                                 db: AsyncSession,
                                ) -> Animal:
        """Updates animal vaccination. Returns the updated animal"""
        if model:
            user = await db.merge(user)
            if update_model.date:
                model.date = update_model.date
            if update_model.is_vaccinated is not None:
                model.is_vaccinated = update_model.is_vaccinated
            if update_model.vaccine_type:
                model.vaccine_type = update_model.vaccine_type
            if update_model.comment:
                model.comment = update_model.comment
            model.animal.updated_by = user
            db.add(model)
            await db.commit()
            await db.refresh(model)
        return model.animal

    async def update_procedure(self,
                               update_model: ProcedureUpdate,
                               model: Procedure,
                               user: User,
                               db: AsyncSession,
                              ) -> Animal:
        """Updates animal procedure. Returns the updated animal"""
        if model:
            user = await db.merge(user)
            if update_model.date:
                model.date = update_model.date
            if update_model.name:
                model.name = update_model.name
            if update_model.comment:
                model.comment = update_model.comment
            model.animal.updated_by = user
            db.add(model)
            await db.commit()
            await db.refresh(model)
        return model.animal

    async def update_diagnosis(self,
                               update_model: DiagnosisUpdate,
                               model: Diagnosis,
                               user: User,
                               db: AsyncSession,
                              ) -> Animal:
        """Updates animal diagnosis. Returns the updated animal"""
        if model:
            user = await db.merge(user)
            if update_model.date:
                model.date = update_model.date
            if update_model.name:
                model.name = update_model.name
            if update_model.comment:
                model.comment = update_model.comment
            model.animal.updated_by = user
            db.add(model)
            await db.commit()
            await db.refresh(model)
        return model.animal

    async def read_editing_lock(self,
                                animal_id: int,
                                section_name: str,
                                db: AsyncSession,
                               ) -> EditingLock | None:
        """Reads an editing lock by animal id and section name. Returns the retrieved lock record"""
        statement = select(EditingLock)
        statement = statement.filter_by(animal_id=animal_id, section_name=section_name)
        result = await db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def create_editing_lock(self,
                                animal_id: int,
                                section_name: str,
                                user: User,
                                db: AsyncSession,
                              ) -> EditingLock:
        """Creates an editing lock by animal id and section name for the user. Returns the created lock record"""
        user = await db.merge(user)
        editing_lock = EditingLock(animal_id=animal_id,
                                  user=user,
                                  section_name=section_name)
        db.add(editing_lock)
        await db.commit()
        await db.refresh(editing_lock)
        return editing_lock

    async def delete_editing_lock(self,
                                  editing_lock: EditingLock,
                                  db: AsyncSession,
                                 ) -> EditingLock:
        """Deletes editing lock"""
        if editing_lock:
            await db.delete(editing_lock)
            await db.commit()
        return editing_lock

animals_repository:AnimalsRepository = AnimalsRepository()
