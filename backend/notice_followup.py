from fastapi import HTTPException

from heat_book import notice_for,period_for
from notice_triage import validate_resolution


def public_period(cx,period_id,*,lock=False):
    period_for(cx,period_id,lock=lock)
    original=notice_for(cx,period_id)
    if not original:
        raise HTTPException(409,"已签审的公示才可登记发送或异议")
    return original


def followup(cx,period_id):
    period_for(cx,period_id)
    deliveries=cx.execute("SELECT * FROM notice_copies WHERE period_id=%s ORDER BY id DESC",(period_id,)).fetchall()
    cases=cx.execute(
        """SELECT o.*,d.recipient,a.update_code,a.replacement_text FROM notice_objections o
           JOIN notice_copies d ON d.id=o.copy_id LEFT JOIN notice_addenda a ON a.objection_id=o.id
           WHERE d.period_id=%s ORDER BY o.id DESC""",(period_id,),
    ).fetchall()
    return {"notice":notice_for(cx,period_id),"copies":deliveries,"objections":cases}


def enrol(cx,period_id,body,actor):
    public_period(cx,period_id,lock=True)
    return cx.execute(
        """INSERT INTO notice_copies(period_id,recipient,channel,registered_by)
           VALUES (%s,%s,%s,%s) RETURNING *""",(period_id,body["recipient"],body["channel"],actor),
    ).fetchone()


def acknowledge(cx,period_id,copy_id,ref,actor):
    public_period(cx,period_id,lock=True)
    row=cx.execute(
        """UPDATE notice_copies SET delivery_ref=%s,delivered_by=%s WHERE id=%s AND period_id=%s
           AND delivery_ref IS NULL RETURNING *""",(ref,actor,copy_id,period_id),
    ).fetchone()
    if not row:
        raise HTTPException(409,"仅待送达副本可登记收到的分发凭证")
    return row


def file_case(cx,period_id,copy_id,body,actor):
    public_period(cx,period_id,lock=True)
    delivered=cx.execute("SELECT id FROM notice_copies WHERE id=%s AND period_id=%s AND delivery_ref IS NOT NULL",
                         (copy_id,period_id)).fetchone()
    if not delivered:
        raise HTTPException(409,"先确认对应公示副本已送达")
    return cx.execute(
        """INSERT INTO notice_objections(copy_id,category,question,filed_by)
           VALUES (%s,%s,%s,%s) RETURNING *""",(copy_id,body["category"],body["question"],actor),
    ).fetchone()


def resolve(cx,period_id,case_id,body,user):
    original=public_period(cx,period_id,lock=True)
    row=next((case for case in followup(cx,period_id)["objections"] if case["id"]==case_id),None)
    if not row or row["resolution"]:
        raise HTTPException(409,"只可签审本账期尚未答复的异议")
    validate_resolution(row,body)
    updated=cx.execute(
        "UPDATE notice_objections SET resolution=%s,answer=%s,answered_by=%s WHERE id=%s RETURNING *",
        (body["resolution"],body["answer"],user,case_id),
    ).fetchone()
    if body["resolution"]=="addendum":
        addendum=cx.execute(
            """INSERT INTO notice_addenda(objection_id,update_code,replacement_text)
               VALUES (%s,%s,%s) RETURNING *""",
            (case_id,f"{original['notice_code']}-A{case_id}",body["replacement_text"]),
        ).fetchone()
        return {**updated,"addendum":addendum}
    return updated
