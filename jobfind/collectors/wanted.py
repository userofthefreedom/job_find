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


def fetch_wanted_detail(job_id: str) -> dict | None:
    url = f"{WANTED_URL}/{job_id}"
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _UA, "Accept": "application/json", "Referer": "https://www.wanted.co.kr/"},
                timeout=15,
            )
            resp.raise_for_status()
            job = resp.json().get("job")
            return normalize_wanted(job) if job else None
        except (requests.RequestException, ValueError) as e:
            if attempt == 1:
                print(f"[원티드] 공고 상세 조회 오류: {e}")
    return None


def fetch_wanted_all() -> list[dict]:
    jobs: list[dict] = []
    offset = 0
    while offset < 100:
        page = fetch_wanted_page(offset)
        if not page:
            break
        for item in page:
            job = normalize_wanted(item)
            if job:
                jobs.append(job)
        if len(page) < 20:
            break
        offset += len(page)
    return jobs
