# mypy: disable-error-code="assignment"
import enum
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Callable, List, Optional

from fastapi import Query
from pydantic import (
        UUID4,
        BaseModel,
        ConfigDict,
        Field,
        PastDate,
        PlainSerializer,
        Strict,
        computed_field,
        model_serializer,
)
from sqlalchemy.orm.decl_api import DeclarativeMeta
from src.configuration.settings import settings
from src.crm.models import Gender
from src.media.schemas import MediaAssetReference, MediaAssetResponse
from src.users.schemas import UserResponse

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]
SixDigitID = Annotated[int, PlainSerializer(lambda x: str(x).zfill(6), return_type=str)]
UserEmail = Annotated[UserResponse, PlainSerializer(lambda x: x.email, return_type=str)]


class DynamicSection(BaseModel):
        model_config = ConfigDict(extra="allow")


class AuthorizableField:
    def __init__(self, *args, **kwargs) -> None:
        """Initializes AuthorizableField instance"""
        self.default = kwargs.get("default", None)
        self.field_info = Field(*args, **kwargs)

    def __set_name__(self, owner: BaseModel, name: str) -> None:
        """Adds attribute name to an owner's _authorizable_attributes"""
        if not hasattr(owner, "_authorizable_attributes"):
            owner._authorizable_attributes = [] #noqa: SLF001
        owner._authorizable_attributes.append(name) #noqa: SLF001
        setattr(owner, name, self.field_info)


class DynamicResponse(BaseModel):
    editable_attributes: List[str] = []

    @classmethod
    def __get_instance_attributes(cls, instance: DeclarativeMeta) -> dict:
        instance_data = {}
        for key in instance.__mapper__.c.keys(): #noqa: SIM118
            instance_data[key] = getattr(instance, key, None)
        for rel_name in instance.__mapper__.relationships.keys(): #noqa: SIM118
            related_obj = getattr(instance, rel_name, None)
            if related_obj:
                if isinstance(related_obj, list):
                    instance_data[rel_name] = [
                        {k: v for k, v in rel.__dict__.items() if not k.startswith("_")}
                        for rel in related_obj
                    ]
                else:
                    instance_data[rel_name] = {
                        k: v for k, v in related_obj.__dict__.items()
                        if not k.startswith("_")
                    }
        return instance_data

    @classmethod
    def __structure_instance_data(cls, instance_data: dict) -> dict:
        structured_data: dict = {}
        for key, value in instance_data.items():
            if "__" in key and len(key.split("__")) == 2: #noqa: PLR2004
                try:
                    section, field_name = key.split("__", 1)
                except ValueError:
                    continue
                if section not in structured_data:
                    structured_data[section] = {}
                structured_data[section][field_name] = value
            else:
                structured_data[key] = value
        return structured_data

    @classmethod
    def model_validate(cls, instance:DeclarativeMeta|dict) -> BaseModel:
        """Custom validation method to handle SQLAlchemy objects with relationships."""
        instance_data = instance if isinstance(instance, dict) else cls.__get_instance_attributes(instance=instance)

        return super().model_validate(cls.__structure_instance_data(instance_data=instance_data))

    def __serialize_value(self, value: datetime|Decimal|str) -> datetime|float|str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    @model_serializer(mode="wrap")
    def custom_serializer(self, handler:Callable) -> dict:
        """Serializes pydantic model to dict"""
        serialized_data = handler(self)
        return {key: self.__serialize_value(value)
                for key, value in serialized_data.items()
                if value is not None}

    @property
    def authorizable_attributes(self) -> List[str]:
        """Returns authorizable data sections"""
        return self._authorizable_attributes


class ReferenceBase(BaseModel):
    id: Annotated[UUID4, Strict(strict=False)]

class ResponseReferenceBase(BaseModel):
    id: UUIDString


class LocationBase(BaseModel):
    name: str


class AnimalTypeBase(BaseModel):
    name: str


class AnimalLocationBase(BaseModel):
    location: ReferenceBase
    date_from: PastDate
    date_to: Optional[PastDate] = None


