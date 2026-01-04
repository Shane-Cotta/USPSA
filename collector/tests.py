from datetime import timedelta, date

import pytest
from django.utils import timezone

from collector.management.commands.run_collectors import Command
from collector.models import ClubSource, CollectedScore, MatchSource
from collector.parsers import HTMLV1Parser


def test_parser_html_v1():
    html = '<tr data-classifier="19-01" data-division="CO" data-hitfactor="5.12" data-date="2024-01-01" data-competitor="Test Shooter"></tr>'
    parser = HTMLV1Parser()
    results = parser.parse(html)
    assert len(results) == 1
    assert results[0]["classifier_code"] == "19-01"


@pytest.mark.django_db
def test_rate_limit_logic():
    club = ClubSource.objects.create(name="Club", practiscore_club_url="https://practiscore.com/club")
    match = MatchSource.objects.create(
        club_source=club,
        practiscore_match_url="https://practiscore.com/match",
        last_fetched_at=timezone.now(),
    )
    cmd = Command()
    assert cmd._rate_limited(match) is True


@pytest.mark.django_db
def test_domain_restriction():
    club = ClubSource.objects.create(
        name="Club", practiscore_club_url="https://practiscore.com/club", allowed_domains="practiscore.com"
    )
    match = MatchSource.objects.create(club_source=club, practiscore_match_url="https://evil.com/match")
    cmd = Command()
    assert cmd._domain_allowed(match) is False

# Create your tests here.
