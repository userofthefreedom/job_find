from __future__ import annotations
import argparse
import re
import sys
from datetime import datetime

from jobfind.collectors.saramin import fetch_saramin_detail
from jobfind.collectors.wanted import fetch_wanted_detail
from jobfind.dedup import fetch_all
from jobfind.filters import filter_jobs
from jobfind.pipeline.orchestrator import run_for_job
from jobfind.relevance import evaluate_relevance
from jobfind.selection import MAX_SELECTED, selected_ids, sync_materials_folders
from jobfind.storage import (
    ensure_output_dir,
    find_block,
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


def _parse_manual_url(url: str) -> tuple[str, str] | None:
    if "saramin.co.kr" in url:
        m = re.search(r"rec_idx=(\d+)", url)
        if m:
            return "saramin", m.group(1)
    m = re.search(r"wanted\.co\.kr/wd/(\d+)", url)
    if m:
        return "wanted", m.group(1)
    return None


def add_job(url: str) -> None:
    parsed = _parse_manual_url(url)
    if not parsed:
        print("지원하지 않는 URL입니다 (사람인 공고 상세 URL 또는 wanted.co.kr/wd/<번호> 형식만 가능)")
        return

    source, job_id = parsed
    job = fetch_saramin_detail(job_id) if source == "saramin" else fetch_wanted_detail(job_id)
    if not job:
        print("공고 정보를 가져오지 못했습니다.")
        return

    skip_ids = load_active_ids(JOBS_PATH) | load_dismissed_ids(DISMISSED_PATH)
    if job["id"] in skip_ids:
        print(f"이미 목록에 있는 공고입니다: {job['title']}")
        return

    ensure_output_dir()
    write_jobs([job], JOBS_PATH)
    print(f"공고 추가됨: [{job['source']}] {job['title']} ({job['id']})")


def select() -> None:
    count, over_limit = sync_materials_folders(JOBS_PATH)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 자소서 선택 반영 | 선택됨: {count}건")
    if over_limit:
        print(f"[경고] 자소서는 최대 4개까지만 작성할 수 있습니다 (현재 {count}건 선택됨) "
              "— 초과분의 [자소서] 마커를 해제해주세요")


def write() -> None:
    ids = selected_ids(JOBS_PATH)
    if not ids:
        print("자소서를 작성할 공고가 없습니다. jobs_all.txt에서 [자소서]로 표시한 뒤 다시 시도하세요.")
        return
    if len(ids) > MAX_SELECTED:
        print(f"[오류] 자소서는 최대 {MAX_SELECTED}개까지만 작성할 수 있습니다 (현재 {len(ids)}건 선택됨). "
              "초과분의 [자소서] 마커를 해제한 뒤 다시 실행하세요.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 자소서 작성 시작 | 대상: {len(ids)}건")
    succeeded: list[str] = []
    failed: list[str] = []
    for job_id in ids:
        block = find_block(JOBS_PATH, job_id)
        if not block:
            print(f"- {job_id}: jobs_all.txt에서 찾을 수 없어 건너뜀")
            continue
        print(f"- {job_id} 작성 중...")
        try:
            run_for_job(job_id, block)
        except Exception as e:
            print(f"  실패: {e}")
            failed.append(job_id)
            continue
        print(f"  완료: output/cover_letters/{job_id}/draft.md")
        succeeded.append(job_id)

    print(f"자소서 작성 완료 — 성공 {len(succeeded)}건, 실패 {len(failed)}건. "
          "output/cover_letters/<공고ID>/ 하위에서 plan.md · plan_review.md · draft.md · "
          "draft_review.md를 확인하세요.")
    if failed:
        print(f"[실패한 공고] {', '.join(failed)} — provider 상태나 네트워크를 확인한 뒤 "
              "다시 write를 실행하면 해당 공고만 재시도됩니다.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="jobfind")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("collect", help="사람인+원티드 공고 수집 후 필터링해 저장")
    subparsers.add_parser("evaluate", help="수집된 공고를 직무·도메인 관련성 순으로 정렬해 상위 top_n건만 유지")
    add_parser = subparsers.add_parser("add", help="사람인/원티드 공고 URL을 수동으로 추가")
    add_parser.add_argument("url", help="공고 상세 페이지 URL")
    subparsers.add_parser("select", help="[자소서]로 표시한 공고에 materials/ 폴더를 준비")
    subparsers.add_parser("write", help="[자소서]로 선택된 공고의 자소서 초안을 작성")
    args = parser.parse_args()

    if args.command == "collect":
        collect()
    elif args.command == "evaluate":
        evaluate()
    elif args.command == "add":
        add_job(args.url)
    elif args.command == "select":
        select()
    elif args.command == "write":
        write()


if __name__ == "__main__":
    main()
