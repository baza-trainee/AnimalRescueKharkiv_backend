from typing import Optional

from pydantic import UUID1, BaseModel, ConfigDict, EmailStr
from src.roles.schemas import RoleBase, RoleResponse


class UserBase(BaseModel):
    username: str
    domain: str


class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[RoleBase]


class UserResponse(UserBase):
    id: UUID1
    email: EmailStr
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)
