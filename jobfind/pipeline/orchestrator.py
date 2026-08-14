from __future__ import annotations
import os
from pathlib import Path

from jobfind.config import config
from jobfind.pipeline import prompts
from jobfind.providers.base import get_provider

COVER_LETTERS_DIR = "output/cover_letters"
PROFILE_PATH = "profile.md"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def load_profile() -> str:
    if not os.path.exists(PROFILE_PATH):
        return ""
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return f.read()


def _materials_images(materials_dir: Path) -> list[Path]:
    if not materials_dir.exists():
        return []
    return sorted(p for p in materials_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)


def _save(job_id: str, name: str, text: str) -> str:
    job_dir = os.path.join(COVER_LETTERS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _verdict(evaluation: str) -> str:
    first_line = evaluation.strip().splitlines()[0].strip().upper() if evaluation.strip() else ""
    return "NEEDS_REVISION" if "NEEDS_REVISION" in first_line else "OK"


def run_for_job(job_id: str, job_text: str) -> dict:
    """공고 하나에 대해 계획 → 계획평가 → (필요 시 계획 재작성) → 작성 → 초안평가를
    실행하고, 각 단계 결과를 output/cover_letters/<id>/에 저장한다."""
    profile = load_profile()
    materials_dir = Path(COVER_LETTERS_DIR) / job_id / "materials"
    images = _materials_images(materials_dir)

    planner = get_provider(config.PROVIDER_PLANNER)
    plan_evaluator = get_provider(config.PROVIDER_PLAN_EVALUATOR)
    writer = get_provider(config.PROVIDER_WRITER)
    draft_evaluator = get_provider(config.PROVIDER_DRAFT_EVALUATOR)

    system, user = prompts.planner_prompt(job_text, profile, materials_dir)
    plan = planner.run(system, user, images=images)
    _save(job_id, "plan.md", plan)

    system, user = prompts.plan_evaluator_prompt(job_text, plan)
    plan_review = plan_evaluator.run(system, user)
    _save(job_id, "plan_review.md", plan_review)

    if _verdict(plan_review) == "NEEDS_REVISION":
        system, user = prompts.planner_revision_prompt(
            job_text, profile, materials_dir, plan, plan_review
        )
        plan = planner.run(system, user, images=images)
        _save(job_id, "plan.md", plan)

    system, user = prompts.writer_prompt(job_text, profile, plan)
    draft = writer.run(system, user)
    _save(job_id, "draft.md", draft)

    system, user = prompts.draft_evaluator_prompt(job_text, draft)
    draft_review = draft_evaluator.run(system, user)
    _save(job_id, "draft_review.md", draft_review)

    return {
        "id": job_id,
        "plan": plan,
        "plan_review": plan_review,
        "draft": draft,
        "draft_review": draft_review,
    }
