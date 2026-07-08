from __future__ import annotations
import os
import tempfile
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from fetch_jobs import (
    _norm_title,
    _wanted_experience,
    deduplicate_cross_platform,
    format_block,
    load_active_ids,
    load_dismissed_ids,
    normalize_saramin,
    normalize_wanted,
    parse_saramin_date,
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
