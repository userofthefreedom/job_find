from __future__ import annotations
import os
import tempfile
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from fetch_jobs import (
    DIVIDER,
    _norm_title,
    _parse_list,
    _parse_optional_int,
    _wanted_experience,
    append_dismissed_ids,
    config,
    deduplicate_cross_platform,
    extract_id,
    filter_career_type,
    filter_exp_range,
    filter_jobs,
    filter_keywords,
    filter_location,
    format_block,
    is_dismissed,
    load_active_ids,
    load_config,
    load_dismissed_ids,
    normalize_saramin,
    normalize_wanted,
    parse_blocks,
    parse_saramin_date,
    process_x_markers,
)

# ── parse_saramin_date ────────────────────────────────────────────────────────

def test_parse_saramin_date_normal():
    result = parse_saramin_date("~ 08/06(목)")
    assert result == f"{datetime.now().year}-08-06"

def test_parse_saramin_date_empty():
    assert parse_saramin_date("") == ""

def test_parse_saramin_date_no_match():
    assert parse_saramin_date("상시채용") == ""


# ── _wanted_experience ────────────────────────────────────────────────────────

def test_wanted_experience_none():
    assert _wanted_experience(0, 0) == "경력무관"

def test_wanted_experience_newbie():
    assert _wanted_experience(0, 3) == "신입~3년"

def test_wanted_experience_range():
    assert _wanted_experience(3, 7) == "경력 3~7년"


# ── config.ini 로드 ───────────────────────────────────────────────────────────

def test_parse_list_splits_and_strips():
    assert _parse_list(" Python ,  백엔드,") == ["Python", "백엔드"]

def test_parse_list_empty_string():
    assert _parse_list("") == []

def test_parse_optional_int_blank_is_none():
    assert _parse_optional_int("  ") is None

def test_parse_optional_int_parses_value():
    assert _parse_optional_int(" 5 ") == 5

def test_load_config_reads_ini(tmp_path):
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[filter]\n"
        "keywords = Python, 백엔드\n"
        "locations = 서울\n"
        "career_type = 경력\n"
        "exp_min = 1\n"
        "exp_max = 5\n"
        "exclude_keywords = 교육생\n",
        encoding="utf-8",
    )
    cfg = load_config(str(ini))
    assert cfg.KEYWORDS == ["Python", "백엔드"]
    assert cfg.LOCATIONS == ["서울"]
    assert cfg.CAREER_TYPE == "경력"
    assert cfg.EXP_MIN == 1
    assert cfg.EXP_MAX == 5
    assert cfg.EXCLUDE_KEYWORDS == ["교육생"]

def test_load_config_blank_fields_allow_all(tmp_path):
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[filter]\n"
        "keywords =\n"
        "locations =\n"
        "career_type =\n"
        "exp_min =\n"
        "exp_max =\n"
        "exclude_keywords =\n",
        encoding="utf-8",
    )
    cfg = load_config(str(ini))
    assert cfg.KEYWORDS == []
    assert cfg.LOCATIONS == []
    assert cfg.CAREER_TYPE is None
    assert cfg.EXP_MIN is None
    assert cfg.EXP_MAX is None
    assert cfg.EXCLUDE_KEYWORDS == []

def test_load_config_missing_file_allows_all():
    cfg = load_config("nonexistent_config.ini")
    assert cfg.KEYWORDS == []
    assert cfg.CAREER_TYPE is None


# ── normalize_saramin ─────────────────────────────────────────────────────────

_SARAMIN_HTML = """
<div class="item_recruit" value="12345">
  <div class="area_job">
    <h2 class="job_tit">
      <a title="Python 백엔드 개발자"
         href="/zf_user/jobs/relay/view?rec_idx=12345&amp;search_uuid=abc">
        <span>Python 백엔드 개발자</span>
      </a>
    </h2>
    <div class="job_date"><span class="date">~ 08/31(일)</span></div>
    <div class="job_condition">
      <span><a>서울</a> <a>강남구</a></span>
      <span>경력 3~5년</span>
      <span>대졸↑</span>
      <span>정규직</span>
    </div>
    <div class="job_sector">
      <a>Python</a>, <a>Django</a>
    </div>
  </div>
  <div class="area_corp">
    <strong class="corp_name">테스트컴퍼니</strong>
  </div>
</div>
"""

def _saramin_item():
    return BeautifulSoup(_SARAMIN_HTML, "html.parser").select_one("div.item_recruit")

def test_normalize_saramin_basic():
    job = normalize_saramin(_saramin_item())
    assert job is not None
    assert job["id"] == "saramin_12345"
    assert job["source"] == "사람인"
    assert job["title"] == "Python 백엔드 개발자"
    assert job["company"] == "테스트컴퍼니"
    assert "서울" in job["location"]
    assert job["experience"] == "경력 3~5년"
    assert job["job_type"] == "정규직"
    assert "Python" in job["keyword"]
    assert job["url"] == "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345"
    assert job["deadline"] == f"{datetime.now().year}-08-31"

