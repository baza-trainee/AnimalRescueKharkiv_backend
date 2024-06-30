import enum
import uuid
from datetime import date, datetime
from typing import Annotated, Dict, Hashable, List, Optional, TypeVar

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PastDate,
    PlainSerializer,
    Strict,
    computed_field,
    conset,
)

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]

class MediaAssetInfo(BaseModel):
    blob_id: UUIDString
    extension: str
    content_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MediaAssetResponse(BaseModel):
    id: UUIDString
    extension: str
    content_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @property
    @computed_field
    def uri(self) -> str:
        """Returns preformatted media URI"""
        return f"/media/{self.id}"
