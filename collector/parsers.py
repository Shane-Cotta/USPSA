from __future__ import annotations

import re
from datetime import datetime
from typing import List


class BaseParser:
    name = "base"

    def parse(self, html: str) -> List[dict]:
        raise NotImplementedError


class HTMLV1Parser(BaseParser):
    name = "HTML_V1"
    ROW_RE = re.compile(
        r'data-classifier="(?P<classifier>[^"]+)"[^>]*data-division="(?P<division>[^"]+)"[^>]*data-hitfactor="(?P<hitfactor>[^"]+)"[^>]*data-date="(?P<date>[^"]+)"[^>]*data-competitor="(?P<competitor>[^"]+)"'
    )

    def parse(self, html: str) -> List[dict]:
        results = []
        for match in self.ROW_RE.finditer(html):
            results.append(
                {
                    "classifier_code": match.group("classifier"),
                    "division": match.group("division"),
                    "hit_factor": match.group("hitfactor"),
                    "match_date": datetime.strptime(match.group("date"), "%Y-%m-%d").date(),
                    "competitor_name": match.group("competitor"),
                    "competitor_uspsa_number": None,
                    "parser": self.name,
                }
            )
        return results


class HTMLV2Parser(BaseParser):
    name = "HTML_V2"
    ROW_RE = re.compile(
        r"classifier:(?P<classifier>\S+)\s+division:(?P<division>\S+)\s+hf:(?P<hitfactor>\S+)\s+date:(?P<date>\S+)\s+name:(?P<competitor>[^\n]+)"
    )

    def parse(self, html: str) -> List[dict]:
        results = []
        for match in self.ROW_RE.finditer(html):
            results.append(
                {
                    "classifier_code": match.group("classifier"),
                    "division": match.group("division"),
                    "hit_factor": match.group("hitfactor"),
                    "match_date": datetime.strptime(match.group("date"), "%Y-%m-%d").date(),
                    "competitor_name": match.group("competitor").strip(),
                    "competitor_uspsa_number": None,
                    "parser": self.name,
                }
            )
        return results


class AutoParser(BaseParser):
    name = "AUTO"

    def __init__(self):
        self.parsers = [HTMLV1Parser(), HTMLV2Parser()]
        self.last_parser_used = None

    def parse(self, html: str) -> List[dict]:
        for parser in self.parsers:
            results = parser.parse(html)
            if results:
                self.last_parser_used = parser.name
                return results
        return []
