from __future__ import annotations

from jobfind.pipeline.prompts import (
    draft_evaluator_prompt,
    plan_evaluator_prompt,
    planner_prompt,
    planner_revision_prompt,
    writer_prompt,
    writer_revision_prompt,
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

def test_planner_prompt_labels_notes_as_priority_question_source(tmp_path):
    (tmp_path / "notes.md").write_text("1. 지원동기를 작성하시오 (500자 이내)", encoding="utf-8")
    _, user = planner_prompt("공고", "프로필", tmp_path)
    assert "최우선으로 따를 것" in user

def test_planner_prompt_omits_notes_section_when_absent(tmp_path):
    _, user = planner_prompt("공고", "프로필", tmp_path)
    assert "최우선으로 따를 것" not in user

def test_planner_prompt_instructs_to_follow_real_questions_when_present(tmp_path):
    system, _ = planner_prompt("공고", "프로필", tmp_path)
    assert "그대로 따라 계획을 세우고" in system

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

def test_writer_prompt_prioritizes_plan_question_structure_over_standard_assumption():
    system, _ = writer_prompt("공고", "프로필", "계획")
    assert "계획에 이미 실제 문항 기반 구성" in system
    assert "그런 정보가 없을 때만 가장 흔한 표준 구성" in system

def test_planner_revision_prompt_labels_notes_as_priority_question_source(tmp_path):
    (tmp_path / "notes.md").write_text("1. 성장과정을 작성하시오", encoding="utf-8")
    _, user = planner_revision_prompt("공고", "프로필", tmp_path, "이전 계획", "피드백")
    assert "최우선으로 따를 것" in user

def test_draft_evaluator_prompt_includes_draft():
    system, user = draft_evaluator_prompt("공고", "초안 내용")
    assert "초안 내용" in user
    assert "평가" in system

def test_draft_evaluator_prompt_instructs_verdict_format():
    system, _ = draft_evaluator_prompt("공고", "초안 내용")
    assert "OK" in system and "NEEDS_REVISION" in system

def test_writer_revision_prompt_includes_previous_draft_and_feedback():
    _, user = writer_revision_prompt("공고", "프로필", "계획 내용", "이전 초안 내용", "피드백 내용")
    assert "이전 초안 내용" in user
    assert "피드백 내용" in user
    assert "계획 내용" in user

def test_style_principles_present_in_all_cover_letter_prompts(tmp_path):
    marker = "최대 1회"
    assert marker in planner_prompt("공고", "프로필", tmp_path)[0]
    assert marker in planner_revision_prompt("공고", "프로필", tmp_path, "이전 계획", "피드백")[0]
    assert marker in plan_evaluator_prompt("공고", "계획")[0]
    assert marker in writer_prompt("공고", "프로필", "계획")[0]
    assert marker in draft_evaluator_prompt("공고", "초안")[0]
    assert marker in writer_revision_prompt("공고", "프로필", "계획", "초안", "피드백")[0]


# ── 자소서 작성 전략 (Phase 21) ────────────────────────────────────────────

def test_writing_strategy_present_in_all_cover_letter_prompts(tmp_path):
    marker = "[두괄식]"
    assert marker in planner_prompt("공고", "프로필", tmp_path)[0]
    assert marker in planner_revision_prompt("공고", "프로필", tmp_path, "이전 계획", "피드백")[0]
    assert marker in plan_evaluator_prompt("공고", "계획")[0]
    assert marker in writer_prompt("공고", "프로필", "계획")[0]
    assert marker in draft_evaluator_prompt("공고", "초안")[0]
    assert marker in writer_revision_prompt("공고", "프로필", "계획", "초안", "피드백")[0]

def test_writing_strategy_warns_against_generic_motivation(tmp_path):
    system, _ = planner_prompt("공고", "프로필", tmp_path)
    assert "안정적인 직장" in system

def test_style_principles_warns_against_precise_unverified_numbers(tmp_path):
    # 실사용 e2e 검증(Phase 21)에서 확인된 문제 — 헤지 어조를 붙여도 비상장 기업의
    # 소수점 단위 매출 성장률처럼 정밀한 미확인 수치는 그 자체로 위험 신호였다.
    system, _ = planner_prompt("공고", "프로필", tmp_path)
    assert "소수점 단위" in system

def test_evaluation_note_only_in_evaluator_prompts(tmp_path):
    note_marker = "명백한 위반이므로"
    assert note_marker in plan_evaluator_prompt("공고", "계획")[0]
    assert note_marker in draft_evaluator_prompt("공고", "초안")[0]
    assert note_marker not in planner_prompt("공고", "프로필", tmp_path)[0]
    assert note_marker not in writer_prompt("공고", "프로필", "계획")[0]
