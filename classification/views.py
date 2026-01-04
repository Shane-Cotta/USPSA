from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, TemplateView

from .forms import AttemptForm, CSVImportForm
from .models import ClassifierAttempt, ClassifierStage, Division, DivisionSummary
from .services import on_attempt_created


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "classification/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        ctx["summaries"] = DivisionSummary.objects.filter(profile=profile).select_related("division")
        ctx["recent_attempts"] = (
            ClassifierAttempt.objects.filter(profile=profile)
            .select_related("stage", "division")
            .order_by("-match_date")[:10]
        )
        return ctx


class AttemptCreateView(LoginRequiredMixin, FormView):
    form_class = AttemptForm
    template_name = "classification/attempt_form.html"
    success_url = reverse_lazy("dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["profile"] = self.request.user.profile
        return kwargs

    def form_valid(self, form):
        attempt = form.save()
        on_attempt_created(
            profile=attempt.profile,
            division=attempt.division,
            stage=attempt.stage,
            match_date=attempt.match_date,
        )
        messages.success(self.request, "Attempt recorded")
        return super().form_valid(form)


class AttemptHistoryView(LoginRequiredMixin, ListView):
    model = ClassifierAttempt
    template_name = "classification/attempt_history.html"
    paginate_by = 50

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(profile=self.request.user.profile)
            .select_related("stage", "division")
            .order_by("-match_date")
        )


class CSVImportView(LoginRequiredMixin, FormView):
    form_class = CSVImportForm
    template_name = "classification/csv_import.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        profile = self.request.user.profile
        created = 0
        available_slugs = list(Division.objects.values_list("slug", flat=True))
        for row in form.parse_rows():
            try:
                division = Division.objects.get(slug=row["division"])
            except Division.DoesNotExist:
                messages.error(
                    self.request,
                    f"Unknown division slug '{row.get('division')}'. Available: {', '.join(available_slugs)}.",
                )
                continue
            try:
                match_date = datetime.strptime(row["match_date"], "%Y-%m-%d").date()
                stage_code = row["classifier_code"]
                hit_factor = row["hit_factor"]
            except (KeyError, ValueError):
                messages.error(
                    self.request,
                    "Invalid row format. Expect columns: match_date (YYYY-MM-DD), division, classifier_code, hit_factor.",
                )
                continue
            try:
                stage = ClassifierStage.objects.get(code=stage_code)
            except ClassifierStage.DoesNotExist:
                messages.error(self.request, f"Unknown classifier code '{stage_code}'. Ensure it matches a stage like 19-01.")
                continue
            if ClassifierAttempt.objects.filter(
                profile=profile, division=division, stage=stage, match_date=match_date, hit_factor=hit_factor
            ).exists():
                continue
            attempt = ClassifierAttempt.objects.create(
                profile=profile,
                division=division,
                stage=stage,
                match_date=match_date,
                hit_factor=hit_factor,
                source=ClassifierAttempt.Source.CSV,
            )
            on_attempt_created(profile, division, stage, match_date)
            created += 1
        messages.success(self.request, f"Imported {created} attempts")
        return super().form_valid(form)
