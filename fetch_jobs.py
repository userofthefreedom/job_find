from __future__ import annotations
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher

from bs4 import BeautifulSoup
import requests
import config

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

JOBS_PATH = "output/jobs_all.txt"
DISMISSED_PATH = "output/dismissed_ids.txt"
SARAMIN_URL = "https://www.saramin.co.kr/zf_user/search/recruit"
WANTED_URL = "https://www.wanted.co.kr/api/v4/jobs"
DIVIDER = "═" * 48
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def ensure_output_dir() -> None:
    os.makedirs("output", exist_ok=True)


# ── Saramin ───────────────────────────────────────────────────────────────────

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


# ── Wanted ────────────────────────────────────────────────────────────────────

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


# ── Cross-platform dedup ──────────────────────────────────────────────────────

def _norm_title(title: str) -> str:
    return re.sub(r"\s+", "", title).lower()


def deduplicate_cross_platform(saramin: list[dict], wanted: list[dict]) -> list[dict]:
    result = list(saramin)
    for w in wanted:
        is_dup = any(
            SequenceMatcher(None, _norm_title(s["title"]), _norm_title(w["title"])).ratio() >= 0.85
            and (s["deadline"] == w["deadline"] or s["location"] == w["location"])
            for s in saramin
        )
        if not is_dup:
            result.append(w)
    return result


def fetch_all() -> list[dict]:
    return deduplicate_cross_platform(fetch_saramin_all(), fetch_wanted_all())


# ── Filters ──────────────────────────────────────────────────────────────────

def filter_keywords(job: dict) -> bool:
    if not config.KEYWORDS:
        return True
    text = f"{job['title']} {job['keyword']}".lower()
    return any(kw.lower() in text for kw in config.KEYWORDS)


def filter_location(job: dict) -> bool:
    if not config.LOCATIONS:
        return True
    return any(loc in job["location"] for loc in config.LOCATIONS)


def filter_career_type(job: dict) -> bool:
    if config.CAREER_TYPE is None:
        return True
    return config.CAREER_TYPE in job["experience"]


def filter_exp_range(job: dict) -> bool:
    if config.EXP_MIN is None and config.EXP_MAX is None:
        return True
    nums = [int(n) for n in re.findall(r"\d+", job["experience"])]
    if not nums:
        return True  # 추출 불가(경력무관·신입 등) → 관대하게 통과
    lo = config.EXP_MIN if config.EXP_MIN is not None else 0
    hi = config.EXP_MAX if config.EXP_MAX is not None else 99
    return min(nums) <= hi and max(nums) >= lo


def filter_jobs(jobs: list[dict]) -> list[dict]:
    return [
        j for j in jobs
        if filter_keywords(j) and filter_location(j)
        and filter_career_type(j) and filter_exp_range(j)
    ]


# ── Storage ───────────────────────────────────────────────────────────────────

def format_block(job: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    cond = " | ".join(p for p in [job["location"], job["job_type"], job["experience"]] if p)
    lines = [
        DIVIDER,
        f"[수집일] {today}",
        f"[출처]   {job['source']}",
        f"[회사]   {job['company']}",
        f"[제목]   {job['title']}",
    ]
    if cond:
        lines.append(f"[조건]   {cond}")
    if job["keyword"]:
        lines.append(f"[직무]   {job['keyword']}")
    lines.append(f"[링크]   {job['url']}")
    if job["deadline"]:
        lines.append(f"[마감]   {job['deadline']}")
    lines += [f"[ID]     {job['id']}", DIVIDER]
    return "\n".join(lines) + "\n"


def load_active_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {ln.split(None, 1)[1].strip() for ln in f if ln.startswith("[ID]")}


def load_dismissed_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip()}


def write_jobs(jobs: list[dict], path: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for job in jobs:
            f.write(format_block(job))


# ── X 마커 처리 ──────────────────────────────────────────────────────────────

def parse_blocks(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    start: int | None = None
    for i, line in enumerate(lines):
        if line.rstrip() == DIVIDER:
            if start is None:
                start = i
            else:
                blocks.append("".join(lines[start:i + 1]))
                start = None
    return blocks


def is_dismissed(block: str) -> bool:
    return any(ln.strip().upper() == "[X]" for ln in block.splitlines())


def extract_id(block: str) -> str | None:
    for ln in block.splitlines():
        if ln.startswith("[ID]"):
            parts = ln.split(None, 1)
            return parts[1].strip() if len(parts) > 1 else None
    return None


def append_dismissed_ids(ids: list[str], path: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for id_ in ids:
            f.write(id_ + "\n")


def rewrite_jobs_file(blocks: list[str], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for block in blocks:
            f.write(block)


def process_x_markers(jobs_path: str, dismissed_path: str) -> int:
    if not os.path.exists(jobs_path):
        return 0
    with open(jobs_path, encoding="utf-8") as f:
        text = f.read()
    blocks = parse_blocks(text)
    keep: list[str] = []
    removed_ids: list[str] = []
    for block in blocks:
        if is_dismissed(block):
            id_ = extract_id(block)
            if id_:
                removed_ids.append(id_)
        else:
            keep.append(block)
    if removed_ids:
        append_dismissed_ids(removed_ids, dismissed_path)
        rewrite_jobs_file(keep, jobs_path)
        print(f"[X] 처리: {len(removed_ids)}건 제거됨")
    return len(removed_ids)


def print_summary(total: int, x_removed: int, filtered: int, new: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 조회: {total}건 | X 처리: {x_removed}건 | 필터 통과: {filtered}건 | 신규 저장: {new}건")


def main() -> None:
    ensure_output_dir()
    x_count = process_x_markers(JOBS_PATH, DISMISSED_PATH)
    skip_ids = load_active_ids(JOBS_PATH) | load_dismissed_ids(DISMISSED_PATH)
    jobs = fetch_all()
    filtered = filter_jobs(jobs)
    new_jobs = [j for j in filtered if j["id"] not in skip_ids]
    write_jobs(new_jobs, JOBS_PATH)
    print_summary(len(jobs), x_count, len(filtered), len(new_jobs))


if __name__ == "__main__":
    main()
