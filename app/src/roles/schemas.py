from typing import Annotated, List, Optional

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    PlainSerializer,
)
from src.base_schemas import ResponseReferenceBase, SanitizedString
from src.configuration.settings import settings
from src.permissions.schemas import PermissionBase, PermissionResponse


class RoleBase(BaseModel):
    name: SanitizedString
    domain: SanitizedString
    title: Optional[SanitizedString] = None


class RoleResponse(RoleBase, ResponseReferenceBase):
    permissions: Optional[List[PermissionResponse]]

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    title: Optional[SanitizedString] = None
    assign: Optional[List[PermissionBase]] = None
    unassign: Optional[List[PermissionBase]] = None
