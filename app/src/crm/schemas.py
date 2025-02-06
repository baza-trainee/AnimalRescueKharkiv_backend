# mypy: disable-error-code="assignment"
import enum
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Callable, ClassVar, List, Optional, Type

from fastapi import HTTPException, Query, status
from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
    Strict,
    computed_field,
    field_validator,
    model_serializer,
)
from sqlalchemy.orm.decl_api import DeclarativeMeta
from src.base_schemas import IntReferenceBase, ResponseReferenceBase, UUIDReferenceBase
from src.configuration.settings import settings
from src.crm.models import Gender
from src.exceptions.exceptions import RETURN_MSG
from src.media.schemas import MediaAssetResponse
from src.users.schemas import UserResponse

SixDigitID = Annotated[int, PlainSerializer(lambda x: str(x).zfill(6), return_type=str)]
UserEmail = Annotated[UserResponse, PlainSerializer(lambda x: x.email, return_type=str)]

def validate_past_or_present(value: date) -> date:
    """Validates value for past or present date"""
    if isinstance(value, str):
        value = date.fromisoformat(value)
    if value > datetime.now().date():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.date_not_past_present)
    return value

PastOrPresentDate = Annotated[date, PlainValidator(validate_past_or_present)]
SORTING_VALIDATION_REGEX = r"^[a-zA-Z0-9_]+\|(asc|desc)$"

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
                    section, _ = key.split("__", 1)
                except ValueError:
                    continue
                if section not in structured_data:
                    structured_data[section] = {}
                structured_data[section][key] = value
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


class LocationBase(BaseModel):
    name: str


class AnimalTypeBase(BaseModel):
    name: str


class AnimalLocationBase(BaseModel):
    location: IntReferenceBase
    date_from: PastOrPresentDate
    date_to: Optional[PastOrPresentDate] = None


