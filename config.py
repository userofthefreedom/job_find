from __future__ import annotations

# 검색 키워드 — 공고 제목 또는 직무 키워드에 하나라도 포함되면 통과 (대소문자 무시)
# 빈 리스트 [] → 전체 허용
KEYWORDS: list[str] = ["Python", "백엔드"]

# 근무 지역 — location 필드에 하나라도 포함되면 통과
# 빈 리스트 [] → 전체 허용
LOCATIONS: list[str] = ["서울", "판교"]

# 경력 유형 — "신입" | "경력" | "신입·경력" | None (전체 허용)
CAREER_TYPE: str | None = None

# 경력 연차 범위 — None 이면 해당 방향 제한 없음
EXP_MIN: int | None = 1
EXP_MAX: int | None = 5
