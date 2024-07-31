import re
from typing import Optional

from pydantic import UUID1, BaseModel, ConfigDict, EmailStr, ValidationError, field_validator
from src.configuration.settings import settings
from src.roles.schemas import RoleBase, RoleResponse


class UserBase(BaseModel):
    username: str
    domain: str


class UserCreate(UserBase):
    email: EmailStr
    password: str


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

    @field_validator("password_new")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Check the new password using the regular expression from the password_regex settings field"""
        pattern = re.compile(settings.password_regex)
        if not pattern.match(value):
            msg = "Password is incorrect"
            raise ValidationError(msg)
        return value
