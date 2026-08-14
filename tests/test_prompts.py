from __future__ import annotations

from jobfind.pipeline.prompts import (
    draft_evaluator_prompt,
    plan_evaluator_prompt,
    planner_prompt,
    planner_revision_prompt,
    writer_prompt,
)


def test_planner_prompt_includes_job_and_profile(tmp_path):
    system, user = planner_prompt("공고 내용입니다", "내 프로필입니다", tmp_path)
    assert "공고 내용입니다" in user
    assert "내 프로필입니다" in user
    assert "계획" in system

def test_planner_prompt_includes_notes_when_present(tmp_path):
    (tmp_path / "notes.md").write_text("비공개 팀 정보", encoding="utf-8")
    _, user = planner_prompt("공고", "프로필", tmp_path)
    assert "비공개 팀 정보" in user

def test_planner_prompt_omits_notes_section_when_absent(tmp_path):
    _, user = planner_prompt("공고", "프로필", tmp_path)
    assert "[추가 메모]" not in user

def test_planner_revision_prompt_includes_previous_plan_and_feedback(tmp_path):
    _, user = planner_revision_prompt("공고", "프로필", tmp_path, "이전 계획 내용", "피드백 내용")
    assert "이전 계획 내용" in user
    assert "피드백 내용" in user

def test_plan_evaluator_prompt_instructs_verdict_format():
    system, user = plan_evaluator_prompt("공고", "계획 내용")
    assert "OK" in system and "NEEDS_REVISION" in system
    assert "계획 내용" in user

def test_writer_prompt_includes_plan_and_profile():
    _, user = writer_prompt("공고", "프로필", "계획 내용")
    assert "공고" in user
    assert "프로필" in user
    assert "계획 내용" in user

def test_writer_prompt_instructs_never_to_refuse():
    system, _ = writer_prompt("공고", "프로필", "계획")
    assert "거부하지 마라" in system

def test_draft_evaluator_prompt_includes_draft():
    system, user = draft_evaluator_prompt("공고", "초안 내용")
    assert "초안 내용" in user
    assert "평가" in system
