from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from degree_days import degrees,normalize


def simulate(zones,raw,days,base,reference):
    selection=[row for row in raw if row["day"] in days]
    for zone in zones:
        hdd=sum(degrees(base,row["amount"]) for row in selection
                if row["zone_id"]==zone["id"] and row["channel"]=="weather")
        if not hdd:
            raise HTTPException(409,f"{zone['zone_code']} 在情景开启日的采暖度日为零")
    metrics,_=normalize(zones,selection,base)
    return {**metrics,"difference":(metrics["normalized"]-reference).quantize(Decimal(".000001"),rounding=ROUND_HALF_UP)}
