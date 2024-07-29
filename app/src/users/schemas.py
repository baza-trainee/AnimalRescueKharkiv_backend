from typing import Annotated, List, Optional

from pydantic import (
    UUID1,
    BaseModel,
    ConfigDict,
    PlainSerializer,
)
from src.roles.models import Role

UUIDString = Annotated[UUID1, PlainSerializer(lambda x: str(x), return_type=str)]


class UserBase(BaseModel):
    username: str
    email: str
    domain: str
    password: str
    role: Optional[Role]


class UserResponse(UserBase):
    id: UUIDString

    model_comfig = ConfigDict(from_attributes=True)
