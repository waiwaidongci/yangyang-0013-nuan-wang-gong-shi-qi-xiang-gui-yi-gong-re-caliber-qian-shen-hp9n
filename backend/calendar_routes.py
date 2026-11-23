from fastapi import APIRouter,Depends
from calendar_models import ComparisonCase,DayMode
from core import db,require
from operation_calendar import manage_days,mark,scenario

router=APIRouter(prefix="/heat-periods/{period_id}/operations")


@router.get("")
def operation_book(period_id:int,_=Depends(require())):
    with db() as cx:
        return manage_days(cx,period_id)


@router.post("/mark",status_code=201)
def mark_day(period_id:int,body:DayMode,user=Depends(require("operator"))):
    with db() as cx:
        return mark(cx,period_id,body.model_dump(),user["email"])


@router.post("/scenario",status_code=201)
def run_sensitivity(period_id:int,body:ComparisonCase,user=Depends(require("reviewer"))):
    with db() as cx:
        return scenario(cx,period_id,body.model_dump(),user["email"])
