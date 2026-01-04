from django.urls import path

from .views import ProfileUpdateView, SignupView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
]
