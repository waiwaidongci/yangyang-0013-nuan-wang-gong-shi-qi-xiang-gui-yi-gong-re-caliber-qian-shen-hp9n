from collections import defaultdict
from decimal import Decimal


def degrees(base: Decimal, observed: Decimal) -> Decimal:
    return max(base - observed, Decimal(0))


def normalize(zones: list[dict], readings: list[dict], base: Decimal) -> tuple[dict, list[dict]]:
    tallies = defaultdict(lambda: {"mwh": Decimal(0), "hdd": Decimal(0)})
    for entry in readings:
        channel = entry["channel"]
        tally = tallies[entry["zone_id"]]
        if channel == "heat":
            tally["mwh"] += entry["amount"]
        else:
            tally["hdd"] += degrees(base, entry["amount"])
    scope_area = sum(zone["area_m2"] for zone in zones)
    total_mwh = sum((tally["mwh"] for tally in tallies.values()), Decimal(0))
    area_hdd = sum((zone["area_m2"] * tallies[zone["id"]]["hdd"] for zone in zones), Decimal(0))
    metrics = {
        "total_mwh": total_mwh,
        "scope_area": scope_area,
        "area_hdd": area_hdd,
        "period_hdd": area_hdd / scope_area,
        "raw_kwh_m2": total_mwh * 1000 / scope_area,
        "normalized": total_mwh * 1000 / area_hdd,
    }
    detail = []
    for zone in zones:
        tally = tallies[zone["id"]]
        detail.append({"zone_id": zone["id"], "total_mwh": tally["mwh"], "hdd": tally["hdd"],
                       "normalized": tally["mwh"] * 1000 / (tally["hdd"] * zone["area_m2"])})
    return metrics, detail
