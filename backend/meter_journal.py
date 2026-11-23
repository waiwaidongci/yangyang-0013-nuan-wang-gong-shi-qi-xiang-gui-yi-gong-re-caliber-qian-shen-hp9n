from datetime import timedelta

from fastapi import HTTPException
from heat_book import add_entry,period_for,writable_period,zones_for
from meter_units import counter_mwh


def meter_ledger(cx,period_id):
    period_for(cx,period_id)
    return {
        "meters":cx.execute(
            """SELECT m.*,z.zone_name FROM zone_meters m JOIN heated_zones z ON z.id=m.zone_id
               WHERE z.period_id=%s ORDER BY z.id""",(period_id,),
        ).fetchall(),
        "reads":cx.execute(
            """SELECT j.*,i.amount,i.source_ref,i.revision FROM meter_journal j
               JOIN daily_inputs i ON i.id=j.input_id JOIN heated_zones z ON z.id=i.zone_id
               WHERE z.period_id=%s ORDER BY j.day DESC,j.id DESC""",(period_id,),
        ).fetchall(),
    }


def register_meter(cx,period_id,body):
    writable_period(cx,period_id)
    if body["zone_id"] not in {zone["id"] for zone in zones_for(cx,period_id)}:
        raise HTTPException(409,"计量表必须登记在当前账期片区")
    return cx.execute(
        """INSERT INTO zone_meters(zone_id,serial,dial_limit,multiplier)
           VALUES (%s,%s,%s,%s) RETURNING *""",
        (body["zone_id"],body["serial"],body["dial_limit"],body["multiplier"]),
    ).fetchone()


def readings(cx,meter_id,day):
    return cx.execute(
        """SELECT * FROM meter_journal WHERE meter_id=%s AND day=%s ORDER BY id DESC LIMIT 1""",
        (meter_id,day),
    ).fetchone()


def record_meter(cx,period_id,meter_id,body,actor):
    writable_period(cx,period_id)
    meter=next((row for row in meter_ledger(cx,period_id)["meters"] if row["id"]==meter_id),None)
    if not meter:
        raise HTTPException(404,"该账期没有此采暖表号")
    day,first,last=body["day"],body["before_reading"],body["after_reading"]
    prior=readings(cx,meter_id,day-timedelta(days=1))
    succeeding=readings(cx,meter_id,day+timedelta(days=1))
    if (prior and first!=prior["after_reading"]) or (succeeding and last!=succeeding["before_reading"]):
        raise HTTPException(409,"昨日尾数或次日首数与本次表底不符，先核对衔接")
    mwh=counter_mwh(meter["dial_limit"],meter["multiplier"],first,last,body["rollover"])
    input_row=add_entry(cx,period_id,{"zone_id":meter["zone_id"],"day":day,"channel":"heat",
                        "amount":mwh,"source_ref":body["source_ref"]},actor,via_meter=True)
    earlier=readings(cx,meter_id,day)
    row=cx.execute(
        """INSERT INTO meter_journal(meter_id,input_id,day,before_reading,after_reading,rollover,previous_journal_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (meter_id,input_row["id"],day,first,last,body["rollover"],earlier["id"] if earlier else None),
    ).fetchone()
    return {**row,"amount":mwh,"daily_revision":input_row["revision"]}
