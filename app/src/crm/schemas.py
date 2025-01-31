# mypy: disable-error-code="assignment"
from datetime import date as date_type
from datetime import datetime
from typing import Annotated, Callable, List, Optional

from pydantic import UUID4, BaseModel, ConfigDict, Field, PlainSerializer, Strict, model_serializer
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
            owner._authorizable_sections = [] #noqa: SLF001
        owner._authorizable_attributes.append(name) #noqa: SLF001
        setattr(owner, name, self.field_info)


class DynamicResponse(BaseModel):
    editable_attributes: List[str] = []

    def __init__(self, **data) -> None:
        """Initializes DynamicResponse instance"""
        structured_data: dict = {}
        for key, value in data.items():
            if "__" in key:
                section, _ = key.split("__", 1)
                if section not in structured_data:
                    structured_data[section] = {}
                structured_data[section][key] = value
            else:
                structured_data[key] = value

        super().__init__(**structured_data)

    @model_serializer(mode="wrap")
    def custom_serializer(self, handler:Callable) -> dict:
        """Serializes pydantic model to dict"""
        serialized_data = handler(self)
        return {
            name: (value if value is not None else None)
            for name, value in serialized_data.items()
            if value is not None}

    @property
    def authorizable_attributes(self) -> List[str]:
        """Returns authorizable data sections"""
        return self._authorizable_attributes


class AnimalReferenceBase(BaseModel):
    animal_id: Annotated[UUID4, Strict(strict=False)]


class LocationBase(BaseModel):
    name: str


class AnimalLocationBase(BaseModel):
    date_from: date_type
    date_to: Optional[date_type] = None


class VaccinationBase(BaseModel):
    is_vaccinated: bool
    vaccine_type: Optional[str] = None
    date: Optional[date_type] = None
    comment: Optional[str] = None


class DiagnosisBase(BaseModel):
    is_vaccinated: bool
    name: Optional[str] = None
    date: Optional[date_type] = None
    comment: Optional[str] = None


class ProcedureBase(BaseModel):
    is_vaccinated: bool
    name: Optional[str] = None
    date: Optional[date_type] = None
    comment: Optional[str] = None


class LocationResponse(LocationBase):
    id: UUIDString

    model_config = ConfigDict(from_attributes=True)

class AnimalLocationResponse(AnimalLocationBase):
    id: UUIDString
    animal_id: SixDigitID
    location: LocationResponse

    model_config = ConfigDict(from_attributes=True)


class VaccinationResponse(VaccinationBase):
    id: UUIDString
    animal_id: SixDigitID

    model_config = ConfigDict(from_attributes=True)


class DiagnosisResponse(DiagnosisBase):
    id: UUIDString
    animal_id: SixDigitID

    model_config = ConfigDict(from_attributes=True)


class ProcedureResponse(ProcedureBase):
    id: UUIDString
    animal_id: SixDigitID

    model_config = ConfigDict(from_attributes=True)


class AnimalReponse(DynamicResponse):
    id: SixDigitID
    name: str

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

    media: Optional[List[MediaAssetResponse]] = AuthorizableField(default=None)
    locations: Optional[List[AnimalLocationResponse]] = AuthorizableField(default=None)
    vaccinations: Optional[List[VaccinationResponse]] = AuthorizableField(default=None)
    diagnoses: Optional[List[DiagnosisResponse]] = AuthorizableField(default=None)
    procedures: Optional[List[ProcedureResponse]] = AuthorizableField(default=None)


class LocationCreate(LocationBase):
    pass

class AnimalLocationCreate(LocationBase, AnimalReferenceBase):
    animal_id: Annotated[UUID4, Strict(strict=False)]

class VaccinationCreate(VaccinationBase, AnimalReferenceBase):
    pass

class DiagnosisCreate(DiagnosisBase, AnimalReferenceBase):
    pass

class ProcedureCreate(ProcedureBase, AnimalReferenceBase):
    pass

class AnimalCreate(BaseModel):
    name: str

    origin__arrival_date: date_type
    origin__city: str
    origin__address: Optional[str] = None

    general__animal_type_id: Annotated[UUID4, Strict(strict=False)]
    general__gender: Gender = Gender.male
    general__weight: Optional[float] = None
    general__age: Optional[float] = None
    general__specials: Optional[str] = None

    owner__info: Optional[str] = None

    comment__text: Optional[str] = None

    adoption__country: Optional[str] = None
    adoption__city: Optional[str] = None
    adoption__date: Optional[date_type] = None
    adoption__comment: Optional[str] = None

    death__dead: Optional[bool] = None
    death__date: Optional[date_type] = None
    death__comment: Optional[str] = None

    sterilization__done: Optional[bool] = None
    sterilization__date: Optional[date_type] = None
    sterilization__comment: Optional[str] = None

    microchipping__done: Optional[bool] = None
    microchipping__date: Optional[date_type] = None
    microchipping__comment: Optional[str] = None
