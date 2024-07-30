from typing import Optional

from pydantic import UUID1, BaseModel, ConfigDict, EmailStr
from src.roles.schemas import RoleBase


class UserBase(BaseModel):
    username: str
    domain: str


class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: UUID1
    email: EmailStr
    role: Optional[RoleBase] = None

    model_config = ConfigDict(from_attributes=True)
