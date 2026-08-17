from __future__ import annotations
import re
from difflib import SequenceMatcher

from jobfind.collectors.jasoseol import fetch_jasoseol_all
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


def fetch_all(skip_ids: set[str]) -> tuple[list[dict], bool, bool, bool, bool]:
    """반환: (jobs, saramin_failed, wanted_failed, saramin_page_cap_hit, jasoseol_failed) —
    Phase 5 실행 로그·이상 감지에서 쓰는 소스별 실패/상한 신호를 그대로 전달한다.

    자소설닷컴(Phase 23)은 사람인/원티드와 교차 중복제거를 하지 않는다 — 목록 제목이
    "2026년 8월 신입/경력 채용"처럼 회사 단위 포괄적 제목이라 특정 직무 제목과 유사도
    매칭이 안 되고, 애초에 서로 다른 지원 채널(사람인/원티드 지원 vs 자소설닷컴 자소서
    작성)이라 중복이 아니다. skip_ids는 신규 회사만 상세조회하기 위해 넘긴다(§dedup)."""
    saramin_jobs, saramin_failed, page_cap_hit = fetch_saramin_all()
    wanted_jobs, wanted_failed = fetch_wanted_all()
    jasoseol_jobs, jasoseol_failed = fetch_jasoseol_all(skip_ids)
    jobs = deduplicate_cross_platform(saramin_jobs, wanted_jobs) + jasoseol_jobs
    return jobs, saramin_failed, wanted_failed, page_cap_hit, jasoseol_failed
