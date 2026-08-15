from __future__ import annotations

from jobfind.config import config
from jobfind.filters import (
    filter_career_type,
    filter_company_blacklist,
    filter_exp_range,
    filter_jobs,
    filter_keywords,
    filter_location,
)


def _job_stub(**kwargs):
    base = {"title": "", "keyword": "", "location": "", "experience": "", "job_type": "", "company": ""}
    return {**base, **kwargs}


# ── filter_keywords ───────────────────────────────────────────────────────────

def test_filter_keywords_match_title(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["Python"])
    assert filter_keywords(_job_stub(title="Python 백엔드 개발자"))

def test_filter_keywords_match_keyword_field(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["Django"])
    assert filter_keywords(_job_stub(title="백엔드 개발자", keyword="Python, Django"))

def test_filter_keywords_no_match(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["Java"])
    assert not filter_keywords(_job_stub(title="Python 백엔드 개발자", keyword="Python"))

def test_filter_keywords_empty_allows_all(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", [])
    assert filter_keywords(_job_stub(title="아무거나"))

def test_filter_keywords_case_insensitive(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["python"])
    assert filter_keywords(_job_stub(title="Python 개발자"))

def test_filter_keywords_tag_compound_substring_not_matched(monkeypatch):
    # "영업기획", "기획MD"처럼 다른 직무 태그에 "기획"이 부분 문자열로 포함되어도
    # 태그 자체가 KEYWORDS와 완전히 일치하지 않으면 통과시키지 않는다.
    monkeypatch.setattr(config, "KEYWORDS", ["기획"])
    job = _job_stub(title="온라인MD 모집", keyword="영업관리, 기획MD, 리테일MD")
    assert not filter_keywords(job)

def test_filter_keywords_tag_exact_match_excluded_by_job_type(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["백엔드"])
    monkeypatch.setattr(config, "EXCLUDE_KEYWORDS", ["교육생"])
    job = _job_stub(title="AI 경력자 무료교육 모집", keyword="백엔드, 서버개발", job_type="교육생")
    assert not filter_keywords(job)

def test_filter_keywords_tag_exact_match_excluded_by_title(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["백엔드"])
    monkeypatch.setattr(config, "EXCLUDE_KEYWORDS", ["상시채용"])
    job = _job_stub(title="2026년 상반기 상시채용 모집", keyword="백엔드, 프론트엔드")
    assert not filter_keywords(job)

def test_filter_keywords_tag_only_match_passes_without_exclude_hit(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["Django"])
    monkeypatch.setattr(config, "EXCLUDE_KEYWORDS", ["교육생"])
    job = _job_stub(title="백엔드 개발자", keyword="Python, Django", job_type="정규직")
    assert filter_keywords(job)

def test_filter_keywords_title_match_bypasses_exclude(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["백엔드"])
    monkeypatch.setattr(config, "EXCLUDE_KEYWORDS", ["상시채용"])
    job = _job_stub(title="상시채용 백엔드 개발자 모집", keyword="")
    assert filter_keywords(job)


# ── filter_location ───────────────────────────────────────────────────────────

def test_filter_location_match(monkeypatch):
    monkeypatch.setattr(config, "LOCATIONS", ["서울"])
    assert filter_location(_job_stub(location="서울 강남구"))

def test_filter_location_no_match(monkeypatch):
    monkeypatch.setattr(config, "LOCATIONS", ["서울"])
    assert not filter_location(_job_stub(location="부산"))

def test_filter_location_empty_allows_all(monkeypatch):
    monkeypatch.setattr(config, "LOCATIONS", [])
    assert filter_location(_job_stub(location="제주"))


# ── filter_career_type ────────────────────────────────────────────────────────

def test_filter_career_type_empty_allows_all(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", [])
    assert filter_career_type(_job_stub(experience="신입"))

def test_filter_career_type_match(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", ["경력"])
    assert filter_career_type(_job_stub(experience="경력 3~5년"))

def test_filter_career_type_both_accepts_entry_only(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", ["신입·경력"])
    assert filter_career_type(_job_stub(experience="신입"))

def test_filter_career_type_both_accepts_career_unrestricted(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", ["신입·경력"])
    assert filter_career_type(_job_stub(experience="경력무관"))

def test_filter_career_type_both_accepts_specific_range(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", ["신입·경력"])
    assert filter_career_type(_job_stub(experience="경력 3~8년"))

def test_filter_career_type_both_rejects_blank(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", ["신입·경력"])
    assert not filter_career_type(_job_stub(experience=""))

def test_filter_career_type_no_match(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", ["경력"])
    assert not filter_career_type(_job_stub(experience="신입"))

def test_filter_career_type_multi_select_matches_either(monkeypatch):
    # Phase 6: "신입, 경력무관"처럼 여러 값을 선택하면 그중 하나라도 맞으면 통과
    monkeypatch.setattr(config, "CAREER_TYPE", ["신입", "경력무관"])
    assert filter_career_type(_job_stub(experience="경력무관"))
    assert filter_career_type(_job_stub(experience="신입"))
    assert not filter_career_type(_job_stub(experience="경력 5~10년"))


# ── filter_company_blacklist (Phase 6) ──────────────────────────────────────

def test_filter_company_blacklist_empty_allows_all(monkeypatch):
    monkeypatch.setattr(config, "EXCLUDE_COMPANIES", [])
    assert filter_company_blacklist(_job_stub(company="아무회사"))

def test_filter_company_blacklist_blocks_match(monkeypatch):
    monkeypatch.setattr(config, "EXCLUDE_COMPANIES", ["블랙기업"])
    assert not filter_company_blacklist(_job_stub(company="(주)블랙기업"))

def test_filter_company_blacklist_allows_non_match(monkeypatch):
    monkeypatch.setattr(config, "EXCLUDE_COMPANIES", ["블랙기업"])
    assert filter_company_blacklist(_job_stub(company="(주)좋은회사"))


# ── filter_exp_range ──────────────────────────────────────────────────────────

def test_filter_exp_range_both_none_allows_all(monkeypatch):
    monkeypatch.setattr(config, "EXP_MIN", None)
    monkeypatch.setattr(config, "EXP_MAX", None)
    assert filter_exp_range(_job_stub(experience="경력 10~20년"))

def test_filter_exp_range_no_numbers_passes(monkeypatch):
    monkeypatch.setattr(config, "EXP_MIN", 1)
    monkeypatch.setattr(config, "EXP_MAX", 5)
    assert filter_exp_range(_job_stub(experience="경력무관"))

def test_filter_exp_range_overlap(monkeypatch):
    monkeypatch.setattr(config, "EXP_MIN", 1)
    monkeypatch.setattr(config, "EXP_MAX", 5)
    assert filter_exp_range(_job_stub(experience="경력 3~10년"))

def test_filter_exp_range_no_overlap(monkeypatch):
    monkeypatch.setattr(config, "EXP_MIN", 1)
    monkeypatch.setattr(config, "EXP_MAX", 5)
    assert not filter_exp_range(_job_stub(experience="경력 7~10년"))

def test_filter_exp_range_single_number(monkeypatch):
    monkeypatch.setattr(config, "EXP_MIN", 1)
    monkeypatch.setattr(config, "EXP_MAX", 5)
    assert filter_exp_range(_job_stub(experience="신입~3년"))


# ── filter_jobs ───────────────────────────────────────────────────────────────

def test_filter_jobs_and_logic(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["Python"])
    monkeypatch.setattr(config, "LOCATIONS", ["서울"])
    monkeypatch.setattr(config, "CAREER_TYPE", [])
    monkeypatch.setattr(config, "EXP_MIN", None)
    monkeypatch.setattr(config, "EXP_MAX", None)
    monkeypatch.setattr(config, "EXCLUDE_COMPANIES", [])
    jobs = [
        _job_stub(title="Python 백엔드", location="서울"),   # 통과
        _job_stub(title="Java 백엔드", location="서울"),     # 키워드 불일치
        _job_stub(title="Python 백엔드", location="부산"),   # 지역 불일치
    ]
    result = filter_jobs(jobs)
    assert len(result) == 1
    assert result[0]["title"] == "Python 백엔드"

def test_filter_jobs_blocks_blacklisted_company(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", [])
    monkeypatch.setattr(config, "LOCATIONS", [])
    monkeypatch.setattr(config, "CAREER_TYPE", [])
    monkeypatch.setattr(config, "EXP_MIN", None)
    monkeypatch.setattr(config, "EXP_MAX", None)
    monkeypatch.setattr(config, "EXCLUDE_COMPANIES", ["블랙기업"])
    jobs = [
        _job_stub(title="백엔드", company="(주)블랙기업"),
        _job_stub(title="백엔드", company="(주)좋은회사"),
    ]
    result = filter_jobs(jobs)
    assert len(result) == 1
    assert result[0]["company"] == "(주)좋은회사"
