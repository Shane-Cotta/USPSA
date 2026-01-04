from django.urls import path

from .views import AttemptCreateView, AttemptHistoryView, CSVImportView

urlpatterns = [
    path("enter/", AttemptCreateView.as_view(), name="attempt-create"),
    path("history/", AttemptHistoryView.as_view(), name="attempt-history"),
    path("csv-import/", CSVImportView.as_view(), name="csv-import"),
]