def test_normalize_saramin_missing_value():
    html = _SARAMIN_HTML.replace('value="12345"', 'value=""')
    item = BeautifulSoup(html, "html.parser").select_one("div.item_recruit")
    assert normalize_saramin(item) is None


# ── normalize_wanted ──────────────────────────────────────────────────────────

_WANTED_ITEM = {
    "id": 99999,
    "position": "백엔드 개발자 (Python)",
    "company": {"name": "원티드랩"},
    "address": {"location": "서울"},
    "annual_from": 2,
    "annual_to": 5,
    "due_time": "2026-08-31",
}

def test_normalize_wanted_basic():
    job = normalize_wanted(_WANTED_ITEM)
    assert job is not None
    assert job["id"] == "wanted_99999"
    assert job["source"] == "원티드"
    assert job["title"] == "백엔드 개발자 (Python)"
    assert job["company"] == "원티드랩"
    assert job["location"] == "서울"
    assert job["experience"] == "경력 2~5년"
    assert job["deadline"] == "2026-08-31"
    assert job["url"] == "https://www.wanted.co.kr/wd/99999"

def test_normalize_wanted_null_deadline():
    item = {**_WANTED_ITEM, "due_time": None}
    job = normalize_wanted(item)
    assert job is not None
    assert job["deadline"] == ""

def test_normalize_wanted_missing_key():
    assert normalize_wanted({"id": 1}) is None


# ── format_block ──────────────────────────────────────────────────────────────

_JOB = {
    "id": "saramin_12345",
    "source": "사람인",
    "company": "테스트컴퍼니",
    "title": "Python 백엔드 개발자",
    "location": "서울",
    "job_type": "정규직",
    "experience": "경력 3~5년",
    "keyword": "Python, Django",
    "url": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345",
    "deadline": "2026-08-31",
}

def test_format_block_contains_required_fields():
    block = format_block(_JOB)
    assert "[출처]   사람인" in block
    assert "[ID]     saramin_12345" in block
    assert "[제목]   Python 백엔드 개발자" in block
    assert "[직무]   Python, Django" in block
    assert "[마감]   2026-08-31" in block
    assert block.startswith("═")
    assert block.rstrip().endswith("═" * 48)

def test_format_block_skips_empty_keyword():
    job = {**_JOB, "keyword": ""}
    block = format_block(job)
    assert "[직무]" not in block

def test_format_block_skips_empty_deadline():
    job = {**_JOB, "deadline": ""}
    block = format_block(job)
    assert "[마감]" not in block

def test_format_block_id_is_last_content_line():
    block = format_block(_JOB)
    lines = [l for l in block.strip().splitlines() if l.strip()]
    assert lines[-2].startswith("[ID]")  # last content line before closing divider

def test_format_block_includes_empty_check_marker():
    block = format_block(_JOB)
    lines = block.splitlines()
    assert lines[1] == "[ ]"  # 구분선 바로 다음 줄에 체크용 빈 마커


# ── load_active_ids ───────────────────────────────────────────────────────────

