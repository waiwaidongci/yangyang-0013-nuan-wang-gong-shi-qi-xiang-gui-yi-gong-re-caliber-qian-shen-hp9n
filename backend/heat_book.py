from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException

from degree_days import degrees, normalize


def period_for(cx, period_id, *, lock=False):
    row = cx.execute("SELECT * FROM heating_periods WHERE id=%s" + (" FOR UPDATE" if lock else ""),
                     (period_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "找不到供热账期")
    return row


def notice_for(cx, period_id):
    return cx.execute(
        """SELECT n.*,s.spec_code,c.total_mwh,c.scope_area,c.area_hdd,c.period_hdd,
           c.raw_kwh_m2,c.normalized
           FROM public_notices n JOIN heat_calculations c ON c.id=n.calculation_id
           JOIN normalization_specs s ON s.id=c.spec_id WHERE n.period_id=%s""",
        (period_id,),
    ).fetchone()


def writable_period(cx, period_id):
    period = period_for(cx, period_id, lock=True)
    if notice_for(cx, period_id):
        raise HTTPException(409, "该账期已签发公示，签审档案保持冻结")
    return period


def add_period(cx, data, *, seed_only=False):
    row = cx.execute(
        """INSERT INTO heating_periods(code,starts_on,ends_on) VALUES (%(code)s,%(starts_on)s,%(ends_on)s)
           ON CONFLICT(code) DO NOTHING RETURNING *""", data,
    ).fetchone()
    if not row and not seed_only:
        raise HTTPException(409, "该供热账期编号已登记")
    return row


def zones_for(cx, period_id):
    return cx.execute("SELECT * FROM heated_zones WHERE period_id=%s ORDER BY id", (period_id,)).fetchall()


def entries_for(cx, period_id):
    return cx.execute(
        """SELECT DISTINCT ON (i.zone_id,i.day,i.channel) i.* FROM daily_inputs i
           JOIN heated_zones z ON z.id=i.zone_id WHERE z.period_id=%s
           ORDER BY i.zone_id,i.day,i.channel,i.revision DESC""", (period_id,),
    ).fetchall()


def add_zone(cx, period_id, data):
    writable_period(cx, period_id)
    if len(zones_for(cx, period_id)) >= 12:
        raise HTTPException(409, "本账期最多登记 12 个核算区")
    row = cx.execute(
        """INSERT INTO heated_zones(period_id,zone_code,zone_name,area_m2)
           VALUES (%s,%s,%s,%s) ON CONFLICT(period_id,zone_code) DO NOTHING RETURNING *""",
        (period_id,data["zone_code"],data["zone_name"],data["area_m2"]),
    ).fetchone()
    if row is None:
        raise HTTPException(409, "该核算区编号已存在")
    return row


def add_entry(cx, period_id, data, email, *, via_meter=False):
    period = writable_period(cx, period_id)
    if not period["starts_on"] <= data["day"] <= period["ends_on"]:
        raise HTTPException(409, "日账日期超出选定账期")
    if data["zone_id"] not in {zone["id"] for zone in zones_for(cx, period_id)}:
        raise HTTPException(409, "日账须属于当前账期核算区")
    if data["channel"]=="heat" and not via_meter and cx.execute(
        "SELECT id FROM zone_meters WHERE zone_id=%s",(data["zone_id"],),
    ).fetchone():
        raise HTTPException(409,"该片区已经接入累计表，请从表底流水录入供热量")
    previous = cx.execute(
        """SELECT revision FROM daily_inputs WHERE zone_id=%s AND day=%s AND channel=%s
           ORDER BY revision DESC LIMIT 1""", (data["zone_id"],data["day"],data["channel"]),
    ).fetchone()
    return cx.execute(
        """INSERT INTO daily_inputs(zone_id,day,channel,amount,source_ref,revision,entered_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (data["zone_id"],data["day"],data["channel"],data["amount"],data["source_ref"],
         previous["revision"] + 1 if previous else 1,email),
    ).fetchone()


def days(period):
    return [period["starts_on"] + timedelta(days=offset)
            for offset in range((period["ends_on"] - period["starts_on"]).days + 1)]


def checks_for(period, zones, entries):
    keys = {(row["zone_id"],row["day"],row["channel"]) for row in entries}
    return [
        {"zone_id": zone["id"], "zone_code": zone["zone_code"], "day": day, "channel": channel}
        for zone in zones for day in days(period) for channel in ("weather","heat")
        if (zone["id"],day,channel) not in keys
    ]


def add_spec(cx, period_id, data):
    writable_period(cx, period_id)
    row = cx.execute(
        """INSERT INTO normalization_specs(period_id,spec_code,base_celsius,description)
           VALUES (%s,%s,%s,%s) ON CONFLICT(period_id,spec_code) DO NOTHING RETURNING *""",
        (period_id,data["spec_code"],data["base_celsius"],data["description"]),
    ).fetchone()
    if row is None:
        raise HTTPException(409, "该版口径编号已存在")
    return row


def calc_for(cx, period_id, calculation_id):
    row = cx.execute(
        """SELECT c.*,s.spec_code,s.period_id,s.base_celsius FROM heat_calculations c
           JOIN normalization_specs s ON s.id=c.spec_id WHERE s.period_id=%s AND c.id=%s""",
        (period_id,calculation_id),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "找不到本账期的归一快照")
    return row


def freeze(cx, period_id, spec_id):
    period = writable_period(cx, period_id)
    spec = cx.execute("SELECT * FROM normalization_specs WHERE id=%s AND period_id=%s",
                      (spec_id,period_id)).fetchone()
    if spec is None:
        raise HTTPException(404, "找不到本账期的口径版次")
    zones, entries = zones_for(cx, period_id), entries_for(cx, period_id)
    if not zones:
        raise HTTPException(409, "先登记核算区和采暖面积")
    missing = checks_for(period, zones, entries)
    if missing:
        first = missing[0]
        source = "气温" if first["channel"] == "weather" else "热量"
        raise HTTPException(409, f"缺少 {len(missing)} 项日账，先补 {first['zone_code']} {first['day']} {source}")
    for zone in zones:
        hdd = sum((degrees(spec["base_celsius"], row["amount"]) for row in entries
                   if row["zone_id"] == zone["id"] and row["channel"] == "weather"), Decimal(0))
        if hdd == 0:
            raise HTTPException(409, f"{zone['zone_code']} 采暖度日为零，口径无法归一")
    return cx.execute(
        """INSERT INTO heat_calculations(spec_id,zone_ids,entry_ids) VALUES (%s,%s,%s) RETURNING *""",
        (spec_id,[zone["id"] for zone in zones],[row["id"] for row in entries]),
    ).fetchone()


def run_calculation(cx, calculation_id):
    row = cx.execute(
        """SELECT c.*,s.base_celsius FROM heat_calculations c
           JOIN normalization_specs s ON s.id=c.spec_id WHERE c.id=%s FOR UPDATE OF c""",
        (calculation_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("缺少冻结归一快照")
    if row["phase"] == "ready":
        return {"id": calculation_id, "phase": "ready"}
    zones = cx.execute("SELECT * FROM heated_zones WHERE id=ANY(%s) ORDER BY id", (row["zone_ids"],)).fetchall()
    raw = cx.execute("SELECT * FROM daily_inputs WHERE id=ANY(%s) ORDER BY id", (row["entry_ids"],)).fetchall()
    metrics, detail = normalize(zones, raw, row["base_celsius"])
    cx.execute(
        """UPDATE heat_calculations SET phase='ready',total_mwh=%(total_mwh)s,scope_area=%(scope_area)s,
           area_hdd=%(area_hdd)s,period_hdd=%(period_hdd)s,raw_kwh_m2=%(raw_kwh_m2)s,
           normalized=%(normalized)s WHERE id=%(id)s""", {**metrics,"id":calculation_id},
    )
    with cx.cursor() as cursor:
        cursor.executemany(
            """INSERT INTO zone_calculations(calculation_id,zone_id,total_mwh,hdd,normalized)
               VALUES (%(calculation_id)s,%(zone_id)s,%(total_mwh)s,%(hdd)s,%(normalized)s)""",
            [{**zone, "calculation_id":calculation_id} for zone in detail],
        )
    return {"id":calculation_id,"phase":"ready"}


def compare(cx, period_id, id_a, id_b):
    a, b = calc_for(cx, period_id, id_a), calc_for(cx, period_id, id_b)
    if a["spec_id"] == b["spec_id"] or a["phase"] != "ready" or b["phase"] != "ready":
        raise HTTPException(409, "请选择两版已完成的不同口径")
    if a["entry_ids"] != b["entry_ids"] or a["zone_ids"] != b["zone_ids"]:
        raise HTTPException(409, "两版日账冻结范围不同，请使用相同源版本重新计算")
    return {"base":a,"candidate":b,"normalized_delta":b["normalized"]-a["normalized"],
            "degree_days_delta":b["period_hdd"]-a["period_hdd"]}


def publish(cx, period_id, trial_id, note, reviewer):
    period = writable_period(cx, period_id)
    result = calc_for(cx, period_id, trial_id)
    if result["phase"] != "ready":
        raise HTTPException(409, "须等待归一计算完成后签审")
    if result["zone_ids"] != [zone["id"] for zone in zones_for(cx, period_id)] or result["entry_ids"] != [
        row["id"] for row in entries_for(cx, period_id)
    ]:
        raise HTTPException(409, "台账已有新修订，当前快照不可公示，须重算")
    return cx.execute(
        """INSERT INTO public_notices(period_id,calculation_id,notice_code,note,signed_by)
           VALUES (%s,%s,%s,%s,%s) RETURNING *""",
        (period_id,trial_id,"NW-"+period["code"],note,reviewer),
    ).fetchone()
