from typing import Annotated, List, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict
from src.base_schemas import ResponseReferenceBase
from src.configuration.settings import settings
from src.crm.schemas import PastOrPresentDate


class LabeledStats(BaseModel):
    labels: List[str]
    data: List[int]

class AnimalStatusStats(BaseModel):
    sterilized: int
    adopted: int
    dead: int
    total: int

class DateQuery(BaseModel):
    from_date: Optional[PastOrPresentDate] = None
    to_date: Optional[PastOrPresentDate] = None
