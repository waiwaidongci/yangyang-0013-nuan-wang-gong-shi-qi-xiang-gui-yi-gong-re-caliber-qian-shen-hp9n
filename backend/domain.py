from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from core import db, enqueue, require
from heat_book import add_entry, add_period, add_spec, add_zone, checks_for, compare, days, entries_for, freeze, notice_for, period_for, publish, run_calculation, zones_for

from calendar_routes import router as operation_router
from followup_routes import router as notice_router
from meter_routes import router as meter_router

router = APIRouter(prefix="/api")
router.include_router(meter_router)
router.include_router(operation_router)
router.include_router(notice_router)
operator = require("operator")
reviewer = require("reviewer")
any_role = require()


class Period(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9-]{3,24}$")
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def short_period(self):
        if (self.ends_on - self.starts_on).days not in range(31):
            raise ValueError("账期须含 1 至 31 个自然日")
        return self


class HeatingZone(BaseModel):
    zone_code: str = Field(pattern=r"^[A-Z0-9-]{2,24}$")
    zone_name: str = Field(min_length=2, max_length=80)
    area_m2: int = Field(ge=100, le=1000000)


class SourceReading(BaseModel):
    zone_id: int = Field(gt=0)
    day: date
    channel: Literal["weather","heat"]
    amount: Decimal = Field(ge=-60, le=25000, decimal_places=3, allow_inf_nan=False)
    source_ref: str = Field(min_length=4, max_length=100)

    @model_validator(mode="after")
    def channel_limits(self):
        if (self.channel == "weather" and self.amount > 55) or (self.channel == "heat" and self.amount < 0):
            raise ValueError("气温应在 -60 至 55°C，热量应为非负 MWh")
        return self


class Version(BaseModel):
    spec_code: str = Field(pattern=r"^[A-Z0-9-]{2,24}$")
    base_celsius: Decimal = Field(ge=0, le=35, decimal_places=1, allow_inf_nan=False)
    description: str = Field(min_length=4, max_length=220)


class PublishNote(BaseModel):
    calculation_id: int = Field(gt=0)
    note: str = Field(min_length=4, max_length=220)


@router.get("/heat-periods")
def periods(_=Depends(any_role)):
    with db() as cx:
        return cx.execute(
            """SELECT p.*,n.notice_code FROM heating_periods p LEFT JOIN public_notices n ON n.period_id=p.id
               ORDER BY p.starts_on DESC,p.id DESC""",
        ).fetchall()


@router.post("/heat-periods", status_code=201)
def register_period(body: Period, _=Depends(operator)):
    with db() as cx:
        return add_period(cx, body.model_dump())


@router.get("/heat-periods/{period_id}/worksheet")
def worksheet(period_id: int, _=Depends(any_role)):
    with db() as cx:
        period, zones, entries = period_for(cx, period_id), zones_for(cx, period_id), entries_for(cx, period_id)
        return {"period":period,"zones":zones,"days":days(period),"entries":entries,
                "missing":checks_for(period,zones,entries),"notice":notice_for(cx,period_id)}


@router.post("/heat-periods/{period_id}/zones", status_code=201)
def register_zone(period_id: int, body: HeatingZone, _=Depends(operator)):
    with db() as cx:
        return add_zone(cx, period_id, body.model_dump())


@router.post("/heat-periods/{period_id}/entries", status_code=201)
def record_source(period_id: int, body: SourceReading, actor=Depends(operator)):
    with db() as cx:
        return add_entry(cx, period_id, body.model_dump(), actor["email"])


