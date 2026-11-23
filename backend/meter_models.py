from datetime import date
from decimal import Decimal

from pydantic import BaseModel,Field


class MeterRegistry(BaseModel):
    zone_id:int=Field(gt=0)
    serial:str=Field(min_length=3,max_length=40)
    dial_limit:Decimal=Field(ge=1,le=100000000,decimal_places=3)
    multiplier:Decimal=Field(ge=.001,le=10000,decimal_places=3)


class MeterLog(BaseModel):
    day:date
    before_reading:Decimal=Field(ge=0,le=100000000,decimal_places=3)
    after_reading:Decimal=Field(ge=0,le=100000000,decimal_places=3)
    source_ref:str=Field(min_length=4,max_length=100)
    rollover:bool=False
