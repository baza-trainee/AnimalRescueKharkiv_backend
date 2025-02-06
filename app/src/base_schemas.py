from typing import Annotated, Optional

from pydantic import UUID4, BaseModel, Field, PlainSerializer

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]


class ReferenceBase(BaseModel):
    pass


class UUIDReferenceBase(ReferenceBase):
    id: Optional[UUID4] = Field(default=None)


class IntReferenceBase(ReferenceBase):
    id: int


class ResponseReferenceBase(ReferenceBase):
    id: UUIDString