class VaccinationBase(BaseModel):
    is_vaccinated: bool
    vaccine_type: Optional[str] = Field(default=None, max_length=100)
    date: Optional[PastOrPresentDate] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class DiagnosisBase(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    date: Optional[PastOrPresentDate] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class ProcedureBase(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    date: Optional[PastOrPresentDate] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class AnimalTypeResponse(AnimalTypeBase, IntReferenceBase):
    model_config = ConfigDict(from_attributes=True)


class LocationResponse(LocationBase, IntReferenceBase):
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


class AnimalLocationUpdate(AnimalLocationBase, UUIDReferenceBase):
    pass

class VaccinationUpdate(VaccinationBase, UUIDReferenceBase):
    pass

class DiagnosisUpdate(DiagnosisBase, UUIDReferenceBase):
    pass

class ProcedureUpdate(ProcedureBase, UUIDReferenceBase):
    pass

class NamedSection:
    _section_name: ClassVar[str]

    @classmethod
    def get_section_name(cls) -> str:
        """Gets section name"""
        return cls._section_name

    @classmethod
    def get_section_by_name(cls, section_name: str) -> Optional[Type[BaseModel]]:
        """Gets subclass section type by section name. Returns resolved type"""
        for section_model in cls.__subclasses__():
            if issubclass(section_model, BaseModel) and section_model.get_section_name() == section_name:
                return section_model
        return None

class AnimalNameUpdate(BaseModel, NamedSection):
    _section_name = "name"
    name: str = Field(min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯґҐєЄіІїЇ'’\-\s]+$")


class OriginUpdate(BaseModel, NamedSection):
    _section_name = "origin"
    origin__arrival_date: PastOrPresentDate
    origin__city: str = Field(max_length=100)
    origin__address: Optional[str] = Field(default=None, max_length=100)


class GeneralUpdate(BaseModel, NamedSection):
    _section_name = "general"
    general__animal_type: Optional[IntReferenceBase] = Field(default=None)
    general__gender: Gender = Gender.male
    general__weight: Optional[float] = Field(default=None, ge=0.0)
    general__age: Optional[float] = Field(default=None, le=100.0)
    general__specials: Optional[str] = Field(default=None, max_length=200)


class OwnerUpdate(BaseModel, NamedSection):
    _section_name = "owner"
    owner__info: Optional[str] = Field(default=None, max_length=500)


class CommentUpdate(BaseModel, NamedSection):
    _section_name = "comment"
    comment__text: Optional[str] = Field(default=None, max_length=1000)


class AdoptionUpdate(BaseModel, NamedSection):
    _section_name = "adoption"
    adoption__country: Optional[str] = Field(default=None, max_length=50)
    adoption__city: Optional[str] = Field(default=None, max_length=50)
    adoption__date: Optional[PastOrPresentDate] = None
    adoption__comment: Optional[str] = Field(default=None, max_length=500)


class DeathUpdate(BaseModel, NamedSection):
    _section_name = "death"
    death__dead: Optional[bool] = False
    death__date: Optional[PastOrPresentDate] = None
    death__comment: Optional[str] = Field(default=None, max_length=500)


class SterilizationUpdate(BaseModel, NamedSection):
    _section_name = "sterilization"
    sterilization__done: Optional[bool] = None
    sterilization__date: Optional[PastOrPresentDate] = None
    sterilization__comment: Optional[str] = Field(default=None, max_length=500)


class MicrochippingUpdate(BaseModel, NamedSection):
    _section_name = "microchipping"
    microchipping__done: Optional[bool] = None
    microchipping__date: Optional[PastOrPresentDate] = None
    microchipping__comment: Optional[str] = Field(default=None, max_length=500)


class MediaUpdate(BaseModel, NamedSection):
    _section_name = "media"
    media: Optional[List[UUIDReferenceBase]] = None

class LocationsUpdate(BaseModel, NamedSection):
    _section_name = "locations"
    locations: Optional[List[AnimalLocationUpdate]] = None


class VaccinationsUpdate(BaseModel, NamedSection):
    _section_name = "vaccinations"
    vaccinations: Optional[List[VaccinationUpdate]] = None


class DiagnosesUpdate(BaseModel, NamedSection):
    _section_name = "diagnoses"
    diagnoses: Optional[List[DiagnosisUpdate]] = None


class ProceduresUpdate(BaseModel, NamedSection):
    _section_name = "procedures"
    procedures: Optional[List[ProcedureUpdate]] = None


class LocationsCreate(BaseModel):
    locations: Optional[List[AnimalLocationBase]] = None


class VaccinationsCreate(BaseModel):
    vaccinations: Optional[List[VaccinationBase]] = None


class DiagnosesCreate(BaseModel):
    diagnoses: Optional[List[DiagnosisBase]] = None


class ProceduresCreate(BaseModel):
    procedures: Optional[List[ProcedureBase]] = None



class GeneralCreate(GeneralUpdate):
    general__animal_type: IntReferenceBase = Field()


class AnimalCreate(ProceduresUpdate,
                   DiagnosesUpdate,
                   VaccinationsUpdate,
                   LocationsUpdate,
                   MediaUpdate,
                   MicrochippingUpdate,
                   SterilizationUpdate,
                   DeathUpdate,
                   AdoptionUpdate,
                   CommentUpdate,
                   OwnerUpdate,
                   GeneralCreate,
                   OriginUpdate,
                   AnimalNameUpdate):
    pass


class AnimalState(enum.Enum):
    active: str = "active"
    dead: str = "dead"
    adopted: str = "adopted"

class Sorting(BaseModel):
    sort: str | None = Query(default="created_at|desc",
                                description="Sort option in format of {field}|{direction}. Default: created_at|desc")

    @field_validator("sort")
    @classmethod
    def validate_regex(cls, value: str) -> str:
        """Validates sorting option value via regular expression"""
        if not re.match(SORTING_VALIDATION_REGEX, value):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.crm_illegal_sort)
        return value


class EditingLockResponse(BaseModel):
    user: UserEmail
    section_name: str
    animal_id: SixDigitID
