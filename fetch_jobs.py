from __future__ import annotations
import os
import sys
from datetime import datetime

# Windows 콘솔/Task Scheduler 환경에서 UTF-8 출력 보장
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from dotenv import load_dotenv

JOBS_PATH = "output/jobs_all.txt"
DISMISSED_PATH = "output/dismissed_ids.txt"
API_URL = "https://oapi.saramin.co.kr/job-search"
DIVIDER = "═" * 48


def load_config() -> str:
    load_dotenv()
    key = os.getenv("SARAMIN_ACCESS_KEY")
    if not key:
        sys.exit("오류: .env 파일에 SARAMIN_ACCESS_KEY가 없습니다.")
    return key


def ensure_output_dir() -> None:
    os.makedirs("output", exist_ok=True)


def fetch_page(api_key: str, start: int) -> dict:
    params = {
        "access-key": api_key,
        "published": 1,
        "count": 110,
        "start": start,
        "sort": "RL",
    }
    headers = {"Accept": "application/json"}
    for attempt in range(2):
        try:
            resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            sys.exit(f"API 오류 {e.response.status_code}: {e}")
        except requests.RequestException as e:
            if attempt == 1:
                sys.exit(f"네트워크 오류 (재시도 실패): {e}")
    return {}


def fetch_all(api_key: str) -> list[dict]:
    jobs: list[dict] = []
    start = 0
    while True:
        data = fetch_page(api_key, start)
        page_jobs = data.get("jobs", {}).get("job", [])
        if not page_jobs:
            break
        jobs.extend(page_jobs)
        total = int(data["jobs"].get("total", 0))
        if start + 110 >= total:
            break
        start += 110
    return jobs


def ts_to_date(ts: str) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return ""


def normalize(job: dict) -> dict:
    exp = job.get("position", {}).get("experience-level", {})
    return {
        "id":         job["id"],
        "company":    job["company"]["detail"]["name"],
        "title":      job["position"]["title"],
        "location":   job["position"]["location"]["name"],
        "job_type":   job["position"]["job-type"]["name"],
        "experience": exp.get("name", ""),
        "keyword":    job.get("keyword", ""),
        "url":        job["url"],
        "deadline":   ts_to_date(job.get("expiration-timestamp", "")),
    }


def format_block(job: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    cond_parts = [p for p in [job["location"], job["job_type"], job["experience"]] if p]
    lines = [
        DIVIDER,
        f"[수집일] {today}",
        f"[회사]   {job['company']}",
        f"[제목]   {job['title']}",
        f"[조건]   {' | '.join(cond_parts)}",
    ]
    if job["keyword"]:
        lines.append(f"[직무]   {job['keyword']}")
    lines.append(f"[링크]   {job['url']}")
    if job["deadline"]:
        lines.append(f"[마감]   {job['deadline']}")
    lines.append(f"[ID]     {job['id']}")
    lines.append(DIVIDER)
    return "\n".join(lines) + "\n"


def load_active_ids(jobs_path: str) -> set[str]:
    if not os.path.exists(jobs_path):
        return set()
    ids: set[str] = set()
    with open(jobs_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("[ID]"):
                ids.add(line.split(None, 1)[1].strip())
    return ids


def load_dismissed_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def write_jobs(jobs: list[dict], jobs_path: str) -> None:
    with open(jobs_path, "a", encoding="utf-8") as f:
        for job in jobs:
            f.write(format_block(job))


def print_summary(total: int, new: int) -> None:
    print(f"조회: {total}건 | 신규 저장: {new}건")


def main() -> None:
    api_key = load_config()
    ensure_output_dir()

    active = load_active_ids(JOBS_PATH)
    dismissed = load_dismissed_ids(DISMISSED_PATH)
    skip_ids = active | dismissed

    raw_jobs = fetch_all(api_key)
    total = len(raw_jobs)

    normalized: list[dict] = []
    for job in raw_jobs:
        try:
            normalized.append(normalize(job))
        except (KeyError, TypeError) as e:
            print(f"경고: 공고 파싱 실패 ({e}), 건너뜀")

    new_jobs = [j for j in normalized if j["id"] not in skip_ids]
    write_jobs(new_jobs, JOBS_PATH)
    print_summary(total, len(new_jobs))


if __name__ == "__main__":
    main()
