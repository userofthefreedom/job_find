from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path

import requests

from jobfind.collectors.saramin import fetch_saramin_images
from jobfind.collectors.wanted import fetch_wanted_description
from jobfind.config import config
from jobfind.pipeline.orchestrator import load_profile
from jobfind.pipeline.prompts import verify_prompt
from jobfind.providers.base import get_provider
from jobfind.storage import (
    extract_field,
    extract_id,
    is_dismissed,
    parse_blocks,
    rewrite_jobs_file,
)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_VALID_VERDICTS = ("PASS", "CONCERN", "UNKNOWN")


def _already_verified(block: str) -> bool:
    return any(ln.startswith("[검수]") for ln in block.splitlines())


def _parse_verdict(result: str) -> tuple[str, str]:
    """provider 응답에서 판정(PASS/CONCERN/UNKNOWN)과 한 줄 요약을 뽑는다.

    모델이 "첫 줄에 정확히 한 단어만" 지침을 항상 지키지는 않는다 — 마크다운 볼드
    (`**CONCERN**`)를 쓰거나, 판정 앞뒤에 군더더기 문장을 붙이거나, 스스로 "수정:" 하며
    처음 판정을 뒤집는 경우까지 실사용 중 확인됨. 그래서 응답에서 판정 단어를 전부 찾아
    **마지막 occurrence**를 최종 판단으로 취급한다(자기 정정 패턴에 더 안전) — 그 단어만
    제거한 나머지를 요약으로 쓴다. 줄바꿈은 공백으로 합쳐 [검수] 메모가 항상 한 줄을
    유지하게 한다(다른 필드들과 형식을 맞추기 위함) — 이렇게 해야 파일 파싱이 깨지지 않는다.
    """
    flat = " ".join(result.replace("*", " ").split())
    matches = list(re.finditer(r"\b(PASS|CONCERN|UNKNOWN)\b", flat, re.IGNORECASE))
    if not matches:
        return "UNKNOWN", flat
    last = matches[-1]
    verdict = last.group(1).upper()
    summary = (flat[: last.start()] + flat[last.end() :]).strip(" :-")
    summary = " ".join(summary.split())
    return verdict, summary


def _download_images(urls: list[str], job_id: str) -> list[Path]:
    tmp_dir = Path(tempfile.gettempdir()) / "jobfind_verify" / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, url in enumerate(urls):
        try:
            resp = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        ext = os.path.splitext(url.split("?")[0])[1] or ".png"
        path = tmp_dir / f"{i}{ext}"
        path.write_bytes(resp.content)
        paths.append(path)
    return paths


def gather_evidence(url: str, job_id: str) -> tuple[str, list[Path]]:
    """(상세 텍스트, 이미지 경로 목록)을 반환한다. 원티드는 상세 API 텍스트, 사람인은
    본문 이미지를 내려받아 반환한다 — 사람인 공고 본문은 이미지로 업로드돼 있어 텍스트로는
    가져올 수 없다(`fetch_saramin_images` 참고)."""
    m = re.search(r"wanted\.co\.kr/wd/(\d+)", url)
    if m:
        return fetch_wanted_description(m.group(1)), []
    m = re.search(r"saramin\.co\.kr.*rec_idx=(\d+)", url)
    if m:
        image_urls = fetch_saramin_images(m.group(1))
        return "", _download_images(image_urls, job_id)
    return "", []


def _insert_note(block: str, note: str) -> str:
    lines = block.splitlines(keepends=True)
    insert_at = next((i for i, ln in enumerate(lines) if ln.startswith("[ID]")), len(lines) - 1)
    lines.insert(insert_at, note + "\n")
    return "".join(lines)


def verify_jobs(jobs_path: str) -> dict:
    """활성 공고 중 아직 검수하지 않은 것마다 상세 요건(원티드는 텍스트, 사람인은 이미지)과
    지원자 프로필을 대조해 [검수] 결과를 블록에 남긴다. 자동으로 지우지 않는다 — 최종
    판단(제거)은 사용자가 [X] 마커로 직접 한다. 이미 [검수]된 블록과 [X] 블록은 건너뛴다."""
    counts = {"checked": 0, "pass": 0, "concern": 0, "unknown": 0}
    if not os.path.exists(jobs_path):
        return counts

    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())

    profile = load_profile()
    verifier = get_provider(config.PROVIDER_VERIFIER)
    result_blocks: list[str] = []

    for block in blocks:
        if is_dismissed(block) or _already_verified(block):
            result_blocks.append(block)
            continue

        job_id = extract_id(block) or "unknown"
        url = extract_field(block, "[링크]")
        title = extract_field(block, "[제목]")
        print(f"- {job_id} ({title}) 검수 중...")
        try:
            posting_text, images = gather_evidence(url, job_id)
            system, user = verify_prompt(block, profile, posting_text)
            result = verifier.run(system, user, images=images)
        except Exception as e:
            print(f"  실패: {e}")
            result_blocks.append(block)
            continue

        verdict, summary = _parse_verdict(result)
        counts["checked"] += 1
        counts[verdict.lower()] += 1

        note = f"[검수] {verdict}: {summary}" if summary else f"[검수] {verdict}"
        result_blocks.append(_insert_note(block, note))

    rewrite_jobs_file(result_blocks, jobs_path)
    return counts
