from __future__ import annotations

import requests

WANTED_URL = "https://www.wanted.co.kr/api/v4/jobs"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_wanted_page(offset: int) -> list | None:
    for attempt in range(2):
        try:
            resp = requests.get(
                WANTED_URL,
                params={"job_sort": "job.latest_order", "limit": 20, "offset": offset, "country": "kr"},
                headers={"User-Agent": _UA, "Accept": "application/json", "Referer": "https://www.wanted.co.kr/"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except (requests.RequestException, ValueError) as e:
            if attempt == 1:
                print(f"[원티드] offset={offset} 오류: {e}")
    return None


def _wanted_experience(annual_from: int, annual_to: int) -> str:
    if annual_from == 0 and annual_to == 0:
        return "경력무관"
    if annual_from == 0:
        return f"신입~{annual_to}년"
    return f"경력 {annual_from}~{annual_to}년"


def normalize_wanted(item: dict) -> dict | None:
    try:
        job_id = item["id"]
        return {
            "id": f"wanted_{job_id}",
            "source": "원티드",
            "company": item["company"]["name"],
            "title": item["position"],
            "location": item["address"]["location"],
            "job_type": "",
            "experience": _wanted_experience(item.get("annual_from", 0), item.get("annual_to", 0)),
            "keyword": "",
            "url": f"https://www.wanted.co.kr/wd/{job_id}",
            "deadline": item.get("due_time") or "",
        }
    except (KeyError, TypeError):
        return None


def _fetch_wanted_raw_job(job_id: str) -> dict | None:
    """상세 API 원본 job dict를 그대로 반환한다 (normalize_wanted가 버리는
    detail.intro/main_tasks/requirements 등 본문 필드를 포함)."""
    url = f"{WANTED_URL}/{job_id}"
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _UA, "Accept": "application/json", "Referer": "https://www.wanted.co.kr/"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("job")
        except (requests.RequestException, ValueError) as e:
            if attempt == 1:
                print(f"[원티드] 공고 상세 조회 오류: {e}")
    return None


def fetch_wanted_detail(job_id: str) -> dict | None:
    job = _fetch_wanted_raw_job(job_id)
    return normalize_wanted(job) if job else None


def fetch_wanted_description(job_id: str) -> str:
    """상세 API의 detail.* 본문 필드를 사람이 읽기 좋은 텍스트로 합쳐 반환한다.
    실패하거나 필드가 없으면 빈 문자열을 반환한다."""
    job = _fetch_wanted_raw_job(job_id)
    detail = (job or {}).get("detail", {}) or {}
    labels = [
        ("intro", "회사/포지션 소개"),
        ("main_tasks", "주요 업무"),
        ("requirements", "자격 요건"),
        ("preferred_points", "우대 사항"),
        ("benefits", "혜택 및 복지"),
    ]
    parts = [f"[{label}]\n{detail[key]}" for key, label in labels if detail.get(key)]
    return "\n\n".join(parts)


def fetch_wanted_all() -> tuple[list[dict], bool]:
    """반환: (jobs, request_failed) — 첫 요청 자체가 실패해 0건이 된 경우 request_failed=True
    (Phase 5, 오늘 신규 공고가 실제로 없어서 0건인 정상 케이스와 구분하기 위함)."""
    jobs: list[dict] = []
    offset = 0
    while offset < 100:
        page = fetch_wanted_page(offset)
        if page is None:
            return jobs, offset == 0
        if not page:
            break
        for item in page:
            job = normalize_wanted(item)
            if job:
                jobs.append(job)
        if len(page) < 20:
            break
        offset += len(page)
    return jobs, False
