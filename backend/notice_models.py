from typing import Literal
from pydantic import BaseModel,Field


class ShareNotice(BaseModel):
    recipient:str=Field(min_length=2,max_length=100)
    channel:Literal["wall","desk","intranet"]


class ReceiptRef(BaseModel):
    delivery_ref:str=Field(min_length=4,max_length=180)


class Objection(BaseModel):
    category:Literal["wording","source","metric"]
    question:str=Field(min_length=6,max_length=260)


class ResponseNote(BaseModel):
    resolution:Literal["clarified","addendum","recheck_next_period"]
    answer:str=Field(min_length=6,max_length=260)
    replacement_text:str|None=Field(default=None,min_length=6,max_length=260)
