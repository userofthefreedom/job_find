from __future__ import annotations
import os
from datetime import date, datetime

from jobfind.bundle_detection import is_bundled_posting

DIVIDER = "═" * 48
BUNDLE_NOTICE = (
    "복수 직무 묶음 공고일 수 있음 — [자소서]로 선택 시 materials/notes.md에 "
    "실제 지원 직무를 명시하세요"
)


def _format_deadline(deadline: str) -> str:
    """마감일에 D-day를 붙인다 (Phase 6, 예: "2026-08-31 (D-16)"). 형식이 다르거나
    파싱 실패하면(예상치 못한 값) 원본 문자열을 그대로 반환해 저장 자체는 막지 않는다."""
    try:
        d = date.fromisoformat(deadline)
    except ValueError:
        return deadline
    days_left = (d - date.today()).days
    return f"{deadline} (마감)" if days_left < 0 else f"{deadline} (D-{days_left})"


def ensure_output_dir() -> None:
    os.makedirs("output", exist_ok=True)


def append_run_log(line: str, path: str) -> None:
    """collect 실행 요약을 output/run_log.txt에 누적한다 (Phase 5, 안정성/신뢰성).
    콘솔 출력과 별도로 남겨 무인 실행이 아니어도 지난 실행 이력을 나중에 확인할 수 있게 한다."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def format_block(job: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    cond = " | ".join(p for p in [job["location"], job["job_type"], job["experience"]] if p)
    lines = [
        DIVIDER,
        "[ ]",
        f"[수집일] {today}",
        f"[출처]   {job['source']}",
        f"[회사]   {job['company']}",
        f"[제목]   {job['title']}",
    ]
    if cond:
        lines.append(f"[조건]   {cond}")
    if job["keyword"]:
        lines.append(f"[직무]   {job['keyword']}")
    if is_bundled_posting(job):
        lines.append(f"[공채후보] {BUNDLE_NOTICE}")
    lines.append(f"[링크]   {job['url']}")
    if job["deadline"]:
        lines.append(f"[마감]   {_format_deadline(job['deadline'])}")
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


def find_block(jobs_path: str, job_id: str) -> str | None:
    if not os.path.exists(jobs_path):
        return None
    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())
    for block in blocks:
        if extract_id(block) == job_id:
            return block
    return None


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


def is_selected(block: str) -> bool:
    return any(ln.strip() == "[자소서]" for ln in block.splitlines())


def is_bundled(block: str) -> bool:
    return any(ln.startswith("[공채후보]") for ln in block.splitlines())


def extract_id(block: str) -> str | None:
    for ln in block.splitlines():
        if ln.startswith("[ID]"):
            parts = ln.split(None, 1)
            return parts[1].strip() if len(parts) > 1 else None
    return None


def extract_field(block: str, label: str) -> str:
    for ln in block.splitlines():
        if ln.startswith(label):
            parts = ln.split(None, 1)
            return parts[1].strip() if len(parts) > 1 else ""
    return ""


def append_dismissed_ids(ids: list[str], path: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for id_ in ids:
            f.write(id_ + "\n")


def load_archived_ids(path: str) -> set[str]:
    """탈락 처리된 공고 ID 목록을 읽는다 (Phase 7). 파일 형식은 dismissed_ids.txt와 동일하다."""
    return load_dismissed_ids(path)


def append_archived_ids(ids: list[str], path: str) -> None:
    append_dismissed_ids(ids, path)


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


def process_status_markers(jobs_path: str, archived_path: str) -> dict[str, int]:
    """[상태] 마커를 스캔한다 (Phase 7). "탈락"은 [X]처럼 파일에서 제거하고
    archived_ids.txt에 영구 기록한다. 그 외 상태(지원함/면접/합격 등)는 개수만 세어
    반환하고 파일에는 그대로 남긴다 — 진행 중인 지원 현황은 jobs_all.txt에서 계속
    확인할 수 있어야 하기 때문이다. [상태] 줄이 없는 블록은 집계에서 제외된다."""
    if not os.path.exists(jobs_path):
        return {}
    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())
    keep: list[str] = []
    archived_ids: list[str] = []
    counts: dict[str, int] = {}
    for block in blocks:
        status = extract_field(block, "[상태]")
        if status == "탈락":
            id_ = extract_id(block)
            if id_:
                archived_ids.append(id_)
                continue
        if status:
            counts[status] = counts.get(status, 0) + 1
        keep.append(block)
    if archived_ids:
        append_archived_ids(archived_ids, archived_path)
        rewrite_jobs_file(keep, jobs_path)
    return counts
