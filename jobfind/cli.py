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
    append_run_log,
    ensure_output_dir,
    find_block,
    load_active_ids,
    load_archived_ids,
    load_dismissed_ids,
    process_status_markers,
    process_x_markers,
    write_jobs,
)
from jobfind.verification import verify_jobs

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

JOBS_PATH = "output/jobs_all.txt"
DISMISSED_PATH = "output/dismissed_ids.txt"
ARCHIVED_PATH = "output/archived_ids.txt"
RUN_LOG_PATH = "output/run_log.txt"


def print_summary(total: int, x_removed: int, filtered: int, new: int, warnings: list[str]) -> str:
    """콘솔에 요약을 출력하고, run_log.txt에 그대로 남길 한 줄을 반환한다 (Phase 5)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{now}] 조회: {total}건 | X 처리: {x_removed}건 | 필터 통과: {filtered}건 | 신규 저장: {new}건"
    if warnings:
        line += " | [경고] " + " / ".join(warnings)
    print(line)
    return line


def collect() -> None:
    ensure_output_dir()
    x_count = process_x_markers(JOBS_PATH, DISMISSED_PATH)
    status_counts = process_status_markers(JOBS_PATH, ARCHIVED_PATH)
    if status_counts:
        summary = ", ".join(f"{status} {count}건" for status, count in status_counts.items())
        print(f"[지원 현황] {summary}")
    skip_ids = (
        load_active_ids(JOBS_PATH)
        | load_dismissed_ids(DISMISSED_PATH)
        | load_archived_ids(ARCHIVED_PATH)
    )
    jobs, saramin_failed, wanted_failed, page_cap_hit = fetch_all()
    filtered = filter_jobs(jobs)
    new_jobs = [j for j in filtered if j["id"] not in skip_ids]
    write_jobs(new_jobs, JOBS_PATH)

    warnings = []
    if saramin_failed:
        warnings.append("사람인 소스 전체 실패(요청 오류로 0건)")
    if wanted_failed:
        warnings.append("원티드 소스 전체 실패(요청 오류로 0건)")
    if page_cap_hit:
        warnings.append("사람인 페이지 상한(10페이지) 도달 — 더 많은 공고가 있을 수 있음")

    line = print_summary(len(jobs), x_count, len(filtered), len(new_jobs), warnings)
    append_run_log(line, RUN_LOG_PATH)


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


def verify() -> None:
    counts = verify_jobs(JOBS_PATH)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 검수 완료 | 확인: {counts['checked']}건 "
          f"(PASS {counts['pass']} · CONCERN {counts['concern']} · UNKNOWN {counts['unknown']})")
    if counts["checked"] == 0:
        print("검수할 신규 공고가 없습니다 (이미 [검수]된 공고는 건너뜁니다).")


def select() -> None:
    count, over_limit = sync_materials_folders(JOBS_PATH)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 자소서 선택 반영 | 선택됨: {count}건")
    if over_limit:
        print(f"[경고] 자소서는 최대 4개까지만 작성할 수 있습니다 (현재 {count}건 선택됨) "
              "— 초과분의 [자소서] 마커를 해제해주세요")
    for job_id in selected_ids(JOBS_PATH):
        print(f"  - output/cover_letters/{job_id}/materials/notes.md — 실제 자소서 문항이 있다면 "
              "여기에 붙여넣어 두세요 (문항 제목·글자수 제한까지 포함하면 write 단계에서 그대로 반영됩니다)")


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
    subparsers.add_parser("verify", help="목록 요약과 실제 상세 요건을 대조해 [검수] 결과를 남김 (AI 호출)")
    subparsers.add_parser("select", help="[자소서]로 표시한 공고에 materials/ 폴더를 준비")
    subparsers.add_parser("write", help="[자소서]로 선택된 공고의 자소서 초안을 작성")
    args = parser.parse_args()

    if args.command == "collect":
        collect()
    elif args.command == "evaluate":
        evaluate()
    elif args.command == "add":
        add_job(args.url)
    elif args.command == "verify":
        verify()
    elif args.command == "select":
        select()
    elif args.command == "write":
        write()


if __name__ == "__main__":
    main()
