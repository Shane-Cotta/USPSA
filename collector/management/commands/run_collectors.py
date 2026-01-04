from __future__ import annotations

import time
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from classification.models import ClassifierAttempt, ClassifierStage, Division, ShooterProfile
from classification.services import on_attempt_created
from collector.parsers import AutoParser, HTMLV1Parser, HTMLV2Parser
from collector.models import ClubSource, CollectedScore, CollectorRun, MatchSource


class Command(BaseCommand):
    help = "Run PractiScore collectors"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--club", type=int)
        parser.add_argument("--match", type=int)

    def handle(self, *args, **options):
        run = CollectorRun.objects.create(status="RUNNING")
        try:
            matches = self._select_matches(options)
            self._process_matches(run, matches)
            run.status = "FINISHED"
        finally:
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "finished_at"])

    def _select_matches(self, options):
        qs = MatchSource.objects.filter(enabled=True, club_source__enabled=True)
        if options.get("club"):
            qs = qs.filter(club_source_id=options["club"])
        if options.get("match"):
            qs = qs.filter(id=options["match"])
        return qs.select_related("club_source")

    def _process_matches(self, run: CollectorRun, matches):
        for match in matches:
            run.matches_checked += 1
            run.save(update_fields=["matches_checked"])
            if not self._domain_allowed(match):
                match.last_status = "FAILED"
                match.last_error = "Domain not allowed"
                match.save(update_fields=["last_status", "last_error"])
                run.errors += 1
                continue
            if self._rate_limited(match):
                run.append_log(f"Rate limited {match}")
                continue
            response = self._fetch(match)
            if response is None:
                continue
            if response.status_code == 304:
                match.last_status = "NO_CHANGE"
                match.last_fetched_at = timezone.now()
                match.save(update_fields=["last_status", "last_fetched_at"])
                continue
            if response.status_code == 403:
                match.last_status = "ACCESS_DENIED"
                match.last_error = "Access denied"
                match.last_fetched_at = timezone.now()
                match.save(update_fields=["last_status", "last_error", "last_fetched_at"])
                run.errors += 1
                continue
            if response.status_code != 200:
                match.last_status = "FAILED"
                match.last_error = f"HTTP {response.status_code}"
                match.last_fetched_at = timezone.now()
                match.save(update_fields=["last_status", "last_error", "last_fetched_at"])
                run.errors += 1
                continue
            self._parse_and_store(run, match, response)
            time.sleep(max(1, int(3600 / match.club_source.max_requests_per_hour)))

    def _domain_allowed(self, match: MatchSource) -> bool:
        allowed = match.club_source.allowed_domains.split(",")
        domain = urlparse(match.practiscore_match_url).hostname or ""
        return any(a.strip() in domain for a in allowed)

    def _rate_limited(self, match: MatchSource) -> bool:
        if not match.last_fetched_at:
            return False
        interval = 3600 / max(1, match.club_source.max_requests_per_hour)
        return (timezone.now() - match.last_fetched_at) < timedelta(seconds=interval)

    def _fetch(self, match: MatchSource):
        headers = {"User-Agent": match.club_source.user_agent}
        if match.etag:
            headers["If-None-Match"] = match.etag
        if match.last_modified:
            headers["If-Modified-Since"] = match.last_modified
        try:
            response = requests.get(match.practiscore_match_url, headers=headers, timeout=10)
        except requests.RequestException as exc:
            match.last_status = "FAILED"
            match.last_error = str(exc)
            match.save(update_fields=["last_status", "last_error"])
            return None
        match.last_fetched_at = timezone.now()
        match.etag = response.headers.get("ETag", match.etag)
        match.last_modified = response.headers.get("Last-Modified", match.last_modified)
        match.save(update_fields=["last_fetched_at", "etag", "last_modified"])
        return response

    def _parser_for(self, match: MatchSource):
        mode = match.club_source.parsing_mode
        if mode == "HTML_V1":
            return HTMLV1Parser()
        if mode == "HTML_V2":
            return HTMLV2Parser()
        return AutoParser()

    def _parse_and_store(self, run: CollectorRun, match: MatchSource, response):
        parser = self._parser_for(match)
        scores = parser.parse(response.text)
        if scores is None:
            match.last_status = "PARSE_ERROR"
            match.last_error = "No scores parsed"
            match.save(update_fields=["last_status", "last_error"])
            run.errors += 1
            return
        for result in scores:
            CollectedScore.objects.create(
                match_source=match,
                competitor_name=result["competitor_name"],
                competitor_uspsa_number=result.get("competitor_uspsa_number"),
                division=result["division"],
                classifier_code=result["classifier_code"],
                match_date=result["match_date"],
                hit_factor=result.get("hit_factor"),
                raw_excerpt=response.text[:500],
            )
            run.scores_found += 1
        match.last_status = "OK"
        match.save(update_fields=["last_status"])
        run.save(update_fields=["scores_found"])


def approve_collected_score(collected: CollectedScore):
    try:
        division = Division.objects.get(slug=collected.division)
        stage = ClassifierStage.objects.get(code=collected.classifier_code)
    except (Division.DoesNotExist, ClassifierStage.DoesNotExist):
        collected.import_status = "REJECTED"
        collected.save(update_fields=["import_status"])
        return None
    profile = None
    if collected.competitor_uspsa_number:
        profile = ShooterProfile.objects.filter(uspsa_number=collected.competitor_uspsa_number).first()
    if not profile:
        collected.import_status = "REJECTED"
        collected.save(update_fields=["import_status"])
        return None
    attempt = ClassifierAttempt.objects.create(
        profile=profile,
        division=division,
        stage=stage,
        match_date=collected.match_date,
        hit_factor=collected.hit_factor or 0,
        source=ClassifierAttempt.Source.PRACTISCORE,
    )
    collected.import_status = "IMPORTED"
    collected.save(update_fields=["import_status"])
    on_attempt_created(profile, division, stage, collected.match_date)
    return attempt