def test_load_active_ids():
    content = (
        "════\n[수집일] 2026-07-09\n[ID]     saramin_111\n════\n"
        "════\n[수집일] 2026-07-09\n[ID]     wanted_222\n════\n"
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        ids = load_active_ids(path)
        assert ids == {"saramin_111", "wanted_222"}
    finally:
        os.unlink(path)

def test_load_active_ids_missing_file():
    assert load_active_ids("nonexistent.txt") == set()


# ── load_dismissed_ids ────────────────────────────────────────────────────────

def test_load_dismissed_ids():
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write("saramin_999\nwanted_888\n")
        path = f.name
    try:
        assert load_dismissed_ids(path) == {"saramin_999", "wanted_888"}
    finally:
        os.unlink(path)


# ── deduplicate_cross_platform ────────────────────────────────────────────────

def _job(source, title, deadline="2026-08-31", location="서울", job_id="x"):
    return {"id": job_id, "source": source, "title": title,
            "deadline": deadline, "location": location}

def test_dedup_removes_exact_title_same_deadline():
    s = [_job("사람인", "Python 백엔드 개발자", job_id="saramin_1")]
    w = [_job("원티드", "Python 백엔드 개발자", job_id="wanted_1")]
    result = deduplicate_cross_platform(s, w)
    ids = [j["id"] for j in result]
    assert "saramin_1" in ids
    assert "wanted_1" not in ids

def test_dedup_keeps_different_job():
    s = [_job("사람인", "Python 백엔드 개발자", job_id="saramin_1")]
    w = [_job("원티드", "Java 백엔드 개발자", job_id="wanted_2")]
    result = deduplicate_cross_platform(s, w)
    assert len(result) == 2

def test_dedup_keeps_if_different_deadline_and_location():
    s = [_job("사람인", "Python 백엔드 개발자", deadline="2026-08-31", location="서울", job_id="saramin_1")]
    w = [_job("원티드", "Python 백엔드 개발자", deadline="2026-09-30", location="부산", job_id="wanted_1")]
    result = deduplicate_cross_platform(s, w)
    assert len(result) == 2

def test_norm_title_strips_spaces_and_lowercases():
    assert _norm_title("Python 백엔드  개발자") == "python백엔드개발자"


# ── filter_keywords ───────────────────────────────────────────────────────────

def _job_stub(**kwargs):
    base = {"title": "", "keyword": "", "location": "", "experience": "", "job_type": ""}
    return {**base, **kwargs}

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

def test_filter_career_type_none_allows_all(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", None)
    assert filter_career_type(_job_stub(experience="신입"))

def test_filter_career_type_match(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", "경력")
    assert filter_career_type(_job_stub(experience="경력 3~5년"))

def test_filter_career_type_both_accepts_entry_only(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", "신입·경력")
    assert filter_career_type(_job_stub(experience="신입"))

def test_filter_career_type_both_accepts_career_unrestricted(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", "신입·경력")
    assert filter_career_type(_job_stub(experience="경력무관"))

def test_filter_career_type_both_accepts_specific_range(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", "신입·경력")
    assert filter_career_type(_job_stub(experience="경력 3~8년"))

def test_filter_career_type_both_rejects_blank(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", "신입·경력")
    assert not filter_career_type(_job_stub(experience=""))

def test_filter_career_type_no_match(monkeypatch):
    monkeypatch.setattr(config, "CAREER_TYPE", "경력")
    assert not filter_career_type(_job_stub(experience="신입"))


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

# ── parse_blocks ──────────────────────────────────────────────────────────────

def _make_block(job_id: str, x_marker: bool = False) -> str:
    lines = [DIVIDER, f"[수집일] 2026-07-09"]
    if x_marker:
        lines.append("[X]")
    lines += [f"[제목]   테스트 공고", f"[ID]     {job_id}", DIVIDER]
    return "\n".join(lines) + "\n"

def test_parse_blocks_single():
    text = _make_block("saramin_1")
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert "saramin_1" in blocks[0]

def test_parse_blocks_multiple():
    text = _make_block("saramin_1") + _make_block("wanted_2")
    blocks = parse_blocks(text)
    assert len(blocks) == 2

def test_parse_blocks_empty():
    assert parse_blocks("") == []


# ── is_dismissed ──────────────────────────────────────────────────────────────

def test_is_dismissed_upper():
    assert is_dismissed(_make_block("saramin_1", x_marker=True))

def test_is_dismissed_lower():
    block = _make_block("saramin_1").replace(DIVIDER + "\n[수집일]", DIVIDER + "\n[x]\n[수집일]")
    assert is_dismissed(block)

def test_is_dismissed_no_marker():
    assert not is_dismissed(_make_block("saramin_1"))


# ── extract_id ────────────────────────────────────────────────────────────────

def test_extract_id_found():
    assert extract_id(_make_block("saramin_99")) == "saramin_99"

def test_extract_id_not_found():
    block = DIVIDER + "\n[제목] 뭔가\n" + DIVIDER
    assert extract_id(block) is None


# ── process_x_markers ─────────────────────────────────────────────────────────

def test_process_x_markers_removes_block_and_records_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")

        normal = _make_block("saramin_1")
        marked = _make_block("wanted_2", x_marker=True)
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(normal + marked)

        count = process_x_markers(jobs_path, dismissed_path)

        assert count == 1
        remaining = open(jobs_path, encoding="utf-8").read()
        assert "saramin_1" in remaining
        assert "wanted_2" not in remaining
        dismissed = open(dismissed_path, encoding="utf-8").read()
        assert "wanted_2" in dismissed

def test_process_x_markers_no_file_returns_zero():
    assert process_x_markers("nonexistent.txt", "nonexistent2.txt") == 0

def test_process_x_markers_no_marker_does_nothing():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        content = _make_block("saramin_1") + _make_block("wanted_2")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)
        count = process_x_markers(jobs_path, dismissed_path)
        assert count == 0
        assert not os.path.exists(dismissed_path)
        assert open(jobs_path, encoding="utf-8").read() == content

def test_process_x_markers_block_without_id_preserved():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        no_id_block = DIVIDER + "\n[X]\n[제목] 손상된 블록\n" + DIVIDER + "\n"
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(no_id_block)
        count = process_x_markers(jobs_path, dismissed_path)
        assert count == 0  # [ID] 없으므로 제거하지 않음


# ── filter_jobs ───────────────────────────────────────────────────────────────

def test_filter_jobs_and_logic(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", ["Python"])
    monkeypatch.setattr(config, "LOCATIONS", ["서울"])
    monkeypatch.setattr(config, "CAREER_TYPE", None)
    monkeypatch.setattr(config, "EXP_MIN", None)
    monkeypatch.setattr(config, "EXP_MAX", None)
    jobs = [
        _job_stub(title="Python 백엔드", location="서울"),   # 통과
        _job_stub(title="Java 백엔드", location="서울"),     # 키워드 불일치
        _job_stub(title="Python 백엔드", location="부산"),   # 지역 불일치
    ]
    result = filter_jobs(jobs)
    assert len(result) == 1
    assert result[0]["title"] == "Python 백엔드"
