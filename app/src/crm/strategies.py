import logging
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List
from uuid import UUID

import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from src.configuration.settings import settings
from src.crm.models import Animal
from src.crm.repository import animals_repository
from src.crm.schemas import (
    BaseModel,
    IntReferenceBase,
)
from src.exceptions.exceptions import RETURN_MSG
from src.media.models import MediaAsset
from src.media.repository import media_repository
from src.singleton import SingletonMeta
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)

class UpdateStrategy(ABC):
    @abstractmethod
    async def update(self,
                     model: Animal,
                     update_model: BaseModel,
                     user: User,
                     db: AsyncSession,
                    ) -> Animal:
        """Updates animal based on passed model. Returns the updated animal"""

class UpdateAttrsStrategy(UpdateStrategy):
    def __init__(self,
                 not_fount_msg: str | None = None,
                 read_def_func: Callable[[int, AsyncSession], Awaitable[DeclarativeBase]] | None = None,
                ) -> None:
        """Initializes strategy"""
        self.__not_fount_msg: str | None = not_fount_msg
        self.__read_def_func: Callable[[int, AsyncSession], Awaitable[DeclarativeBase]] | None = read_def_func

    async def update(self,
                     model: Animal,
                     update_model: BaseModel,
                     user: User,
                     db: AsyncSession,
                    ) -> Animal:
        """Updates animal based on passed model. Returns the updated animal"""
        if not update_model:
            return model
        definition: DeclarativeBase = None
        for field_name in update_model.model_fields:
                field = getattr(update_model, field_name, None)
                if isinstance(field, IntReferenceBase) and self.__read_def_func:
                    definition = await self.__read_def_func(field.id, db)
                    if not definition:
                        raise ValueError(self.__not_fount_msg)

        return await animals_repository.update_animal_fields(
            update_model=update_model,
            model=model,
            user=user,
            db=db)

class UpdateRefsStrategy(UpdateStrategy):
    def __init__(self,
                 ref_name: str,
                 add_func: Callable[...,Awaitable[DeclarativeBase]] | None = None,
                 read_def_func: Callable[[int | UUID, AsyncSession], Awaitable[DeclarativeBase]] | None = None,
                 read_def_id_type: type = IntReferenceBase,
                 update_func: Callable[..., Awaitable[DeclarativeBase]] | None = None,
                 *,
                 add_func_model_supported: bool = True,
                ) -> None:
        """Initializes strategy"""
        self.__ref_name: str = ref_name
        self.__add_func: Callable[...,Awaitable[DeclarativeBase]] | None = add_func
        self.__read_def_func: Callable[[int | UUID, AsyncSession], Awaitable[DeclarativeBase]] | None = read_def_func
        self.__read_def_id_type: type = read_def_id_type
        self.__update_func: Callable[..., Awaitable[DeclarativeBase]] | None = update_func
        self.__def_id_accessor: Callable[[Any], Any] = ((lambda x: x)
                                                        if self.__read_def_id_type == UUID
                                                        else (lambda x: x.id))
        self.__add_func_model_supported = add_func_model_supported

    async def update(self,
                     model: Animal,
                     update_model: BaseModel,
                     user: User,
                     db: AsyncSession,
                    ) -> Animal:
        """Updates animal based on passed model. Returns the updated animal"""
        if not update_model:
            return model
        refs: List[BaseModel] = update_model if isinstance(update_model, list) else []
        if not refs:
            for field_name in update_model.model_fields:
                    field = getattr(update_model, field_name, None)
                    if isinstance(field, list):
                        refs = field
        for ref in refs:
            model = await self.__update_single(model=model,
                                 update_model=ref,
                                 user=user,
                                 db=db)
        return model

    def __get_ref_by_id(self, ref_id:UUID, model: Animal) -> DeclarativeBase | None:
        references: List[DeclarativeBase] | None = getattr(model, self.__ref_name, None)
        if references:
            return next((ref for ref in references if ref.id == ref_id), None)
        return None

    async def __update_single(self,
                     model: Animal,
                     update_model: BaseModel,
                     user: User,
                     db: AsyncSession,
                    ) -> Animal:
        ref_obj: DeclarativeBase = None
        definition: DeclarativeBase = None
        for field_name in update_model.model_fields:
                field = getattr(update_model, field_name, None)
                if isinstance(field, UUID):
                    ref_obj = self.__get_ref_by_id(ref_id=field, model=model)
                if isinstance(field, self.__read_def_id_type) and self.__read_def_func:
                    def_id = self.__def_id_accessor(field)
                    definition = await self.__read_def_func(def_id , db)
                    if not definition:
                        raise ValueError(RETURN_MSG.definition_for_model_not_found % (def_id, field_name))
        if ref_obj:
            model = await self.__update_reference(model=model,
                                                  ref_obj=ref_obj,
                                                  definition=definition,
                                                  update_model=update_model,
                                                  user=user,
                                                  db=db)
        else:
            model = await self.__add_reference(model=model,
                                               update_model=update_model,
                                               definition=definition,
                                               user=user,
                                               db=db)
        return model

    async def __add_reference(self,
                              model: Animal,
                              update_model: BaseModel,
                              definition: DeclarativeBase,
                              user: User,
                              db: AsyncSession,
                             ) -> Animal:
        if not self.__add_func:
            return model

        if definition:
            if self.__add_func_model_supported:
                model = await self.__add_func(
                            definition=definition,
                            model=update_model,
                            animal=model,
                            user=user,
                            db=db)
            else:
                model = await self.__add_func(
                            definition=definition,
                            animal=model,
                            user=user,
                            db=db)
        elif not self.__read_def_func:
            model = await self.__add_func(
                        model=update_model,
                        animal=model,
                        user=user,
                        db=db)
        return model

    async def __update_reference(self,
                              model: Animal,
                              ref_obj: DeclarativeBase,
                              definition: DeclarativeBase,
                              update_model: BaseModel,
                              user: User,
                              db: AsyncSession,
                            ) -> Animal:
        if not self.__update_func:
            return model

        if definition:
            model = await self.__update_func(update_model=update_model,
                                                definition=definition,
                                                model=ref_obj,
                                                user=user,
                                                db=db)
        elif not self.__read_def_func:
            model = await self.__update_func(update_model=update_model,
                                                model=ref_obj,
                                                user=user,
                                                db=db)
        return model


