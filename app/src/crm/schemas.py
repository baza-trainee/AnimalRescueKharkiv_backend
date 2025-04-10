# mypy: disable-error-code="assignment"
import enum
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Callable, ClassVar, List, Optional, Type

import uvicorn
from dateutil import parser  # type: ignore[import-untyped]
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
    model_serializer,
    model_validator,
)
from sqlalchemy.orm.decl_api import DeclarativeMeta
from src.base_schemas import IntReferenceBase, ResponseReferenceBase, SanitizedString, UUIDReferenceBase
from src.configuration.settings import settings
from src.crm.models import Gender
from src.exceptions.exceptions import RETURN_MSG
from src.media.schemas import MediaAssetResponse
from src.roles.models import Role
from src.users.schemas import UserResponse
from typing_extensions import Self

SixDigitID = Annotated[int, PlainSerializer(lambda x: str(x).zfill(6), return_type=str)]
UserEmail = Annotated[UserResponse, PlainSerializer(lambda x: x.email, return_type=str)]

logger = logging.getLogger(uvicorn.logging.__name__)

def validate_past_or_present(value: date | str) -> date:
    """Validates value for past or present date"""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        ValueError(RETURN_MSG.crm_invalid_date_format)

    parsed_date = None
    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed_date = datetime.strptime(value, fmt).date() #noqa: DTZ007
            break
        except ValueError:
            continue

    if not parsed_date:
        raise ValueError(RETURN_MSG.crm_invalid_date_format)
    if parsed_date > datetime.now().date():
        raise ValueError(RETURN_MSG.date_not_past_present)
    return parsed_date


PastOrPresentDate = Annotated[date, BeforeValidator(validate_past_or_present), Field(
        example="YYYY-MM-DD or DD/MM/YYYY",
        json_schema_extra={"type": "date", "format": "<= datetime.now().date()"},
    )]

class DynamicSection(BaseModel):
    model_config = ConfigDict(extra="allow")

    def __serialize_value(self, value: datetime|date|Decimal|str) -> datetime|float|str:
        if isinstance(value, (datetime, date)):
            return value.strftime("%d/%m/%Y")
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            try:
                parsed_value = parser.parse(value)
                if parsed_value.hour or parsed_value.minute or parsed_value.second:
                    return parsed_value.strftime("%d/%m/%Y %H:%M:%S")
                return parsed_value.strftime("%d/%m/%Y")
            except parser.ParserError:
                pass
        return value


    @model_serializer(mode="wrap")
    def custom_serializer(self, handler:Callable) -> dict:
        """Serializes pydantic model to dict"""
        serialized_data = handler(self)
        return {key: self.__serialize_value(value)
                for key, value in serialized_data.items()
                if value is not None}


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
    editable_attributes: List[str] =[]

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

    def authorize_model_attributes(self, role: Role) -> None:
        """Authorizes user access to response model attibutes."""
        self.editable_attributes = []
        if self.__is_system_admin(role=role):
            self.editable_attributes = list(self._authorizable_attributes)
        else:
            permission_entities = [perm.entity for perm in role.permissions if perm.operation == "write"]
            for attr_name in self._authorizable_attributes:
                if attr_name in permission_entities:
                    self.editable_attributes.append(attr_name)

    def __is_system_admin(self, role: Role) -> bool:
        return (role.name == settings.super_user_role) and (role.domain == settings.super_user_domain)

    def __serialize_value(self, value: datetime|date|Decimal|str) -> datetime|float|str:
        if isinstance(value, (datetime, date)):
            return value.strftime("%d/%m/%Y")
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            try:
                parsed_value = parser.parse(value)
                if parsed_value.hour or parsed_value.minute or parsed_value.second:
                    return parsed_value.strftime("%d/%m/%Y %H:%M:%S")
                return parsed_value.strftime("%d/%m/%Y")
            except parser.ParserError:
                pass
        return value


    @model_serializer(mode="wrap")
    def custom_serializer(self, handler:Callable) -> dict:
        """Serializes pydantic model to dict"""
        serialized_data = handler(self)
        return {key: self.__serialize_value(value)
                for key, value in serialized_data.items()
                if value is not None}

class AnimalResponseReference(BaseModel):
    animal_id: SixDigitID

class LocationBase(BaseModel):
    name: SanitizedString = Field(min_length=2, max_length=100)


class AnimalTypeBase(BaseModel):
    name: SanitizedString = Field(min_length=2, max_length=50)


class AnimalLocationBase(BaseModel):
    location: IntReferenceBase
    date_from: PastOrPresentDate
    date_to: Optional[PastOrPresentDate] = None

    @model_validator(mode="after")
    def __validate_location_dates(self) -> Self:
        if self.date_to and self.date_to < self.date_from:
            raise ValueError(RETURN_MSG.crm_date_range_invalid % ("date_to", "date_from"))
        return self


