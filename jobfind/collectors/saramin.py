from __future__ import annotations
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SARAMIN_URL = "https://www.saramin.co.kr/zf_user/search/recruit"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_saramin_page(page: int) -> bytes | None:
    for attempt in range(2):
        try:
            resp = requests.get(
                SARAMIN_URL,
                params={"days": 1, "recruitPageCount": 40, "recruitPage": page, "sort": "RL"},
                headers={"User-Agent": _UA, "Accept-Language": "ko-KR,ko;q=0.9"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            if attempt == 1:
                print(f"[사람인] {page}페이지 오류: {e}")
    return None


def parse_saramin_date(text: str) -> str:
    m = re.search(r"(\d{2})/(\d{2})", text)
    if not m:
        return ""
    return f"{datetime.now().year}-{m.group(1)}-{m.group(2)}"


def normalize_saramin(item) -> dict | None:
    try:
        rec_idx = item.get("value", "").strip()
        a = item.select_one("h2.job_tit a")
        title = (a.get("title") or a.get_text(strip=True)) if a else ""
        corp = item.select_one("strong.corp_name")
        company = corp.get_text(strip=True) if corp else ""
        spans = item.select("div.job_condition span")
        location = spans[0].get_text(" ", strip=True) if spans else ""
        experience = spans[1].get_text(strip=True) if len(spans) > 1 else ""
        job_type = spans[3].get_text(strip=True) if len(spans) > 3 else ""
        keyword = ", ".join(a.get_text(strip=True) for a in item.select("div.job_sector a"))
        date_el = item.select_one("div.job_date span.date")
        deadline = parse_saramin_date(date_el.get_text(strip=True)) if date_el else ""
        if not rec_idx or not title:
            return None
        return {
            "id": f"saramin_{rec_idx}",
            "source": "사람인",
            "company": company,
            "title": title,
            "location": location,
            "job_type": job_type,
            "experience": experience,
            "keyword": keyword,
            "url": f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec_idx}",
            "deadline": deadline,
        }
    except (AttributeError, IndexError, KeyError):
        return None


def fetch_saramin_all() -> list[dict]:
    jobs: list[dict] = []
    for page in range(1, 11):
        content = fetch_saramin_page(page)
        if not content:
            break
        items = BeautifulSoup(content, "html.parser").select("div.item_recruit")
        if not items:
            break
        for item in items:
            job = normalize_saramin(item)
            if job:
                jobs.append(job)
        if len(items) < 40:
            break
    return jobs
