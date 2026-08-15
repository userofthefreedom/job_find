from __future__ import annotations
import html as html_lib
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


def _parse_og_description(desc: str) -> dict:
    """상세 페이지 og:description은 "회사, 제목, 경력:X, 학력:X, 지역:X, 마감일:X, ..."
    형태다. 항목마다 있고 없음이 달라 위치가 아닌 "라벨:값" 패턴으로만 필요한 값을 뽑는다."""
    parts = [p.strip() for p in desc.split(",")]
    company = parts[0] if parts else ""
    title = parts[1] if len(parts) > 1 else ""
    fields: dict[str, str] = {}
    for part in parts[2:]:
        if ":" in part:
            label, _, value = part.partition(":")
            fields[label.strip()] = value.strip()
    return {
        "company": company,
        "title": title,
        "experience": fields.get("경력", ""),
        "location": fields.get("지역", ""),
        "deadline": fields.get("마감일", ""),
    }


def fetch_saramin_detail(rec_idx: str) -> dict | None:
    url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec_idx}"
    html_text = None
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _UA, "Accept-Language": "ko-KR,ko;q=0.9"},
                timeout=15,
            )
            resp.raise_for_status()
            html_text = resp.text
            break
        except requests.RequestException as e:
            if attempt == 1:
                print(f"[사람인] 공고 상세 조회 오류: {e}")
    if html_text is None:
        return None

    m = re.search(r'<meta property="og:description" content="([^"]*)"', html_text)
    if not m:
        return None
    info = _parse_og_description(html_lib.unescape(m.group(1)))
    if not info["title"]:
        return None
    return {
        "id": f"saramin_{rec_idx}",
        "source": "사람인",
        "company": info["company"],
        "title": info["title"],
        "location": info["location"],
        "job_type": "",
        "experience": info["experience"],
        "keyword": "",
        "url": url,
        "deadline": info["deadline"],
    }


def fetch_saramin_images(rec_idx: str) -> list[str]:
    """상세 공고 본문 이미지 URL 목록을 반환한다. 사람인은 자격요건 등 본문 전체를
    이미지로 올려두고(§13-3의 "JS 렌더링이라 텍스트를 못 가져온다"보다 근본적인 문제 —
    아예 텍스트가 없음), 그 이미지는 `view-detail` 엔드포인트가 담당한다. 이 엔드포인트
    자체는 인증 없는 정적 HTML이라 requests만으로 이미지 URL을 얻을 수 있다(헤드리스
    브라우저 불필요) — 실제 이미지 픽셀을 읽으려면 비전 지원 provider에 넘겨야 한다.
    아이콘/워터마크 등 장식용 이미지는 파일명 패턴으로 걸러낸다."""
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view-detail"
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                params={"rec_idx": rec_idx},
                headers={"User-Agent": _UA, "Accept-Language": "ko-KR,ko;q=0.9"},
                timeout=15,
            )
            resp.raise_for_status()
            srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', resp.text)
            return [
                ("https:" + s if s.startswith("//") else s)
                for s in srcs
                if not re.search(r"icon|watermark", s, re.IGNORECASE)
            ]
        except requests.RequestException as e:
            if attempt == 1:
                print(f"[사람인] 공고 이미지 조회 오류: {e}")
    return []


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
