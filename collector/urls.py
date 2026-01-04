from django.urls import path

from .views import CollectorInfoView

urlpatterns = [
    path("", CollectorInfoView.as_view(), name="collector-info"),
]
