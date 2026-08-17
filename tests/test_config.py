from __future__ import annotations

from jobfind.config import _parse_bool, _parse_list, _parse_optional_int, load_config


def test_parse_list_splits_and_strips():
    assert _parse_list(" Python ,  백엔드,") == ["Python", "백엔드"]

def test_parse_list_empty_string():
    assert _parse_list("") == []

def test_parse_optional_int_blank_is_none():
    assert _parse_optional_int("  ") is None

def test_parse_optional_int_parses_value():
    assert _parse_optional_int(" 5 ") == 5

def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("FILTER_KEYWORDS", "Python, 백엔드")
    monkeypatch.setenv("FILTER_LOCATIONS", "서울")
    monkeypatch.setenv("FILTER_CAREER_TYPE", "경력")
    monkeypatch.setenv("FILTER_EXP_MIN", "1")
    monkeypatch.setenv("FILTER_EXP_MAX", "5")
    monkeypatch.setenv("FILTER_EXCLUDE_KEYWORDS", "교육생")
    monkeypatch.setenv("FILTER_EXCLUDE_COMPANIES", "블랙기업")
    cfg = load_config()
    assert cfg.KEYWORDS == ["Python", "백엔드"]
    assert cfg.LOCATIONS == ["서울"]
    assert cfg.CAREER_TYPE == ["경력"]
    assert cfg.EXP_MIN == 1
    assert cfg.EXP_MAX == 5
    assert cfg.EXCLUDE_KEYWORDS == ["교육생"]
    assert cfg.EXCLUDE_COMPANIES == ["블랙기업"]

def test_load_config_career_type_multi_select(monkeypatch):
    monkeypatch.setenv("FILTER_CAREER_TYPE", "신입, 경력무관")
    cfg = load_config()
    assert cfg.CAREER_TYPE == ["신입", "경력무관"]

def test_load_config_blank_fields_allow_all(monkeypatch):
    for key in [
        "FILTER_KEYWORDS", "FILTER_LOCATIONS", "FILTER_CAREER_TYPE",
        "FILTER_EXP_MIN", "FILTER_EXP_MAX", "FILTER_EXCLUDE_KEYWORDS",
        "FILTER_EXCLUDE_COMPANIES",
    ]:
        monkeypatch.setenv(key, "")
    cfg = load_config()
    assert cfg.KEYWORDS == []
    assert cfg.LOCATIONS == []
    assert cfg.CAREER_TYPE == []
    assert cfg.EXP_MIN is None
    assert cfg.EXP_MAX is None
    assert cfg.EXCLUDE_KEYWORDS == []
    assert cfg.EXCLUDE_COMPANIES == []

def test_load_config_missing_env_allows_all(monkeypatch):
    monkeypatch.delenv("FILTER_KEYWORDS", raising=False)
    monkeypatch.delenv("FILTER_CAREER_TYPE", raising=False)
    cfg = load_config()
    assert cfg.KEYWORDS == []
    assert cfg.CAREER_TYPE == []

def test_load_config_providers_defaults_to_claude_cli(monkeypatch):
    for key in [
        "PROVIDER_PLANNER", "PROVIDER_PLAN_EVALUATOR",
        "PROVIDER_WRITER", "PROVIDER_DRAFT_EVALUATOR",
    ]:
        monkeypatch.delenv(key, raising=False)
    cfg = load_config()
    assert cfg.PROVIDER_PLANNER == "claude_cli"
    assert cfg.PROVIDER_PLAN_EVALUATOR == "claude_cli"
    assert cfg.PROVIDER_WRITER == "claude_cli"
    assert cfg.PROVIDER_DRAFT_EVALUATOR == "claude_cli"

def test_load_config_providers_reads_env(monkeypatch):
    # config.py는 provider spec 값을 검증하지 않고 그대로 읽기만 한다 — 실제 유효성
    # 검사는 jobfind/providers/base.py의 get_provider()에서 한다.
    monkeypatch.setenv("PROVIDER_PLANNER", "api:anthropic")
    monkeypatch.setenv("PROVIDER_PLAN_EVALUATOR", "api:anthropic")
    monkeypatch.setenv("PROVIDER_WRITER", "claude_cli")
    monkeypatch.setenv("PROVIDER_DRAFT_EVALUATOR", "api:openai")
    cfg = load_config()
    assert cfg.PROVIDER_PLANNER == "api:anthropic"
    assert cfg.PROVIDER_PLAN_EVALUATOR == "api:anthropic"
    assert cfg.PROVIDER_WRITER == "claude_cli"
    assert cfg.PROVIDER_DRAFT_EVALUATOR == "api:openai"

def test_load_config_relevance_defaults(monkeypatch):
    for key in ["RELEVANCE_ROLES", "RELEVANCE_DOMAINS", "RELEVANCE_TOP_N", "RELEVANCE_MODEL"]:
        monkeypatch.delenv(key, raising=False)
    cfg = load_config()
    assert cfg.RELEVANCE_ROLES == ""
    assert cfg.RELEVANCE_DOMAINS == ""
    assert cfg.RELEVANCE_TOP_N == 20
    assert cfg.RELEVANCE_MODEL == "snunlp/KR-SBERT-V40K-klueNLI-augSTS"


# ── _parse_bool / JASOSEOL_ENABLED (Phase 24: on/off 토글) ──────────────────

def test_parse_bool_true_values():
    assert _parse_bool("true", default=False) is True
    assert _parse_bool("1", default=False) is True
    assert _parse_bool("yes", default=False) is True
    assert _parse_bool("TRUE", default=False) is True

def test_parse_bool_false_value():
    assert _parse_bool("false", default=True) is False

def test_parse_bool_blank_uses_default():
    assert _parse_bool("", default=True) is True
    assert _parse_bool("  ", default=False) is False

def test_load_config_jasoseol_enabled_defaults_true(monkeypatch):
    monkeypatch.delenv("JASOSEOL_ENABLED", raising=False)
    assert load_config().JASOSEOL_ENABLED is True

def test_load_config_jasoseol_enabled_can_be_disabled(monkeypatch):
    monkeypatch.setenv("JASOSEOL_ENABLED", "false")
    assert load_config().JASOSEOL_ENABLED is False
