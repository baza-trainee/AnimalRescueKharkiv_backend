from datetime import datetime
from typing import Annotated

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    PlainSerializer,
    computed_field,
)
from src.configuration.settings import settings

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]

class PermissionResponse(BaseModel):
    id: UUIDString
    access_right: str

    model_config = ConfigDict(from_attributes=True)
