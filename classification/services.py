from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List

from django.db import transaction

from . import classification_engine as engine
from .models import ClassifierAttempt, DailyAggregateScore, Division, DivisionSummary, ShooterProfile


@dataclass
class DailyScore:
    match_date: date
    stage_code: str
    sda_percent: float


def _to_daily_scores(queryset: Iterable[DailyAggregateScore]) -> List[DailyScore]:
    return [
        DailyScore(match_date=ds.match_date, stage_code=ds.stage.code, sda_percent=ds.sda_percent)
        for ds in queryset
    ]


def recompute_daily(profile: ShooterProfile, division: Division, stage, match_date):
    attempts = ClassifierAttempt.objects.filter(
        profile=profile, division=division, stage=stage, match_date=match_date
    ).order_by("-created_at")
    if not attempts.exists():
        return None
    capped_percents = [a.capped_percent for a in attempts]
    sda_percent = engine.compute_sda(capped_percents)
    daily, _ = DailyAggregateScore.objects.update_or_create(
        profile=profile,
        division=division,
        stage=stage,
        match_date=match_date,
        defaults={
            "sda_percent": sda_percent,
            "attempt_count": attempts.count(),
        },
    )
    return daily


def recompute_mro(profile: ShooterProfile, division: Division, stage):
    daily_scores = DailyAggregateScore.objects.filter(
        profile=profile, division=division, stage=stage
    ).order_by("-match_date")
    most_recent_date = daily_scores.first().match_date if daily_scores else None
    for ds in daily_scores:
        should_flag = most_recent_date and ds.match_date == most_recent_date
        if ds.is_mro != should_flag:
            ds.is_mro = should_flag
            ds.save(update_fields=["is_mro", "updated_at"])


def recompute_division_summary(profile: ShooterProfile, division: Division):
    daily_scores = DailyAggregateScore.objects.filter(profile=profile, division=division).order_by("-match_date")
    engine_input = [{"date": ds.match_date, "stage_code": ds.stage.code, "sda_percent": ds.sda_percent} for ds in daily_scores]
    mro_applied = engine.apply_mro(engine_input)
    summary = engine.compute_division_classification(mro_applied)
    DivisionSummary.objects.update_or_create(
        profile=profile,
        division=division,
        defaults={
            "current_percent": summary["current_percent"],
            "implied_class": summary["implied_class"],
            "highest_badge": summary["highest_badge"],
            "active_scores": summary["active_scores"],
        },
    )
    return summary


def on_attempt_created(profile: ShooterProfile, division: Division, stage, match_date):
    with transaction.atomic():
        recompute_daily(profile, division, stage, match_date)
        recompute_mro(profile, division, stage)
        return recompute_division_summary(profile, division)
