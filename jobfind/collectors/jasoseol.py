from __future__ import annotations
from datetime import date, timedelta

import requests

CALENDAR_URL = "https://jasoseol.com/employment/calendar_list.json"
DETAIL_URL = "https://jasoseol.com/api/v1/employment_companies"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_ESSAY_TYPE = "고정질문"
_WINDOW_DAYS = 30


def fetch_jasoseol_calendar(start_time: str, end_time: str) -> list | None:
    """회사 단위 채용 이벤트 목록을 가져온다. 로그인 없이 동작한다(2026-08-17 실측
    확인 — 이용약관 제14조 위반 소지가 있음을 알고도 사용자가 진행을 택함,
    docs/SPEC.md §13-4a 참고). 직무명·자소서 문항 여부는 이 응답에 없고
    fetch_jasoseol_detail()로 회사마다 따로 가져와야 한다."""
    for attempt in range(2):
        try:
            resp = requests.post(
                CALENDAR_URL,
                json={"start_time": start_time, "end_time": end_time},
                headers={"User-Agent": _UA, "Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("employment", [])
        except (requests.RequestException, ValueError) as e:
            if attempt == 1:
                print(f"[자소설닷컴] 목록 조회 오류: {e}")
    return None


def fetch_jasoseol_detail(ec_id: int) -> dict | None:
    """회사 하나의 직무 목록(employments[].field)과 자소서 문항 유무
    (self_introduction_type)를 가져온다."""
    url = f"{DETAIL_URL}/{ec_id}"
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                params={"skip_read_log": "true"},
                headers={"User-Agent": _UA, "Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == 1:
                print(f"[자소설닷컴] {ec_id} 상세 조회 오류: {e}")
    return None


def normalize_jasoseol(event: dict, detail: dict | None) -> dict | None:
    try:
        ec_id = event["id"]
        company = (event.get("company_group") or {}).get("name", "").strip()
        title = (event.get("title") or "").strip()
        if not company or not title:
            return None
        employments = (detail or {}).get("employments") or []
        roles = [e["field"].strip() for e in employments if e.get("field")]
        essay_roles = [
            e["field"].strip()
            for e in employments
            if e.get("field") and e.get("self_introduction_type") == _ESSAY_TYPE
        ]
        deadline = (event.get("end_time") or "")[:10]
        job = {
            "id": f"jasoseol_{ec_id}",
            "source": "자소설닷컴",
            "company": company,
            "title": title,
            # 목록/상세 API 어디에도 근무지·경력 필드가 없다 — filters.py가 이 소스는
            # 지역/경력 필터를 건너뛰도록 별도 처리한다(job["source"] 기준).
            "location": "",
            "job_type": "",
            "experience": "",
            "keyword": ", ".join(roles),
            "url": f"https://jasoseol.com/recruit?ec={ec_id}",
            "deadline": deadline,
        }
        if essay_roles:
            job["essay_roles"] = essay_roles
        return job
    except (KeyError, TypeError, AttributeError):
        return None


def fetch_jasoseol_all(skip_ids: set[str]) -> tuple[list[dict], bool]:
    """반환: (jobs, request_failed). 목록 조회 자체가 실패하면 request_failed=True.

    skip_ids에 이미 있는 회사는 상세조회(요청 1건/회사)를 건너뛴다 — 한 달 기준 400건
    넘는 회사가 열려있어, 매일 전체를 상세조회하면 사람인·원티드를 합친 것보다도 요청량이
    커진다. 신규 회사만 상세조회하면 이후 실행부턴 그날 새로 나타난 회사 수 정도로
    줄어든다(최초 실행은 예외 — 이번 window 전체가 신규라 상세조회가 많이 발생함,
    docs/SPEC.md §13-4a 참고)."""
    today = date.today()
    start = today.isoformat()
    end = (today + timedelta(days=_WINDOW_DAYS)).isoformat()
    events = fetch_jasoseol_calendar(start, end)
    if events is None:
        return [], True
    jobs = []
    for event in events:
        job_id = f"jasoseol_{event.get('id')}"
        if job_id in skip_ids:
            continue
        detail = fetch_jasoseol_detail(event["id"])
        job = normalize_jasoseol(event, detail)
        if job:
            jobs.append(job)
    return jobs, False
