from __future__ import annotations
from datetime import datetime

from bs4 import BeautifulSoup

from jobfind.collectors.saramin import _parse_og_description, normalize_saramin, parse_saramin_date
from jobfind.collectors.wanted import _wanted_experience, normalize_wanted

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


# ── _parse_og_description ─────────────────────────────────────────────────────

def test_parse_og_description_full_fields():
    desc = (
        "(주)투비파트너즈, 연구소(PM), 경력:경력 3~10년, 학력:대학교(4년)이상, "
        "지역:서울 서초구, 마감일:2026-08-27, 홈페이지:tbps.co.kr"
    )
    info = _parse_og_description(desc)
    assert info["company"] == "(주)투비파트너즈"
    assert info["title"] == "연구소(PM)"
    assert info["experience"] == "경력 3~10년"
    assert info["location"] == "서울 서초구"
    assert info["deadline"] == "2026-08-27"

def test_parse_og_description_missing_location_field():
    # 급여 등 라벨 없는 항목이 섞여도 알려진 라벨만 뽑고 나머지는 무시한다.
    desc = "(주)캠토, 용역부문 기획 담당자 채용, 경력:경력무관, 학력:학력무관, 면접 후 결정, 마감일:2026-08-14"
    info = _parse_og_description(desc)
    assert info["company"] == "(주)캠토"
    assert info["title"] == "용역부문 기획 담당자 채용"
    assert info["experience"] == "경력무관"
    assert info["location"] == ""
    assert info["deadline"] == "2026-08-14"

def test_parse_og_description_empty_string():
    info = _parse_og_description("")
    assert info["company"] == ""
    assert info["title"] == ""
