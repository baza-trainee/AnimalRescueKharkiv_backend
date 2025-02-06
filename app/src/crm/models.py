import enum
from typing import TYPE_CHECKING, List
from uuid import uuid4

from sqlalchemy import UUID, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
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

    general__animal_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_animal_types.id"), nullable=True)
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

    updated_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), index=True)
    updated_by_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    updated_by: Mapped["User"] = relationship("User", lazy="joined", foreign_keys=[updated_by_id])

    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), index=True)
    created_by_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    created_by: Mapped["User"] = relationship("User", lazy="joined", foreign_keys=[created_by_id])

    media: Mapped[List[MediaAsset]] = relationship(secondary="crm_animal_media",
                                                   lazy="joined")
    locations: Mapped[List["AnimalLocation"]] = relationship("AnimalLocation",
                                                             back_populates="animal",
                                                             cascade="all, delete-orphan",
                                                             lazy="joined",
                                                             order_by="desc(AnimalLocation.date_from)")
    vaccinations: Mapped[List["Vaccination"]] = relationship("Vaccination",
                                                             cascade="all, delete-orphan",
                                                             lazy="joined")
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis",
                                                        cascade="all, delete-orphan",
                                                        lazy="joined")
    procedures: Mapped[List["Procedure"]] = relationship("Procedure",
                                                         cascade="all, delete-orphan",
                                                         lazy="joined")


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
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="locations",
                                            lazy="joined")
    location_id: Mapped[int] = mapped_column(ForeignKey(Location.id), nullable=False)
    location: Mapped["Location"] = relationship("Location", lazy="joined")
    date_from: Mapped[Date] = mapped_column(Date, index=False, nullable=False)
    date_to: Mapped[Date] = mapped_column(Date, index=False, nullable=True)


class AnimalMedia(Base):
    __tablename__ = "crm_animal_media"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), nullable=False)
    media_id: Mapped[MediaAsset] = mapped_column(ForeignKey(MediaAsset.id), nullable=True)


class Vaccination(Base):
    __tablename__ = "crm_vaccinations"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="vaccinations",
                                            lazy="joined")
    is_vaccinated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    vaccine_type: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    date: Mapped[Date] = mapped_column(Date, index=True, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)


class Diagnosis(Base):
    __tablename__ = "crm_diagnoses"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="diagnoses",
                                            lazy="joined")
    name: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    date: Mapped[Date] = mapped_column(Date, index=False, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)


class Procedure(Base):
    __tablename__ = "crm_procedures"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[int] = mapped_column(Integer, ForeignKey(Animal.id), nullable=False)
    animal: Mapped["Animal"] = relationship("Animal",
                                            back_populates="procedures",
                                            lazy="joined")
    name: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    date: Mapped[Date] = mapped_column(Date, index=False, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)
