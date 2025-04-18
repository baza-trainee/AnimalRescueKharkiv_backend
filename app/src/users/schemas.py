import re
from datetime import datetime
from typing import Annotated, Optional

from fastapi import HTTPException, status
from pydantic import UUID4, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, field_validator
from src.base_schemas import ResponseReferenceBase, SanitizedString
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.media.schemas import MediaAssetResponse, UUIDReferenceBase
from src.roles.schemas import RoleBase, RoleResponse


def validate_password(value: str) -> str:
    """Check the password using the regular expression from the password_regex settings field"""
    if not settings.password_regex.match(value):
        raise ValueError(RETURN_MSG.user_pwd_invalid)
    return value


def validate_phone(value: str | None) -> str | None:
    """Validates phone value"""
    if not value:
        return None
    if not settings.phone_regex.fullmatch(value):
        raise ValueError(RETURN_MSG.user_phone_invalid)
    return value

PhoneStr = Annotated[str | None, BeforeValidator(validate_phone),Field(
        example="+380 96 222 22 22",
        json_schema_extra={"type": "string", "format": f"mastches {settings.phone_regex_str}"},
    )]

PwdStr = Annotated[str, BeforeValidator(validate_password),Field(
        example="Password123!",
        json_schema_extra={"type": "string", "format": f"mastches {settings.password_regex_str}"},
    )]

def validate_email(value: EmailStr) -> EmailStr:
    """Validates email value"""
    try:
        if not settings.email_regex.fullmatch(value):
            raise ValueError(RETURN_MSG.user_email_invalid_format)
        if value.endswith(settings.email_restricted_domains_list):
            raise ValueError(RETURN_MSG.user_email_invalid % ", ".join(settings.email_restricted_domains_list))
    except TypeError as e:
        raise ValueError(e.args[0])
    return value

ExtEmailStr = Annotated[EmailStr, BeforeValidator(validate_email),Field(
        example="name@example.com",
        json_schema_extra={"type": "string", "format": f"mastches {settings.email_regex_str}"},
    )]

class UserBase(BaseModel):
    email: ExtEmailStr
    domain: SanitizedString


class UserExt(BaseModel):
    first_name: Optional[SanitizedString] = Field(default=None,
                                      min_length=2,
                                      max_length=30,
                                      pattern=r"^[a-zA-Zа-яА-ЯґҐєЄіІїЇ'’\-\s]+$")
    last_name: Optional[SanitizedString] = Field(default=None,
                                     min_length=2,
                                     max_length=50,
                                     pattern=r"^[a-zA-Zа-яА-ЯґҐєЄіІїЇ'’\-\s]+$")
    phone: Optional[PhoneStr] = None
    photo: Optional[UUIDReferenceBase] = None


class UserCreate(UserBase, UserExt):
    password: PwdStr
    role: Optional[RoleBase] = None


class UserResponse(UserBase, UserExt, ResponseReferenceBase):
    role: Optional[RoleResponse] = None
    phone: Optional[str] = None
    photo: Optional[MediaAssetResponse] = None
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class UserUpdate(UserExt):
    pass


class UserPasswordUpdate(BaseModel):
    password_old: str
    password_new: PwdStr


class UserPasswordNew(BaseModel):
    password_new: PwdStr
