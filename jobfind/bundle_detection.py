from __future__ import annotations
import re

"""복수 직무를 한 번에 모집하는 공채성 공고 후보를 감지한다 (Phase 19).

자동으로 개별 직무로 분리하지는 않는다 — 제목 신호로 후보만 표시하고, 실제 지원
직무를 좁히는 건 기존 notes.md 채널(Phase 18)을 재사용해 사용자가 직접 안내한다.

제목 신호만 쓴다 — 직무 태그 개수(예: 4개 이상)로도 판별해봤지만, 실제 수집 데이터로
검증한 결과 사람인이 단일 직무 공고에도 유사 태그를 4~5개씩 붙이는 경우가 흔해
(예: 영업 공고에 "솔루션기술영업, 영업, 영업기획, 판매, IT·통신기기판매") 오탐이 태그
신호에서만 33%(9건 중 3건)에 달했다. 태그 신호를 제거하고 제목 패턴만 남긴다.
"""

_TITLE_PATTERNS = [
    r"공[개]?채용", r"공채",
    r"각\s*부문", r"부문별", r"직군별", r"직무별", r"분야별",
    r"전\s*부문", r"전\s*직무", r"통합\s*채용",
    r"\d+개\s*(부문|직무|직군|분야)",
]
_TITLE_RE = re.compile("|".join(_TITLE_PATTERNS))


def is_bundled_posting(job: dict) -> bool:
    return bool(_TITLE_RE.search(job.get("title", "")))
