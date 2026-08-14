from __future__ import annotations
import re
from difflib import SequenceMatcher

from jobfind.collectors.saramin import fetch_saramin_all
from jobfind.collectors.wanted import fetch_wanted_all


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", "", title).lower()


def deduplicate_cross_platform(saramin: list[dict], wanted: list[dict]) -> list[dict]:
    result = list(saramin)
    for w in wanted:
        is_dup = any(
            SequenceMatcher(None, _norm_title(s["title"]), _norm_title(w["title"])).ratio() >= 0.85
            and (s["deadline"] == w["deadline"] or s["location"] == w["location"])
            for s in saramin
        )
        if not is_dup:
            result.append(w)
    return result


def fetch_all() -> list[dict]:
    return deduplicate_cross_platform(fetch_saramin_all(), fetch_wanted_all())
