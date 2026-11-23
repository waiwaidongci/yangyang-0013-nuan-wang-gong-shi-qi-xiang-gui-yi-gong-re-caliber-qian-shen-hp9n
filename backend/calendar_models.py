from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel,Field


class DayMode(BaseModel):
    day:date
    mode:Literal["heating","standby"]
    evidence:str=Field(min_length=4,max_length=160)


class ComparisonCase(BaseModel):
    calculation_id:int=Field(gt=0)
    candidate_base:Decimal=Field(ge=0,le=35,decimal_places=1)
