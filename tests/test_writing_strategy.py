from __future__ import annotations

from jobfind.pipeline.writing_strategy import (
    WRITING_STRATEGY,
    WRITING_STRATEGY_EVALUATION_NOTE,
)


def test_writing_strategy_covers_core_sections():
    for marker in ["[두괄식]", "[STAR", "[지원동기", "[경험-직무 연결]", "[클리셰 회피]", "[약점]", "[입사 후 포부]"]:
        assert marker in WRITING_STRATEGY

def test_writing_strategy_flags_self_centered_motivation():
    assert "안정적인 직장" in WRITING_STRATEGY
    assert "평생 다닐 회사" in WRITING_STRATEGY

def test_writing_strategy_lists_common_cliches():
    for cliche in ["열정", "책임감이 강하다", "최선을 다하겠습니다"]:
        assert cliche in WRITING_STRATEGY

def test_evaluation_note_instructs_needs_revision_on_violation():
    assert "NEEDS_REVISION" in WRITING_STRATEGY_EVALUATION_NOTE
