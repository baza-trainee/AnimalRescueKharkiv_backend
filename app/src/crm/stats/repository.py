import logging
from datetime import date
from typing import List, Optional, Tuple, TypeVar

import uvicorn
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.settings import settings
from src.crm.models import (
    Animal,
    AnimalLocation,
    Location,
)
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)


class StatsRepository(metaclass=SingletonMeta):
    async def get_animal_count_by_adoption_country(self,
                                                   db: AsyncSession,
                                                   from_date: Optional[date] = None,
                                                   to_date: Optional[date] = None) -> List[Tuple[str | None, int]]:
        """Returns a list of tuples containing adoption country and the count of animals adopted in that country."""
        statement = (
            select(Animal.adoption__country, func.count(Animal.id))
            .group_by(Animal.adoption__country)
        )
        if from_date:
            statement = statement.where(Animal.adoption__date >= from_date)
        if to_date:
            statement = statement.where(Animal.adoption__date <= to_date)
        result = await db.execute(statement)
        return result.all()

    async def get_total_animal_count(self, db: AsyncSession) -> int:
        """Returns the total count of animal records."""
        statement = select(func.count(Animal.id))
        result = await db.execute(statement)
        return result.scalar_one()

    async def get_adopted_animal_count(self,
                                       db: AsyncSession,
                                       from_date: Optional[date] = None,
                                       to_date: Optional[date] = None) -> int:
        """Returns the count of animal records adopted within the given date range."""
        statement = select(func.count(Animal.id)).where(Animal.adoption__date.isnot(None))

        if from_date:
            statement = statement.where(Animal.adoption__date >= from_date)
        if to_date:
            statement = statement.where(Animal.adoption__date <= to_date)

        result = await db.execute(statement)
        return result.scalar_one()

    async def get_sterilized_animal_count(self,
                                          db: AsyncSession,
                                          from_date: Optional[date] = None,
                                          to_date: Optional[date] = None) -> int:
        """Returns the count of animal records sterilized within the given date range."""
        statement = select(func.count(Animal.id)).where(Animal.sterilization__done.is_(True))

        if from_date:
            statement = statement.where(Animal.sterilization__date >= from_date)
        if to_date:
            statement = statement.where(Animal.sterilization__date <= to_date)

        result = await db.execute(statement)
        return result.scalar_one()

    async def get_dead_animal_count(self,
                                        db: AsyncSession,
                                        from_date: Optional[date] = None,
                                        to_date: Optional[date] = None) -> int:
        """Returns the count of animal records that died within the given date range."""
        statement = select(func.count(Animal.id)).where(Animal.death__dead.is_(True))

        if from_date:
            statement = statement.where(Animal.death__date >= from_date)
        if to_date:
            statement = statement.where(Animal.death__date <= to_date)

        result = await db.execute(statement)
        return result.scalar_one()



    async def get_animal_count_by_status(self,
                                         db: AsyncSession,
                                         from_date: Optional[date] = None,
                                         to_date: Optional[date] = None) -> List[Tuple[str | None, int]]:
        """Returns a list of tuples containing adoption country and the count of animals adopted in that country."""
        statement = (
            select(Animal.adoption__country, func.count(Animal.id))
            .group_by(Animal.adoption__country)
        )
        if from_date:
            statement = statement.where(Animal.adoption__date >= from_date)
        if to_date:
            statement = statement.where(Animal.adoption__date <= to_date)
        result = await db.execute(statement)
        return result.all()

    async def get_animal_count_by_current_location(self, db: AsyncSession) -> List[Tuple[str, int]]:
        """Returns a list of tuples containing the current location name and the count of animals at that location."""
        subquery = (
            select(AnimalLocation.animal_id, AnimalLocation.location_id)
            .distinct(AnimalLocation.animal_id)
            .order_by(AnimalLocation.animal_id, AnimalLocation.date_from.desc())
            .subquery()
        )

        statement = (
            select(Location.name, func.count(subquery.c.animal_id))
            .join(Location, Location.id == subquery.c.location_id)
            .group_by(Location.name)
        )

        result = await db.execute(statement)
        return result.all()

stats_repository:StatsRepository = StatsRepository()
