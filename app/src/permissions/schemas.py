from typing import Annotated, Optional

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    PlainSerializer,
)
from src.base_schemas import ResponseReferenceBase, SanitizedString
from src.configuration.settings import settings


class PermissionBase(BaseModel):
    entity: SanitizedString
    operation: SanitizedString
    title: Optional[SanitizedString] = None


class PermissionResponse(PermissionBase, ResponseReferenceBase):
    model_config = ConfigDict(from_attributes=True)

class PermissionUpdate(BaseModel):
    title: Optional[SanitizedString] = None
