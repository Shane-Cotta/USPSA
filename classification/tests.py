from decimal import Decimal
from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from classification import classification_engine as engine
from classification.models import (
    ClassifierAttempt,
    ClassifierStage,
    DailyAggregateScore,
    Division,
    HHF,
    ShooterProfile,
)
from classification.services import on_attempt_created


@pytest.mark.django_db
def test_smoke_migrations():
    assert User.objects.count() == 0


@pytest.fixture
def profile(db):
    user = User.objects.create_user(username="u1", password="pw")
    profile, _ = ShooterProfile.objects.get_or_create(user=user, defaults={"uspsa_number": "A1234"})
    profile.uspsa_number = "A1234"
    profile.save()
    return profile


@pytest.fixture
def division(db):
    return Division.objects.create(name="Carry Optics", slug="CO")


@pytest.fixture
def stage(db):
    return ClassifierStage.objects.create(code="19-01", name="Test Stage")


@pytest.fixture
def hhf(stage, division):
    return HHF.objects.create(stage=stage, division=division, hhf=Decimal("5.0000"), effective_date=date(2020, 1, 1))


@pytest.mark.django_db
def test_attempt_immutable(profile, division, stage, hhf):
    attempt = ClassifierAttempt.objects.create(
        profile=profile,
        division=division,
        stage=stage,
        match_date=date(2024, 1, 1),
        hit_factor=Decimal("5.0000"),
        source=ClassifierAttempt.Source.MANUAL,
    )
    with pytest.raises(ValidationError):
        attempt.hit_factor = Decimal("6.0")
        attempt.save()


def test_engine_precision_and_caps():
    pct = engine.compute_percent(Decimal("5.0000"), Decimal("5.0000"))
    assert pct == Decimal("100.0000")
    assert engine.cap_percent(Decimal("109.9999")) == Decimal("109.9999")
    assert engine.cap_percent(Decimal("110.0001")) == Decimal("110.0000")
    assert engine.compute_sda([Decimal("100.001"), Decimal("100.001")]) == Decimal("100.0010")


def test_engine_class_mapping_boundaries():
    assert engine.class_from_percent(Decimal("94.999")) == "M"
    assert engine.class_from_percent(Decimal("95.0")) == "GM"
    assert engine.class_from_percent(Decimal("85.0")) == "M"
    assert engine.class_from_percent(Decimal("84.999")) == "A"


def test_engine_windowing_and_best6():
    base_date = date(2024, 1, 1)
    scores = []
    for i in range(1, 10):
        scores.append({"date": base_date + timedelta(days=i), "stage_code": f"{i}", "sda_percent": Decimal(i)})
    mro = engine.apply_mro(scores)
    window = engine.compute_active_window(mro)
    assert len(window) == 8
    summary = engine.compute_division_classification(window)
    assert summary["active_scores"] == 8
    assert summary["is_classified"] is True


@pytest.mark.django_db
def test_services_recompute(profile, division, stage, hhf):
    attempt1 = ClassifierAttempt.objects.create(
        profile=profile,
        division=division,
        stage=stage,
        match_date=date(2024, 1, 1),
        hit_factor=Decimal("5.0000"),
    )
    on_attempt_created(profile, division, stage, attempt1.match_date)
    attempt2 = ClassifierAttempt.objects.create(
        profile=profile,
        division=division,
        stage=stage,
        match_date=date(2024, 1, 2),
        hit_factor=Decimal("6.0000"),
    )
    summary = on_attempt_created(profile, division, stage, attempt2.match_date)
    daily = DailyAggregateScore.objects.filter(profile=profile, division=division, stage=stage)
    assert daily.count() == 2
    assert summary["implied_class"] in {"GM", "M", "A", "B", "C", "D", "Unclassified"}

# Create your tests here.
