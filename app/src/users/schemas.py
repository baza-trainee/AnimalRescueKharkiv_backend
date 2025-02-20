import re
from typing import Annotated, Optional

from fastapi import HTTPException, status
from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field, PlainValidator, field_validator
from src.base_schemas import ResponseReferenceBase
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.media.schemas import MediaAssetResponse, UUIDReferenceBase
from src.roles.schemas import RoleBase, RoleResponse


def validate_phone(value: str | None) -> str | None:
    """Validates phone value"""
    if not value:
        return None
    if not settings.phone_regex.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.user_phone_invalid)
    return value

PhoneStr = Annotated[str | None, PlainValidator(validate_phone)]

def validate_email(value: EmailStr) -> EmailStr:
    """Validates email value"""
    if not settings.email_regex.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=RETURN_MSG.user_email_invalid_format)
    if value.endswith(settings.email_restricted_domains_list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=RETURN_MSG.user_email_invalid % ", ".join(settings.email_restricted_domains_list))
    return value

ExtEmailStr = Annotated[EmailStr, PlainValidator(validate_email)]

class UserBase(BaseModel):
    email: ExtEmailStr
    domain: str


class UserExt(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=50)
    last_name: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[PhoneStr] = None
    photo: Optional[UUIDReferenceBase] = None


def validate_password(value: str) -> str:
    """Check the password using the regular expression from the password_regex settings field"""
    if not settings.password_regex.match(value):
        raise ValueError(RETURN_MSG.user_pwd_invalid)
    return value


class UserCreate(UserBase, UserExt):
    password: str
    role: Optional[RoleBase] = None

    validate_password = field_validator("password")(validate_password)


class UserResponse(UserBase, UserExt, ResponseReferenceBase):
    role: Optional[RoleResponse] = None
    phone: Optional[str] = None
    photo: Optional[MediaAssetResponse] = None
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(UserExt):
    pass


class UserPasswordUpdate(BaseModel):
    password_old: str
    password_new: str

    validate_new_password = field_validator("password_new")(validate_password)


class UserPasswordNew(BaseModel):
    password_new: str

    validate_new_password = field_validator("password_new")(validate_password)