class VaccinationBase(BaseModel):
    is_vaccinated: bool
    vaccine_type: Optional[SanitizedString] = Field(default=None, min_length=2, max_length=100)
    date: Optional[PastOrPresentDate] = None
    comment: Optional[SanitizedString] = Field(default=None, max_length=500)


class DiagnosisBase(BaseModel):
    name: Optional[SanitizedString] = Field(default=None, min_length=2, max_length=200)
    date: Optional[PastOrPresentDate] = None
    comment: Optional[SanitizedString] = Field(default=None, max_length=500)


class ProcedureBase(BaseModel):
    name: Optional[SanitizedString] = Field(default=None, min_length=2, max_length=200)
    date: Optional[PastOrPresentDate] = None
    comment: Optional[SanitizedString] = Field(default=None, max_length=500)


class AnimalTypeResponse(AnimalTypeBase, IntReferenceBase):
    model_config = ConfigDict(from_attributes=True)


class LocationResponse(LocationBase, IntReferenceBase):
    model_config = ConfigDict(from_attributes=True)

class AnimalLocationResponse(AnimalLocationBase, ResponseReferenceBase, AnimalResponseReference):
    location: LocationResponse

    model_config = ConfigDict(from_attributes=True)


class VaccinationResponse(VaccinationBase, ResponseReferenceBase, AnimalResponseReference):
    model_config = ConfigDict(from_attributes=True)


class DiagnosisResponse(DiagnosisBase, ResponseReferenceBase, AnimalResponseReference):
    model_config = ConfigDict(from_attributes=True)


class ProcedureResponse(ProcedureBase, ResponseReferenceBase, AnimalResponseReference):
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
    updated_by: Optional[UserEmail] = None

    created_at: datetime
    created_by: Optional [UserEmail] = None

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
    name: SanitizedString = Field(min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯґҐєЄіІїЇ'’\-\s]+$")


class OriginUpdate(BaseModel, NamedSection):
    _section_name = "origin"
    origin__arrival_date: PastOrPresentDate
    origin__city: SanitizedString = Field(min_length=2, max_length=100)
    origin__address: Optional[SanitizedString] = Field(default=None, min_length=2, max_length=100)


class GeneralUpdate(BaseModel, NamedSection):
    _section_name = "general"
    general__animal_type: Optional[IntReferenceBase] = Field(default=None)
    general__gender: Gender
    general__weight: Optional[float] = Field(default=None, gt=0.0)
    general__age: Optional[float] = Field(default=None, gt=0.0, le=100.0)
    general__specials: Optional[SanitizedString] = Field(default=None, max_length=200)


class OwnerUpdate(BaseModel, NamedSection):
    _section_name = "owner"
    owner__info: Optional[SanitizedString] = Field(default=None, max_length=500)


class CommentUpdate(BaseModel, NamedSection):
    _section_name = "comment"
    comment__text: Optional[SanitizedString] = Field(default=None, max_length=1000)


class AdoptionUpdate(BaseModel, NamedSection):
    _section_name = "adoption"
    adoption__country: Optional[SanitizedString] = Field(default=None, min_length=2, max_length=50)
    adoption__city: Optional[SanitizedString] = Field(default=None, min_length=2, max_length=50)
    adoption__date: Optional[PastOrPresentDate] = None
    adoption__comment: Optional[SanitizedString] = Field(default=None, max_length=500)


class DeathUpdate(BaseModel, NamedSection):
    _section_name = "death"
    death__dead: Optional[bool] = False
    death__date: Optional[PastOrPresentDate] = None
    death__comment: Optional[SanitizedString] = Field(default=None, max_length=500)


class SterilizationUpdate(BaseModel, NamedSection):
    _section_name = "sterilization"
    sterilization__done: Optional[bool] = None
    sterilization__date: Optional[PastOrPresentDate] = None
    sterilization__comment: Optional[SanitizedString] = Field(default=None, max_length=500)


class MicrochippingUpdate(BaseModel, NamedSection):
    _section_name = "microchipping"
    microchipping__done: Optional[bool] = None
    microchipping__date: Optional[PastOrPresentDate] = None
    microchipping__comment: Optional[SanitizedString] = Field(default=None, max_length=500)


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
    locations: List[AnimalLocationBase] = Field(..., min_length=1)


class VaccinationsCreate(BaseModel):
    vaccinations: Optional[List[VaccinationBase]] = None


class DiagnosesCreate(BaseModel):
    diagnoses: Optional[List[DiagnosisBase]] = None


class ProceduresCreate(BaseModel):
    procedures: Optional[List[ProcedureBase]] = None



class GeneralCreate(GeneralUpdate):
    general__animal_type: IntReferenceBase = Field()


class AnimalCreate(ProceduresCreate,
                   DiagnosesCreate,
                   VaccinationsCreate,
                   LocationsCreate,
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


class EditingLockResponse(AnimalResponseReference):
    user: UserEmail
    section_name: str

    model_config = ConfigDict(from_attributes=True)
