from typing import Annotated, List, Optional

from pydantic import (
    UUID1,
    BaseModel,
    ConfigDict,
    PlainSerializer,
)
from src.configuration.settings import settings
from src.permissions.schemas import PermissionBase

UUIDString = Annotated[UUID1, PlainSerializer(lambda x: str(x), return_type=str)]


class RoleBase(BaseModel):
    name: str
    domain: str


class RoleResponse(RoleBase):
    id: UUIDString
    permissions: Optional[List[PermissionBase]]

    model_config = ConfigDict(from_attributes=True)


class RolePermissions(BaseModel):
    assign: Optional[List[PermissionBase]]
    unassign: Optional[List[PermissionBase]]
