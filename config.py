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

# 제외 키워드 — KEYWORDS가 title(제목)이 아닌 keyword(직무 태그)에만 걸린 경우에 한해 검사.
# title 또는 job_type에 아래 단어가 포함되면 채용 공고가 아닌 것으로 간주해 탈락시킨다.
# (예: 무료교육 모집, 설명회, 포괄적 상시채용 공고 등 태그만으로 우연히 매칭되는 노이즈 제거)
EXCLUDE_KEYWORDS: list[str] = ["교육생", "무료교육", "설명회", "상시채용"]
