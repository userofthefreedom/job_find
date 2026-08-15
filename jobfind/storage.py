from __future__ import annotations
import os
from datetime import datetime

DIVIDER = "═" * 48


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