class VaccinationBase(BaseModel):
    is_vaccinated: bool
    vaccine_type: Optional[str] = Field(default=None, max_length=100)
    date: Optional[PastDate] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class DiagnosisBase(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    date: Optional[PastDate] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class ProcedureBase(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    date: Optional[PastDate] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class AnimalTypeResponse(AnimalTypeBase, ResponseReferenceBase):
    model_config = ConfigDict(from_attributes=True)


class LocationResponse(LocationBase, ResponseReferenceBase):
    model_config = ConfigDict(from_attributes=True)

class AnimalLocationResponse(AnimalLocationBase, ResponseReferenceBase):
    animal_id: SixDigitID
    location: LocationResponse

    model_config = ConfigDict(from_attributes=True)


class VaccinationResponse(VaccinationBase, ResponseReferenceBase):
    animal_id: SixDigitID

    model_config = ConfigDict(from_attributes=True)


class DiagnosisResponse(DiagnosisBase, ResponseReferenceBase):
    animal_id: SixDigitID

    model_config = ConfigDict(from_attributes=True)


class ProcedureResponse(ProcedureBase, ResponseReferenceBase):
    animal_id: SixDigitID

    model_config = ConfigDict(from_attributes=True)


class AnimalResponse(DynamicResponse):
    id: SixDigitID
    name: str = AuthorizableField()

    origin: Optional[DynamicSection] = AuthorizableField(default=None)

    general: Optional[DynamicSection] = AuthorizableField(default=None)

    owner: Optional[DynamicSection] = AuthorizableField(default=None)

    comment: Optional[DynamicSection] = AuthorizableField(default=None)

    adoption: Optional[DynamicSection] = AuthorizableField(default=None)

    death: Optional[DynamicSection] = AuthorizableField(default=None)

    sterilization: Optional[DynamicSection] = AuthorizableField(default=None)

    microchipping: Optional[DynamicSection] = AuthorizableField(default=None)

    updated_at: datetime
    updated_by: UserEmail

    created_at: datetime
    created_by: UserEmail

    @computed_field
    def current_location(self) -> AnimalLocationResponse | None:
        """Dynamically generates current_location property based on the locations list"""
        if self.locations:
            return max(self.locations, key=lambda loc: loc.date_from)
        return None

    media: Optional[List[MediaAssetResponse]] = AuthorizableField(default=None)
    locations: Optional[List[AnimalLocationResponse]] = AuthorizableField(default=None)
    vaccinations: Optional[List[VaccinationResponse]] = AuthorizableField(default=None)
    diagnoses: Optional[List[DiagnosisResponse]] = AuthorizableField(default=None)
    procedures: Optional[List[ProcedureResponse]] = AuthorizableField(default=None)


class AnimalTypeCreate(AnimalTypeBase):
    pass


class LocationCreate(LocationBase):
    pass


class AnimalLocationCreate(AnimalLocationBase):
    pass


class VaccinationCreate(VaccinationBase):
    pass


class DiagnosisCreate(DiagnosisBase):
    pass


class ProcedureCreate(ProcedureBase):
    pass


class AnimalName(BaseModel):
    name: str = Field(min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯїЇ'’\-\s]+$")


class OriginBase(BaseModel):
    origin__arrival_date: PastDate
    origin__city: str = Field(max_length=100)
    origin__address: Optional[str] = Field(default=None, max_length=100)


class GeneralBase(BaseModel):
    general__animal_type: ReferenceBase
    general__gender: Gender = Gender.male
    general__weight: Optional[float] = Field(default=None, ge=0.0)
    general__age: Optional[float] = Field(default=None, le=100.0)
    general__specials: Optional[str] = Field(default=None, max_length=200)


class OwnerBase(BaseModel):
    owner__info: Optional[str] = Field(default=None, max_length=500)


class CommentBase(BaseModel):
    comment__text: Optional[str] = Field(default=None, max_length=1000)


class AdoptionBase(BaseModel):
    adoption__country: Optional[str] = Field(default=None, max_length=50)
    adoption__city: Optional[str] = Field(default=None, max_length=50)
    adoption__date: Optional[PastDate] = None
    adoption__comment: Optional[str] = Field(default=None, max_length=500)


class DeathBase(BaseModel):
    death__dead: Optional[bool] = None
    death__date: Optional[PastDate] = None
    death__comment: Optional[str] = Field(default=None, max_length=500)


class SterilizationBase(BaseModel):
    sterilization__done: Optional[bool] = None
    sterilization__date: Optional[PastDate] = None
    sterilization__comment: Optional[str] = Field(default=None, max_length=500)


class MicrochippingBase(BaseModel):
    microchipping__done: Optional[bool] = None
    microchipping__date: Optional[PastDate] = None
    microchipping__comment: Optional[str] = Field(default=None, max_length=500)


class AnimalCreate(AnimalName,
                   OriginBase,
                   GeneralBase,
                   OwnerBase,
                   CommentBase,
                   AdoptionBase,
                   DeathBase,
                   SterilizationBase,
                   MicrochippingBase):
    media: Optional[List[MediaAssetReference]] = None
    locations: Optional[List[AnimalLocationCreate]] = None
    vaccinations: Optional[List[VaccinationCreate]] = None
    diagnoses: Optional[List[DiagnosisCreate]] = None
    procedures: Optional[List[ProcedureCreate]] = None


class AnimalState(enum.Enum):
    active: str = "active"
    dead: str = "dead"
    adopted: str = "adopted"
