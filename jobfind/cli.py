from __future__ import annotations
import argparse
import sys
from datetime import datetime

from jobfind.dedup import fetch_all
from jobfind.filters import filter_jobs
from jobfind.relevance import evaluate_relevance
from jobfind.storage import (
    ensure_output_dir,
    load_active_ids,
    load_dismissed_ids,
    process_x_markers,
    write_jobs,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

JOBS_PATH = "output/jobs_all.txt"
DISMISSED_PATH = "output/dismissed_ids.txt"


def print_summary(total: int, x_removed: int, filtered: int, new: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 조회: {total}건 | X 처리: {x_removed}건 | 필터 통과: {filtered}건 | 신규 저장: {new}건")


def collect() -> None:
    ensure_output_dir()
    x_count = process_x_markers(JOBS_PATH, DISMISSED_PATH)
    skip_ids = load_active_ids(JOBS_PATH) | load_dismissed_ids(DISMISSED_PATH)
    jobs = fetch_all()
    filtered = filter_jobs(jobs)
    new_jobs = [j for j in filtered if j["id"] not in skip_ids]
    write_jobs(new_jobs, JOBS_PATH)
    print_summary(len(jobs), x_count, len(filtered), len(new_jobs))


def evaluate() -> None:
    dropped = evaluate_relevance(JOBS_PATH)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 관련성 평가 완료 | 순위 밖 제외: {dropped}건")


def main() -> None:
    parser = argparse.ArgumentParser(prog="jobfind")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("collect", help="사람인+원티드 공고 수집 후 필터링해 저장")
    subparsers.add_parser("evaluate", help="수집된 공고를 직무·도메인 관련성 순으로 정렬해 상위 top_n건만 유지")
    args = parser.parse_args()

    if args.command == "collect":
        collect()
    elif args.command == "evaluate":
        evaluate()


if __name__ == "__main__":
    main()
