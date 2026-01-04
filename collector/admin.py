from django.contrib import admin

from .management.commands.run_collectors import approve_collected_score
from .models import ClubManagerAssignment, ClubSource, CollectedScore, CollectorRun, MatchSource


@admin.register(ClubSource)
class ClubSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "parsing_mode", "max_requests_per_hour")
    list_filter = ("enabled", "parsing_mode")
    search_fields = ("name",)


@admin.register(MatchSource)
class MatchSourceAdmin(admin.ModelAdmin):
    list_display = ("club_source", "practiscore_match_url", "enabled", "last_status", "last_fetched_at")
    list_filter = ("enabled", "last_status")
    search_fields = ("practiscore_match_url",)


@admin.register(CollectedScore)
class CollectedScoreAdmin(admin.ModelAdmin):
    list_display = ("competitor_name", "division", "classifier_code", "match_date", "import_status")
    list_filter = ("division", "import_status")
    search_fields = ("competitor_name", "classifier_code")
    actions = ["approve_selected"]

    def approve_selected(self, request, queryset):
        for score in queryset:
            approve_collected_score(score)
        self.message_user(request, "Processed selected scores")


@admin.register(ClubManagerAssignment)
class ClubManagerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "club_source")
    list_filter = ("club_source",)


@admin.register(CollectorRun)
class CollectorRunAdmin(admin.ModelAdmin):
    list_display = ("started_at", "finished_at", "status", "matches_checked", "scores_found", "errors")
