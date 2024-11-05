from typing import Annotated, List, Optional

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    PlainSerializer,
)
from src.configuration.settings import settings
from src.permissions.schemas import PermissionBase, PermissionResponse

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]


class RoleBase(BaseModel):
    name: str
    domain: str
    title: Optional[str] = None


class RoleResponse(RoleBase):
    id: UUIDString
    permissions: Optional[List[PermissionResponse]]

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    title: Optional[str] = None
    assign: Optional[List[PermissionBase]] = None
    unassign: Optional[List[PermissionBase]] = None
