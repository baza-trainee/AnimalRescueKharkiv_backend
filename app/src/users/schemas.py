import re
from typing import Optional

from pydantic import UUID1, BaseModel, ConfigDict, EmailStr, field_validator
from src.configuration.settings import settings
from src.roles.schemas import RoleBase, RoleResponse


class UserBase(BaseModel):
    username: str
    domain: str


def validate_password(value: str) -> str:
    """Check the password using the regular expression from the password_regex settings field"""
    pattern = re.compile(settings.password_regex)
    if not pattern.match(value):
        msg = ("The minimum password length is 8 characters, "
        "the password must include at least 1 number, 1 letter and 1 special character")
        raise ValueError(msg)
    return value


class UserCreate(UserBase):
    email: EmailStr
    password: str

    validate_password = field_validator("password")(validate_password)


class UserResponse(UserBase):
    id: UUID1
    email: EmailStr
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[RoleBase]


class UserPasswordUpdate(BaseModel):
    password_old: str
    password_new: str

    validate_new_password = field_validator("password_new")(validate_password)
