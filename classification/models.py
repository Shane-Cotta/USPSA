from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from . import classification_engine as engine

User = get_user_model()


class ShooterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    uspsa_number = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128, blank=True)
    club = models.CharField(max_length=128, blank=True)

    def __str__(self) -> str:
        return self.name or self.uspsa_number


class Division(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ClassifierStage(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class HHF(models.Model):
    stage = models.ForeignKey(ClassifierStage, on_delete=models.CASCADE, related_name="hhfs")
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="hhfs")
    hhf = models.DecimalField(max_digits=10, decimal_places=4)
    effective_date = models.DateField()
    source = models.TextField(blank=True)

    class Meta:
        unique_together = ("stage", "division", "effective_date")
        ordering = ["-effective_date"]

    def __str__(self) -> str:
        return f"{self.stage.code} {self.division.slug} {self.effective_date}"

    @classmethod
    def lookup(cls, stage: ClassifierStage, division: Division, match_date) -> Optional["HHF"]:
        return (
            cls.objects.filter(stage=stage, division=division, effective_date__lte=match_date)
            .order_by("-effective_date")
            .first()
        )


class ClassifierAttempt(models.Model):
    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        CSV = "CSV", "CSV"
        PRACTISCORE = "PRACTISCORE", "PractiScore"

    profile = models.ForeignKey(ShooterProfile, on_delete=models.CASCADE, related_name="attempts")
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="attempts")
    stage = models.ForeignKey(ClassifierStage, on_delete=models.CASCADE, related_name="attempts")
    match_date = models.DateField()
    hit_factor = models.DecimalField(max_digits=10, decimal_places=4)
    raw_percent = models.DecimalField(max_digits=7, decimal_places=4, editable=False, blank=True, default=Decimal("0"))
    capped_percent = models.DecimalField(max_digits=7, decimal_places=4, editable=False, blank=True, default=Decimal("0"))
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-match_date", "-created_at"]

    def clean(self):
        if self.pk:
            raise ValidationError("ClassifierAttempt is immutable")

        hhf_entry = HHF.lookup(self.stage, self.division, self.match_date)
        if not hhf_entry:
            raise ValidationError("HHF not found for stage/division at given date")
        raw = engine.compute_percent(self.hit_factor, hhf_entry.hhf)
        self.raw_percent = raw
        self.capped_percent = engine.cap_percent(raw)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profile} {self.stage.code} {self.match_date}"


class DailyAggregateScore(models.Model):
    profile = models.ForeignKey(ShooterProfile, on_delete=models.CASCADE, related_name="daily_scores")
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="daily_scores")
    stage = models.ForeignKey(ClassifierStage, on_delete=models.CASCADE, related_name="daily_scores")
    match_date = models.DateField()
    sda_percent = models.DecimalField(max_digits=7, decimal_places=4)
    attempt_count = models.PositiveIntegerField(default=0)
    is_mro = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("profile", "division", "stage", "match_date")
        ordering = ["-match_date"]

    def __str__(self):
        return f"{self.profile} {self.stage.code} {self.match_date}"


class DivisionSummary(models.Model):
    profile = models.ForeignKey(ShooterProfile, on_delete=models.CASCADE, related_name="division_summaries")
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="summaries")
    current_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal("0"))
    implied_class = models.CharField(max_length=8, default="Unclassified")
    highest_badge = models.CharField(max_length=8, default="Unclassified")
    active_scores = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("profile", "division")

    def __str__(self):
        return f"{self.profile} {self.division.slug}"
