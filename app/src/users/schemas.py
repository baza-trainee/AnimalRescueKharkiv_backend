import re
from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, field_validator
from src.base_schemas import ResponseReferenceBase
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.media.schemas import MediaAssetResponse, UUIDReferenceBase
from src.roles.schemas import RoleBase, RoleResponse


class UserBase(BaseModel):
    email: EmailStr
    domain: str


class UserExt(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[UUIDReferenceBase] = None


def validate_password(value: str) -> str:
    """Check the password using the regular expression from the password_regex settings field"""
    pattern = re.compile(settings.password_regex)
    if not pattern.match(value):
        raise ValueError(RETURN_MSG.user_pwd_invalid)
    return value


class UserCreate(UserBase, UserExt):
    password: str
    role: Optional[RoleBase] = None

    validate_password = field_validator("password")(validate_password)


class UserResponse(UserBase, UserExt, ResponseReferenceBase):
    role: Optional[RoleResponse] = None
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
