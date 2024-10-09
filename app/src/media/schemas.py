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

    @computed_field
    def uri(self) -> str:
        """Returns preformatted media URI"""
        return f"{settings.media_prefix}/{self.id.hex if settings.media_short_url_id else self.id}"

class MediaAssetReference(BaseModel):
    id: UUIDString