class UpdateHanlder(metaclass=SingletonMeta):
    def __init__(self) -> None:
        """Initializes Update Handler with startegies"""
        self.__strategies: Dict[str, UpdateStrategy] = self.__init_strategies()

    def __init_strategies(self) -> Dict[str, UpdateStrategy]:
        return {
            "name": UpdateAttrsStrategy(),
            "origin": UpdateAttrsStrategy(),
            "general": UpdateAttrsStrategy(not_fount_msg=RETURN_MSG.crm_animal_type_not_found,
                                           read_def_func=animals_repository.read_animal_type),
            "owner": UpdateAttrsStrategy(),
            "comment": UpdateAttrsStrategy(),
            "adoption": UpdateAttrsStrategy(),
            "death": UpdateAttrsStrategy(),
            "sterilization": UpdateAttrsStrategy(),
            "microchipping": UpdateAttrsStrategy(),
            "media": UpdateRefsStrategy(ref_name="media",
                                        read_def_func=media_repository.read_media_asset,
                                        read_def_id_type=UUID,
                                        add_func=animals_repository.add_media_to_animal,
                                        add_func_model_supported=False),
            "locations": UpdateRefsStrategy(ref_name="locations",
                                            add_func=animals_repository.add_animal_location,
                                            read_def_func=animals_repository.read_location,
                                            update_func=animals_repository.update_animal_location),
            "vaccinations": UpdateRefsStrategy(ref_name="vaccinations",
                                            add_func=animals_repository.add_vaccination_to_animal,
                                            update_func=animals_repository.update_vaccination),
            "diagnoses": UpdateRefsStrategy(ref_name="diagnoses",
                                            add_func=animals_repository.add_diagnosis_to_animal,
                                            update_func=animals_repository.update_diagnosis),
            "procedures": UpdateRefsStrategy(ref_name="procedures",
                                            add_func=animals_repository.add_procedure_to_animal,
                                            update_func=animals_repository.update_procedure),
        }

    async def handle_update(self,
                      section_name: str,
                      model: Animal,
                      update_model: BaseModel,
                      user: User,
                      db: AsyncSession,
                    ) -> Animal:
        """Hnadles animal updates via strategies based on section name. Returns the updated animal"""
        strategy: UpdateStrategy = self.__strategies[section_name]

        return await strategy.update(model=model,
                                      update_model=update_model,
                                      user=user,
                                      db=db)

update_handler: UpdateHanlder = UpdateHanlder()
