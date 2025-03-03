from typing import List, Optional, Self

from pydantic import BaseModel, model_validator
from src.configuration.settings import settings
from src.crm.schemas import PastOrPresentDate
from src.exceptions.exceptions import RETURN_MSG


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

    @model_validator(mode="after")
    def __validate_date_range(self) -> Self:
        if self.to_date and self.from_date and self.to_date < self.from_date:
            raise ValueError(RETURN_MSG.crm_date_range_invalid % ("date_to", "date_from"))
        return self
