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


def fetch_all() -> tuple[list[dict], bool, bool, bool]:
    """반환: (jobs, saramin_failed, wanted_failed, saramin_page_cap_hit) — Phase 5 실행
    로그·이상 감지에서 쓰는 소스별 실패/상한 신호를 그대로 전달한다."""
    saramin_jobs, saramin_failed, page_cap_hit = fetch_saramin_all()
    wanted_jobs, wanted_failed = fetch_wanted_all()
    jobs = deduplicate_cross_platform(saramin_jobs, wanted_jobs)
    return jobs, saramin_failed, wanted_failed, page_cap_hit
