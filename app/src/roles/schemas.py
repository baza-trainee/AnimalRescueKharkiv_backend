from typing import Annotated

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    PlainSerializer,
)
from src.configuration.settings import settings

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]


class RoleBase(BaseModel):
    name: str
    domain: str


class RoleResponse(RoleBase):
    id: UUIDString

    model_config = ConfigDict(from_attributes=True)
