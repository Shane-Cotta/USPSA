from django.contrib import admin

from .models import (
    ClassifierAttempt,
    ClassifierStage,
    DailyAggregateScore,
    Division,
    DivisionSummary,
    HHF,
    ShooterProfile,
)


@admin.register(ShooterProfile)
class ShooterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "uspsa_number", "name", "club")
    search_fields = ("uspsa_number", "name", "user__username")


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(ClassifierStage)
class ClassifierStageAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")
    search_fields = ("code", "name")
    list_filter = ("active",)


@admin.register(HHF)
class HHFAdmin(admin.ModelAdmin):
    list_display = ("stage", "division", "hhf", "effective_date")
    list_filter = ("division", "stage")
    search_fields = ("stage__code",)


@admin.register(ClassifierAttempt)
class ClassifierAttemptAdmin(admin.ModelAdmin):
    list_display = ("profile", "division", "stage", "match_date", "hit_factor", "capped_percent", "source")
    list_filter = ("division", "source")
    search_fields = ("profile__uspsa_number", "stage__code")
    readonly_fields = ("raw_percent", "capped_percent", "created_at")


@admin.register(DailyAggregateScore)
class DailyAggregateScoreAdmin(admin.ModelAdmin):
    list_display = ("profile", "division", "stage", "match_date", "sda_percent", "attempt_count", "is_mro")
    list_filter = ("division", "is_mro")
    search_fields = ("profile__uspsa_number", "stage__code")
    readonly_fields = ("updated_at",)


@admin.register(DivisionSummary)
class DivisionSummaryAdmin(admin.ModelAdmin):
    list_display = ("profile", "division", "current_percent", "implied_class", "highest_badge", "active_scores")
    list_filter = ("division",)
    search_fields = ("profile__uspsa_number",)
