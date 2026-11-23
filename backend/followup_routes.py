from fastapi import APIRouter,Depends
from core import db,require
from notice_followup import acknowledge,enrol,file_case,followup,resolve
from notice_models import Objection,ReceiptRef,ResponseNote,ShareNotice

router=APIRouter(prefix="/heat-periods/{period_id}/followup")
reviewer=require("reviewer")
operator=require("operator")


@router.get("")
def notice_archive(period_id:int,_=Depends(require())):
    with db() as cx:
        return followup(cx,period_id)


@router.post("/copies",status_code=201)
def register_delivery(period_id:int,body:ShareNotice,user=Depends(reviewer)):
    with db() as cx:
        return enrol(cx,period_id,body.model_dump(),user["email"])


@router.post("/copies/{copy_id}/receipt")
def delivered(period_id:int,copy_id:int,body:ReceiptRef,user=Depends(operator)):
    with db() as cx:
        return acknowledge(cx,period_id,copy_id,body.delivery_ref,user["email"])


@router.post("/copies/{copy_id}/object",status_code=201)
def request_explanation(period_id:int,copy_id:int,body:Objection,user=Depends(operator)):
    with db() as cx:
        return file_case(cx,period_id,copy_id,body.model_dump(),user["email"])


@router.post("/objections/{case_id}/answer")
def answer_objection(period_id:int,case_id:int,body:ResponseNote,user=Depends(reviewer)):
    with db() as cx:
        return resolve(cx,period_id,case_id,body.model_dump(),user["email"])
