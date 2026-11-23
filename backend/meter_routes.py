from fastapi import APIRouter,Depends
from core import db,require
from meter_journal import meter_ledger,record_meter,register_meter
from meter_models import MeterLog,MeterRegistry

router=APIRouter(prefix="/heat-periods/{period_id}/meters")


@router.get("")
def meter_book(period_id:int,_=Depends(require())):
    with db() as cx:
        return meter_ledger(cx,period_id)


@router.post("",status_code=201)
def commission(period_id:int,body:MeterRegistry,_=Depends(require("operator"))):
    with db() as cx:
        return register_meter(cx,period_id,body.model_dump())


@router.post("/{meter_id}/read",status_code=201)
def daily_counter(period_id:int,meter_id:int,body:MeterLog,user=Depends(require("operator"))):
    with db() as cx:
        return record_meter(cx,period_id,meter_id,body.model_dump(),user["email"])
