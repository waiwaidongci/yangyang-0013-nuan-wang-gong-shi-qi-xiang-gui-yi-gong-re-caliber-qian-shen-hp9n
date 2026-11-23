from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException


def counter_mwh(dial,multiplier,start,end,rollover):
    if max(start,end)>=dial:
        raise HTTPException(409,"表盘读数须严格小于清零上界")
    if rollover!=(end<start):
        raise HTTPException(409,"倒走读数与清零标记不一致，请核对表盘和交班记录")
    delta=(end-start+(dial if rollover else Decimal(0)))*multiplier
    if delta>25000:
        raise HTTPException(409,"倍率折算热量超出单日日账量程")
    return delta.quantize(Decimal(".001"),rounding=ROUND_HALF_UP)
