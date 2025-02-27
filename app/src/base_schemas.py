import re
from typing import Annotated, Optional

from fastapi import HTTPException, Query, status
from pydantic import UUID4, BaseModel, BeforeValidator, Field, PlainSerializer, field_validator
from src.exceptions.exceptions import RETURN_MSG

UUIDString = Annotated[UUID4, PlainSerializer(lambda x: str(x), return_type=str)]

def sanitize_string(value: str) -> str:
    """Sanitizes and validates string for empty value"""
    value = value.strip()
    if value:
        return value
    raise ValueError(RETURN_MSG.non_empty_string)

SanitizedString = Annotated[str, BeforeValidator(sanitize_string)]
SORTING_VALIDATION_REGEX = r"^[a-zA-Z0-9_]+\|(asc|desc)$"

class ReferenceBase(BaseModel):
    pass


class UUIDReferenceBase(ReferenceBase):
    id: Optional[UUID4] = Field(default=None)


class IntReferenceBase(ReferenceBase):
    id: int


class ResponseReferenceBase(ReferenceBase):
    id: UUIDString

def validate_sorting(value: str) -> str:
    """Validates sorting option value via regular expression"""
    if not re.match(SORTING_VALIDATION_REGEX, value):
        raise ValueError(RETURN_MSG.illegal_sort)
    return value

SortingStr = Annotated[str, BeforeValidator(validate_sorting), Field(
        example="created_at|desc",
        json_schema_extra={"type": "string", "format": "{field}|{direction}"},
    )]

class Sorting(BaseModel):
    sort: Optional[SortingStr] = Query(default="created_at|desc",
                                description="Sort option in format of {field}|{direction}. Default: created_at|desc")
