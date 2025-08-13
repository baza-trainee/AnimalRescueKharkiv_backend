import enum
from typing import TYPE_CHECKING, List
from uuid import uuid4

from sqlalchemy import (
    UUID,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, aliased, mapped_column, relationship
from sqlalchemy.sql.expression import Selectable
from src.configuration.db import Base
from src.media.models import MediaAsset

if TYPE_CHECKING:
    from src.users.models import User

class Gender(enum.Enum):
    male: str = "male"
    female: str = "female"

class Animal(Base):
    __tablename__ = "crm_animals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    origin__arrival_date: Mapped[Date] = mapped_column(Date, index=True, nullable=False)
    origin__city: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    origin__address: Mapped[str] = mapped_column(String(100), index=False, nullable=True)

    general__animal_type_id: Mapped[int] = mapped_column(Integer,
                                                         ForeignKey("crm_animal_types.id"),
                                                         index=True,
                                                         nullable=True)
    general__animal_type: Mapped["AnimalType"] = relationship("AnimalType", lazy="joined")
    general__gender: Mapped[enum.Enum] = mapped_column(Enum(Gender), default=Gender.male)
    general__weight: Mapped[float] = mapped_column(Float, index=False, nullable=True)
    general__age: Mapped[float] = mapped_column(Float, index=False, nullable=True)
    general__specials: Mapped[str] = mapped_column(String(200), index=False, nullable=True)

    owner__info: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    comment__text: Mapped[str] = mapped_column(String(1000), index=False, nullable=True)

    adoption__country: Mapped[str] = mapped_column(String(50), index=False, nullable=True)
    adoption__city: Mapped[str] = mapped_column(String(50), index=False, nullable=True)
    adoption__date: Mapped[Date] = mapped_column(Date, index=False, nullable=True)
    adoption__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    death__dead: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    death__date: Mapped[Date] = mapped_column(Date, index=True, nullable=True)
    death__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    sterilization__done: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sterilization__date: Mapped[Date] = mapped_column(Date, index=True, nullable=True)
    sterilization__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    microchipping__done: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    microchipping__date: Mapped[Date] = mapped_column(Date, index=True, nullable=True)
    microchipping__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                 default=func.now(),
                                                 onupdate=func.now(),
                                                 index=True)
    updated_by_id: Mapped[UUID | None] = mapped_column(UUID,
                                                       ForeignKey("users.id", ondelete="SET NULL"),
                                                       index=True,
                                                       nullable=True)
    updated_by: Mapped["User"] = relationship("User", lazy="joined", foreign_keys=[updated_by_id])

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                 default=func.now(),
                                                 index=True)
    created_by_id: Mapped[UUID | None] = mapped_column(UUID,
                                                       ForeignKey("users.id", ondelete="SET NULL"),
                                                       index=True,
                                                       nullable=True)
    created_by: Mapped["User"] = relationship("User", lazy="joined", foreign_keys=[created_by_id])

    media: Mapped[List[MediaAsset]] = relationship(secondary="crm_animal_media",
                                                   lazy="selectin")
    locations: Mapped[List["AnimalLocation"]] = relationship("AnimalLocation",
                                                             back_populates="animal",
                                                             cascade="all, delete-orphan",
                                                             lazy="selectin",
                                                             order_by="desc(AnimalLocation.date_from)")
    vaccinations: Mapped[List["Vaccination"]] = relationship("Vaccination",
                                                             cascade="all, delete-orphan",
                                                             lazy="selectin",
                                                             order_by="desc(Vaccination.date)")
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis",
                                                        cascade="all, delete-orphan",
                                                        lazy="selectin",
                                                        order_by="desc(Diagnosis.date)")
    procedures: Mapped[List["Procedure"]] = relationship("Procedure",
                                                         cascade="all, delete-orphan",
                                                         lazy="selectin",
                                                         order_by="desc(Procedure.date)")

    @hybrid_property
    def current_location(self) -> DeclarativeBase:
        """Returns the latest location object"""
        if not self.locations:
            return None
        return max(self.locations, key=lambda loc: loc.date_from, default=None)


    @current_location.expression
    @classmethod
    def current_location_id(cls) -> Selectable:
        """SQL expression to get the latest AnimalLocation object."""
        return (
            select(AnimalLocation.location_id)
            .where(AnimalLocation.animal_id == cls.id)
            .order_by(AnimalLocation.date_from.desc())  # Get the most recent one
            .limit(1)
            .scalar_subquery()
        )


class AnimalType(Base):
    __tablename__ = "crm_animal_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), index=True, unique=True, nullable=False)


class Location(Base):
    __tablename__ = "crm_locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=False, unique=True, nullable=False)


class AnimalLocation(Base):
    __tablename__ = "crm_animal_locations"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), index=True, nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="locations",
                                            lazy="selectin")
    location_id: Mapped[int] = mapped_column(ForeignKey(Location.id), index=True, nullable=False)
    location: Mapped["Location"] = relationship("Location", lazy="joined")
    date_from: Mapped[Date] = mapped_column(Date, index=False, nullable=False)
    date_to: Mapped[Date] = mapped_column(Date, index=False, nullable=True)


class AnimalMedia(Base):
    __tablename__ = "crm_animal_media"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), index=True, nullable=False)
    media_id: Mapped[MediaAsset] = mapped_column(ForeignKey(MediaAsset.id), index=True, nullable=True)


class Vaccination(Base):
    __tablename__ = "crm_vaccinations"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), index=True, nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="vaccinations",
                                            lazy="selectin")
    is_vaccinated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    vaccine_type: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    date: Mapped[Date] = mapped_column(Date, index=True, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)


class Diagnosis(Base):
    __tablename__ = "crm_diagnoses"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), index=True, nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="diagnoses",
                                            lazy="selectin")
    name: Mapped[str] = mapped_column(String(200), index=False, nullable=True)
    date: Mapped[Date] = mapped_column(Date, index=False, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)


class Procedure(Base):
    __tablename__ = "crm_procedures"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), index=True, nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="procedures",
                                            lazy="selectin")
    name: Mapped[str] = mapped_column(String(200), index=False, nullable=True)
    date: Mapped[Date] = mapped_column(Date, index=False, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

class EditingLock(Base):
    __tablename__ = "crm_editing_locks"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), index=True, nullable=False)
    animal: Mapped["Animal"] = relationship("Animal", lazy="select")
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), index=True, nullable=False)
    user: Mapped["User"] = relationship("User", lazy="select", foreign_keys=[user_id])
    section_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
