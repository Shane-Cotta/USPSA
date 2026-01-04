from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class CollectorInfoView(LoginRequiredMixin, TemplateView):
    template_name = "collector/info.html"
