from fastapi import HTTPException

from calendar_math import simulate
from heat_book import calc_for,days,period_for


def latest_marks(cx,period_id):
    return cx.execute(
        """SELECT DISTINCT ON (day) * FROM schedule_marks WHERE period_id=%s ORDER BY day,id DESC""",
        (period_id,),
    ).fetchall()


def manage_days(cx,period_id):
    period=period_for(cx,period_id)
    marks=latest_marks(cx,period_id)
    scenarios=cx.execute(
        """SELECT v.*,s.spec_code FROM degree_day_scenarios v
           JOIN heat_calculations c ON c.id=v.calculation_id JOIN normalization_specs s ON s.id=c.spec_id
           WHERE s.period_id=%s ORDER BY v.id DESC""",(period_id,),
    ).fetchall()
    return {"days":days(period),"marks":marks,"scenarios":scenarios}


def mark(cx,period_id,body,user):
    period=period_for(cx,period_id,lock=True)
    if not period["starts_on"]<=body["day"]<=period["ends_on"]:
        raise HTTPException(409,"情景日历只接收本账期日期")
    return cx.execute(
        """INSERT INTO schedule_marks(period_id,day,mode,evidence,marked_by)
           VALUES (%s,%s,%s,%s,%s) RETURNING *""",(period_id,body["day"],body["mode"],body["evidence"],user),
    ).fetchone()


def scenario(cx,period_id,body,user):
    period=period_for(cx,period_id,lock=True)
    baseline=calc_for(cx,period_id,body["calculation_id"])
    if baseline["phase"]!="ready":
        raise HTTPException(409,"只能从已完成的归一快照展开情景")
    marks=latest_marks(cx,period_id)
    standby={entry["day"] for entry in marks if entry["mode"]=="standby"}
    active=[day for day in days(period) if day not in standby]
    if not active:
        raise HTTPException(409,"没有开启日可用于情景计算")
    zones=cx.execute("SELECT * FROM heated_zones WHERE id=ANY(%s) ORDER BY id",(baseline["zone_ids"],)).fetchall()
    raw=cx.execute("SELECT * FROM daily_inputs WHERE id=ANY(%s)",(baseline["entry_ids"],)).fetchall()
    metrics=simulate(zones,raw,set(active),body["candidate_base"],baseline["normalized"])
    row=cx.execute(
        """INSERT INTO degree_day_scenarios(calculation_id,candidate_base,active_days,calendar_marks,scope_area,total_mwh,
            weighted_hdd,normalized,difference,reviewed_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (baseline["id"],body["candidate_base"],active,[entry["id"] for entry in marks], metrics["scope_area"],
         metrics["total_mwh"],metrics["period_hdd"],metrics["normalized"],metrics["difference"],user),
    ).fetchone()
    return row
