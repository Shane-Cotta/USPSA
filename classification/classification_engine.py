from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, List, Sequence


def _quantize4(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def compute_percent(hit_factor, hhf) -> Decimal:
    hf = Decimal(hit_factor)
    hhf_val = Decimal(hhf)
    if hhf_val == 0:
        return Decimal("0")
    return _quantize4((hf / hhf_val) * Decimal("100"))


def cap_percent(raw_percent: Decimal) -> Decimal:
    capped = min(Decimal("110.0"), Decimal(raw_percent))
    return _quantize4(capped)


def compute_sda(capped_percents: Iterable[Decimal]) -> Decimal:
    values = [Decimal(v) for v in capped_percents]
    if not values:
        return Decimal("0.0000")
    mean = sum(values) / Decimal(len(values))
    return _quantize4(mean)


def apply_mro(daily_scores: List[dict]) -> List[dict]:
    latest_per_stage = {}
    for score in sorted(daily_scores, key=lambda s: s["date"], reverse=True):
        stage = score["stage_code"]
        if stage not in latest_per_stage:
            latest_per_stage[stage] = score["date"]
        score["is_mro"] = score["date"] == latest_per_stage[stage]
    return daily_scores


def compute_active_window(mro_scores: Sequence[dict]) -> List[dict]:
    active = [s for s in mro_scores if s.get("is_mro")]
    active_sorted = sorted(active, key=lambda s: s["date"], reverse=True)
    return active_sorted[:8]


def class_from_percent(percent: Decimal) -> str:
    val = Decimal(percent)
    if val >= Decimal("95"):
        return "GM"
    if val >= Decimal("85"):
        return "M"
    if val >= Decimal("75"):
        return "A"
    if val >= Decimal("60"):
        return "B"
    if val >= Decimal("40"):
        return "C"
    if val > 0:
        return "D"
    return "Unclassified"


def highest_achieved_class(history_percents: Iterable[Decimal]) -> str:
    best = "Unclassified"
    order = ["Unclassified", "D", "C", "B", "A", "M", "GM"]
    for pct in history_percents:
        cls = class_from_percent(pct)
        if order.index(cls) > order.index(best):
            best = cls
    return best


def compute_division_classification(mro_scores: Sequence[dict]) -> dict:
    window = compute_active_window(mro_scores)
    active_scores = len(window)
    if active_scores < 4:
        return {
            "current_percent": Decimal("0.0000"),
            "implied_class": "Unclassified",
            "used_scores": [],
            "active_scores": active_scores,
            "is_classified": False,
            "highest_badge": highest_achieved_class([s["sda_percent"] for s in mro_scores]),
            "active_window": window,
        }

    if active_scores == 4:
        used = window
    else:
        used = sorted(window, key=lambda s: Decimal(s["sda_percent"]), reverse=True)[:6]

    current_percent = compute_sda([s["sda_percent"] for s in used])
    implied_class = class_from_percent(current_percent)
    highest_badge = highest_achieved_class([s["sda_percent"] for s in mro_scores])
    return {
        "current_percent": current_percent,
        "implied_class": implied_class,
        "used_scores": used,
        "active_scores": active_scores,
        "is_classified": True,
        "highest_badge": highest_badge,
        "active_window": window,
    }
