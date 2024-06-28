import uuid
import enum
from typing import Dict, Hashable, List, Optional, Annotated, TypeVar
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr, PastDate, PlainSerializer, Strict, conset, UUID4, computed_field
from datetime import date

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
    @property
    def uri(self) -> str:
        return f"/media/{self.id}"