@router.get("/heat-periods/{period_id}/specs")
def specs(period_id: int, _=Depends(any_role)):
    with db() as cx:
        period = period_for(cx, period_id)
        definitions = cx.execute("SELECT * FROM normalization_specs WHERE period_id=%s ORDER BY id",
                                 (period_id,)).fetchall()
        summaries = cx.execute(
            """SELECT c.*,s.spec_code,s.base_celsius FROM heat_calculations c
               JOIN normalization_specs s ON s.id=c.spec_id WHERE s.period_id=%s ORDER BY c.id DESC""",
            (period_id,),
        ).fetchall()
        zones = cx.execute(
            """SELECT detail.*,z.zone_name,z.zone_code FROM zone_calculations detail
               JOIN heated_zones z ON z.id=detail.zone_id WHERE z.period_id=%s ORDER BY z.id""", (period_id,),
        ).fetchall()
        return {"period":period,"definitions":definitions,"notice":notice_for(cx,period_id),
                "calculations":[{**row,"zones":[item for item in zones if item["calculation_id"] == row["id"]]}
                                for row in summaries]}


@router.post("/heat-periods/{period_id}/specs", status_code=201)
def create_definition(period_id: int, body: Version, _=Depends(reviewer)):
    with db() as cx:
        return add_spec(cx, period_id, body.model_dump())


@router.post("/heat-periods/{period_id}/specs/{spec_id}/evaluate", status_code=202)
def calculate(period_id: int, spec_id: int, _=Depends(reviewer)):
    with db() as cx:
        row = freeze(cx, period_id, spec_id)
        return {"calculation":row,"job_id":enqueue(cx,"heat_metrics",{"calculation_id":row["id"]})}


@router.get("/heat-periods/{period_id}/compare")
def compare_definitions(period_id: int, first: int, second: int, _=Depends(any_role)):
    with db() as cx:
        return compare(cx, period_id, first, second)


@router.post("/heat-periods/{period_id}/notice")
def authorize_notice(period_id: int, body: PublishNote, actor=Depends(reviewer)):
    with db() as cx:
        return publish(cx, period_id, body.calculation_id, body.note, actor["email"])


def run_job(cx, kind, payload):
    if kind != "heat_metrics":
        raise HTTPException(422, "Unsupported heat normalization job")
    return run_calculation(cx,payload["calculation_id"])


def seed(cx):
    for code, start, end, closed in (
        ("H-1123",date(2026,11,21),date(2026,11,23),False),
        ("H-1116",date(2026,11,15),date(2026,11,16),True),
    ):
        period = add_period(cx, {"code":code,"starts_on":start,"ends_on":end}, seed_only=True)
        if not period:
            continue
        north = add_zone(cx,period["id"],{"zone_code":"NORTH","zone_name":"北岸住宅","area_m2":32000})
        south = add_zone(cx,period["id"],{"zone_code":"SOUTH","zone_name":"南关文教","area_m2":16000})
        for index, day in enumerate(days(period)):
            for zone, temp, heat in ((north,10 + index,22 + 2 * index), (south,12 + index,15 + 3 * index)):
                for channel, amount, prefix in (("weather",temp,"wx-qingqiao"), ("heat",heat,"meter-daily")):
                    if not closed and zone["id"] == south["id"] and day == end and channel == "heat":
                        continue
                    add_entry(cx,period["id"],{"zone_id":zone["id"],"day":day,"channel":channel,"amount":amount,
                              "source_ref":f"{prefix}-{day:%m%d}.csv"}, "seed@heatbook.local")
        calculations = []
        for version, base, description in (("V-18",18,"按 18°C 供热基准"),("V-16",16,"按 16°C 供热基准")):
            spec = add_spec(cx,period["id"],{"spec_code":version,"base_celsius":base,"description":description})
            if closed:
                trial = freeze(cx,period["id"],spec["id"])
                run_calculation(cx,trial["id"])
                calculations.append(trial["id"])
        if closed:
            publish(cx,period["id"],calculations[0],"校对签审口径并按片区面积归一","seed@heatbook.local")
    return {table:cx.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] for table in
            ("heating_periods","heated_zones","daily_inputs","normalization_specs","heat_calculations",
             "zone_calculations","public_notices")}
