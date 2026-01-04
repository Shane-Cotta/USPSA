from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ClubSource(models.Model):
    PARSING_MODES = [
        ("AUTO", "Auto"),
        ("HTML_V1", "HTML v1"),
        ("HTML_V2", "HTML v2"),
    ]

    name = models.CharField(max_length=128)
    practiscore_club_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    fetch_frequency_minutes = models.PositiveIntegerField(default=60)
    user_agent = models.CharField(max_length=256, default="ClassifierTrackerBot/1.0")
    max_requests_per_hour = models.PositiveIntegerField(default=30)
    allowed_domains = models.CharField(max_length=256, default="practiscore.com")
    parsing_mode = models.CharField(max_length=16, choices=PARSING_MODES, default="AUTO")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        domains = [d.strip() for d in self.allowed_domains.split(",") if d.strip()]
        if not domains:
            raise ValidationError("allowed_domains must include at least one domain")
        self.allowed_domains = ",".join(domains)


class ClubManagerAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club_source = models.ForeignKey(ClubSource, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "club_source")

    def __str__(self):
        return f"{self.user} -> {self.club_source}"


class MatchSource(models.Model):
    STATUS = [
        ("OK", "OK"),
        ("NO_CHANGE", "No change"),
        ("FAILED", "Failed"),
        ("ACCESS_DENIED", "Access denied"),
        ("PARSE_ERROR", "Parse error"),
    ]

    club_source = models.ForeignKey(ClubSource, on_delete=models.CASCADE, related_name="matches")
    practiscore_match_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=32, choices=STATUS, default="OK")
    last_error = models.TextField(blank=True)
    etag = models.CharField(max_length=128, blank=True)
    last_modified = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.practiscore_match_url or f"Match {self.pk}"


class CollectedScore(models.Model):
    IMPORT_STATUS = [
        ("NEW", "New"),
        ("DUPLICATE", "Duplicate"),
        ("IMPORTED", "Imported"),
        ("REJECTED", "Rejected"),
    ]

    match_source = models.ForeignKey(MatchSource, on_delete=models.CASCADE, related_name="scores")
    competitor_name = models.TextField()
    competitor_uspsa_number = models.TextField(blank=True, null=True)
    division = models.CharField(max_length=32)
    classifier_code = models.CharField(max_length=16)
    match_date = models.DateField()
    hit_factor = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    raw_excerpt = models.TextField(blank=True)
    mapped_profile = models.ForeignKey("classification.ShooterProfile", on_delete=models.SET_NULL, null=True, blank=True)
    import_status = models.CharField(max_length=16, choices=IMPORT_STATUS, default="NEW")

    def __str__(self):
        return f"{self.competitor_name} {self.classifier_code}"


class CollectorRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    matches_checked = models.IntegerField(default=0)
    scores_found = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default="PENDING")
    log = models.TextField(blank=True)

    def append_log(self, text: str):
        self.log = (self.log or "") + text + "\n"
        self.save(update_fields=["log"])

    def __str__(self):
        return f"Run {self.started_at}"
