from __future__ import annotations
from pathlib import Path


def _read_notes(materials_dir: Path) -> str:
    notes_path = materials_dir / "notes.md"
    if notes_path.exists():
        return notes_path.read_text(encoding="utf-8")
    return ""


def planner_prompt(job_text: str, profile: str, materials_dir: Path) -> tuple[str, str]:
    system = (
        "너는 채용 공고에 맞춘 자기소개서 작성 계획을 세우는 전문가다. "
        "지원자의 프로필에서 이 공고와 가장 관련 있는 경험을 골라, 자소서에 어떤 순서로 "
        "무엇을 강조할지 구체적인 개요(outline)를 만든다. 아직 실제 문장을 쓰지 않는다."
    )
    user = f"[공고 정보]\n{job_text}\n\n[지원자 프로필]\n{profile}\n\n"
    notes = _read_notes(materials_dir)
    if notes:
        user += f"[추가 메모]\n{notes}\n\n"
    user += "위 정보를 바탕으로 이 공고에 지원할 자소서의 작성 계획(개요)을 세워라."
    return system, user


def planner_revision_prompt(
    job_text: str, profile: str, materials_dir: Path, previous_plan: str, feedback: str
) -> tuple[str, str]:
    system = (
        "너는 채용 공고에 맞춘 자기소개서 작성 계획을 세우는 전문가다. "
        "이전에 세운 계획에 대한 평가 피드백을 반영해 계획을 개선한다."
    )
    user = f"[공고 정보]\n{job_text}\n\n[지원자 프로필]\n{profile}\n\n"
    notes = _read_notes(materials_dir)
    if notes:
        user += f"[추가 메모]\n{notes}\n\n"
    user += (
        f"[이전 계획]\n{previous_plan}\n\n"
        f"[평가 피드백]\n{feedback}\n\n"
        "위 피드백을 반영해 개선된 계획을 다시 작성하라."
    )
    return system, user


def plan_evaluator_prompt(job_text: str, plan: str) -> tuple[str, str]:
    system = (
        "너는 자소서 작성 계획을 냉정하게 검토하는 평가자다. 계획 작성자와는 독립적으로 "
        "판단한다. 계획이 공고 요구사항과 잘 맞는지, 진부하거나 추상적이지 않은지 확인하라. "
        "첫 줄에 정확히 'OK' 또는 'NEEDS_REVISION' 중 하나만 쓰고, 그 아래에 구체적인 "
        "수정 제안을 적어라."
    )
    user = f"[공고 정보]\n{job_text}\n\n[작성 계획]\n{plan}\n\n이 계획을 평가하라."
    return system, user


def writer_prompt(job_text: str, profile: str, plan: str) -> tuple[str, str]:
    system = (
        "너는 자기소개서를 실제로 작성하는 전문 라이터다. 주어진 계획을 바탕으로 "
        "지원자의 실제 경험만 사용해 자연스러운 한국어 자소서 초안을 작성한다. "
        "과장하거나 없는 경험을 지어내지 않는다."
    )
    user = (
        f"[공고 정보]\n{job_text}\n\n"
        f"[지원자 프로필]\n{profile}\n\n"
        f"[작성 계획]\n{plan}\n\n"
        "위 계획에 따라 자소서 초안을 작성하라."
    )
    return system, user


def draft_evaluator_prompt(job_text: str, draft: str) -> tuple[str, str]:
    system = (
        "너는 자소서 초안을 냉정하게 검토하는 평가자다. 작성자와는 독립적으로 판단한다. "
        "진부한 표현, 공고와의 연관성 부족, 논리적 비약을 짚어내고 구체적인 수정 방안을 "
        "제시하라."
    )
    user = f"[공고 정보]\n{job_text}\n\n[자소서 초안]\n{draft}\n\n이 초안을 평가하라."
    return system, user
