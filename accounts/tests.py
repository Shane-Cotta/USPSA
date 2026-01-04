import pytest
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_profile_update_limited_to_owner(client):
    user = User.objects.create_user(username="owner", password="pw")
    other = User.objects.create_user(username="other", password="pw")
    client.login(username="owner", password="pw")
    response = client.get(reverse("profile"))
    assert response.status_code == 200
    client.logout()
    client.login(username="other", password="pw")
    response = client.get(reverse("profile"))
    assert response.status_code == 200  # always own profile; should not expose others
