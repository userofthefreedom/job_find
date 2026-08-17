from __future__ import annotations
import re

from jobfind.config import config

# "신입·경력"은 신입/경력 구분 없이 지원 가능하다는 뜻이므로, 신입 전용·경력무관·
# 특정 연차 범위(예: "경력 3~8년")로 표기된 공고도 실질적으로 동일한 조건이다.
_CAREER_EQUIVALENTS = {
    "신입": ["신입", "경력무관"],
    "경력": ["경력", "경력무관"],
    "신입·경력": ["신입", "경력", "경력무관"],
}


def filter_keywords(job: dict) -> bool:
    if not config.KEYWORDS:
        return True
    keywords_lower = [kw.lower() for kw in config.KEYWORDS]
    title = job["title"].lower()
    if any(kw in title for kw in keywords_lower):
        return True  # 제목에서 매칭되면 확실한 채용 공고로 보고 바로 통과
    # 직무 태그는 부분 문자열이 아닌 태그 단위 완전 일치만 인정한다.
    # ("영업기획", "기획MD"처럼 다른 직무의 태그에 우연히 포함되는 것을 방지)
    tags = [t.strip().lower() for t in job["keyword"].split(",") if t.strip()]
    if not any(tag in keywords_lower for tag in tags):
        return False
    # 태그로만 매칭된 경우: 무료교육·설명회 등 노이즈 공고인지 추가 검사
    exclude_text = f"{job['title']} {job['job_type']}".lower()
    return not any(kw.lower() in exclude_text for kw in config.EXCLUDE_KEYWORDS)


_NO_LOCATION_EXPERIENCE_SOURCE = "자소설닷컴"


def filter_location(job: dict) -> bool:
    # 자소설닷컴은 근무지 필드를 아예 제공하지 않는다(사람인/원티드에서 빈 값이 나오는
    # 이례적 상황과 다름 — 소스 자체의 알려진 한계). 소스 단위로 이 필터만 건너뛴다.
    if not config.LOCATIONS or job["source"] == _NO_LOCATION_EXPERIENCE_SOURCE:
        return True
    return any(loc in job["location"] for loc in config.LOCATIONS)


def filter_career_type(job: dict) -> bool:
    if not config.CAREER_TYPE or job["source"] == _NO_LOCATION_EXPERIENCE_SOURCE:
        return True
    return any(
        e in job["experience"]
        for career_type in config.CAREER_TYPE
        for e in _CAREER_EQUIVALENTS.get(career_type, [career_type])
    )


def filter_company_blacklist(job: dict) -> bool:
    if not config.EXCLUDE_COMPANIES:
        return True
    return not any(name in job["company"] for name in config.EXCLUDE_COMPANIES)


def filter_exp_range(job: dict) -> bool:
    if config.EXP_MIN is None and config.EXP_MAX is None:
        return True
    nums = [int(n) for n in re.findall(r"\d+", job["experience"])]
    if not nums:
        return True  # 추출 불가(경력무관 등) → 관대하게 통과
    lo = config.EXP_MIN if config.EXP_MIN is not None else 0
    hi = config.EXP_MAX if config.EXP_MAX is not None else 99
    return min(nums) <= hi and max(nums) >= lo


def filter_jobs(jobs: list[dict]) -> list[dict]:
    return [
        j for j in jobs
        if filter_keywords(j) and filter_location(j)
        and filter_career_type(j) and filter_exp_range(j)
        and filter_company_blacklist(j)
    ]
