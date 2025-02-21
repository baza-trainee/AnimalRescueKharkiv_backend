import re
from typing import Annotated, Optional

from fastapi import HTTPException, Query, status
from pydantic import UUID4, BaseModel, Field, PlainSerializer, field_validator
from src.exceptions.exceptions import RETURN_MSG

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]
SORTING_VALIDATION_REGEX = r"^[a-zA-Z0-9_]+\|(asc|desc)$"

class ReferenceBase(BaseModel):
    pass


class UUIDReferenceBase(ReferenceBase):
    id: Optional[UUID4] = Field(default=None)


class IntReferenceBase(ReferenceBase):
    id: int


class ResponseReferenceBase(ReferenceBase):
    id: UUIDString

class Sorting(BaseModel):
    sort: str | None = Query(default="created_at|desc",
                                description="Sort option in format of {field}|{direction}. Default: created_at|desc")

    @field_validator("sort")
    @classmethod
    def validate_regex(cls, value: str) -> str:
        """Validates sorting option value via regular expression"""
        if not re.match(SORTING_VALIDATION_REGEX, value):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=RETURN_MSG.crm_illegal_sort)
        return value
