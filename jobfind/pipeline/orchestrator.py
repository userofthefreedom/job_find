from __future__ import annotations
import os
import re
from pathlib import Path

import requests

from jobfind.collectors.saramin import fetch_saramin_images
from jobfind.collectors.wanted import fetch_wanted_description
from jobfind.config import config
from jobfind.dart import fetch_company_profile
from jobfind.pipeline import prompts
from jobfind.providers.base import get_provider
from jobfind.storage import cover_letter_folder_name, extract_field

COVER_LETTERS_DIR = "output/cover_letters"
PROFILE_PATH = "profile.md"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
# planner가 회사 리서치(뉴스·홈페이지)를 스스로 검색해 계획에 반영할 수 있게 열어주는 툴.
# claude_cli에서만 실제로 동작한다 — api:*는 --allowedTools 개념이 없어 무시된다.
PLANNER_RESEARCH_TOOLS = ["WebSearch", "WebFetch"]


def fetch_posting_text(url: str) -> str:
    """공고 링크의 상세 설명(담당업무·자격요건·우대사항 등)을 가져온다. planner/writer가
    목록 페이지 태그(제목·조건 등)만이 아니라 실제 요건까지 참고할 수 있게 하기 위함이다.

    원티드는 상세 API가 이 내용을 구조화된 필드로 그대로 제공해 신뢰도 높게 가져올 수
    있다. 사람인은 상세 페이지 본문이 자바스크립트로 렌더링돼 정적 요청으로는 실제 내용을
    가져올 수 없다는 걸 확인함 — 사람인 공고는 현재 이 함수가 빈 문자열을 반환한다
    (알려진 한계, 헤더/내비게이션 같은 노이즈를 프롬프트에 넣는 것보다 나음).
    실패해도 파이프라인은 계속 진행해야 하므로 빈 문자열을 반환한다."""
    if not url:
        return ""
    m = re.search(r"wanted\.co\.kr/wd/(\d+)", url)
    if m:
        return fetch_wanted_description(m.group(1))
    return ""


def load_profile() -> str:
    if not os.path.exists(PROFILE_PATH):
        return ""
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return f.read()


def _materials_images(materials_dir: Path) -> list[Path]:
    if not materials_dir.exists():
        return []
    return sorted(p for p in materials_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)


def _download_saramin_images(rec_idx: str, materials_dir: Path) -> None:
    """사람인 상세 본문 이미지를 materials_dir에 내려받는다(OQ5). 사람인 공고는 상세
    본문이 이미지로만 존재해 fetch_posting_text가 텍스트를 못 가져오는데, planner는
    이미 materials_dir 이미지를 참고하므로 여기 받아두면 비전 지원 provider가 자격요건을
    직접 읽을 수 있다. 파일이 이미 있으면 다시 받지 않아 write를 여러 번 실행해도
    매번 새로 다운로드하지 않는다."""
    materials_dir.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(fetch_saramin_images(rec_idx)):
        ext = os.path.splitext(url.split("?")[0])[1] or ".png"
        path = materials_dir / f"saramin_detail_{i}{ext}"
        if path.exists():
            continue
        try:
            resp = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        except requests.RequestException:
            continue


def _save(job_dir: str, name: str, text: str) -> str:
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _verdict(evaluation: str) -> str:
    first_line = evaluation.strip().splitlines()[0].strip().upper() if evaluation.strip() else ""
    return "NEEDS_REVISION" if "NEEDS_REVISION" in first_line else "OK"


def run_for_job(job_id: str, job_text: str) -> dict:
    """공고 하나에 대해 계획 → 계획평가 → (필요 시 계획 재작성) → 작성 → 초안평가 →
    (필요 시 초안 재작성 → 재평가, 최대 1회)를 실행하고, 각 단계 결과를
    output/cover_letters/<id>/에 저장한다."""
    profile = load_profile()
    job_dir = os.path.join(COVER_LETTERS_DIR, cover_letter_folder_name(job_id, job_text))
    materials_dir = Path(job_dir) / "materials"

    url = extract_field(job_text, "[링크]")
    posting_text = fetch_posting_text(url)
    if posting_text:
        job_text = f"{job_text}\n\n[공고 상세 설명]\n{posting_text}"

    m = re.search(r"saramin\.co\.kr.*rec_idx=(\d+)", url)
    if m:
        _download_saramin_images(m.group(1), materials_dir)
    images = _materials_images(materials_dir)

    company_profile = fetch_company_profile(extract_field(job_text, "[회사]"))
    if company_profile:
        job_text = f"{job_text}\n\n{company_profile}"

    planner = get_provider(config.PROVIDER_PLANNER)
    plan_evaluator = get_provider(config.PROVIDER_PLAN_EVALUATOR)
    writer = get_provider(config.PROVIDER_WRITER)
    draft_evaluator = get_provider(config.PROVIDER_DRAFT_EVALUATOR)

    system, user = prompts.planner_prompt(job_text, profile, materials_dir)
    plan = planner.run(system, user, images=images, extra_tools=PLANNER_RESEARCH_TOOLS)
    _save(job_dir, "plan.md", plan)

    system, user = prompts.plan_evaluator_prompt(job_text, plan)
    plan_review = plan_evaluator.run(system, user)
    _save(job_dir, "plan_review.md", plan_review)

    if _verdict(plan_review) == "NEEDS_REVISION":
        system, user = prompts.planner_revision_prompt(
            job_text, profile, materials_dir, plan, plan_review
        )
        plan = planner.run(system, user, images=images, extra_tools=PLANNER_RESEARCH_TOOLS)
        _save(job_dir, "plan.md", plan)

    system, user = prompts.writer_prompt(job_text, profile, plan)
    draft = writer.run(system, user)
    _save(job_dir, "draft.md", draft)

    system, user = prompts.draft_evaluator_prompt(job_text, draft)
    draft_review = draft_evaluator.run(system, user)
    _save(job_dir, "draft_review.md", draft_review)

    if _verdict(draft_review) == "NEEDS_REVISION":
        system, user = prompts.writer_revision_prompt(job_text, profile, plan, draft, draft_review)
        draft = writer.run(system, user)
        _save(job_dir, "draft.md", draft)

        system, user = prompts.draft_evaluator_prompt(job_text, draft)
        draft_review = draft_evaluator.run(system, user)
        _save(job_dir, "draft_review.md", draft_review)

    return {
        "id": job_id,
        "plan": plan,
        "plan_review": plan_review,
        "draft": draft,
        "draft_review": draft_review,
    }
