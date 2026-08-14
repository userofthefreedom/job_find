from __future__ import annotations

from jobfind.config import _parse_list, _parse_optional_int, load_config


def test_parse_list_splits_and_strips():
    assert _parse_list(" Python ,  백엔드,") == ["Python", "백엔드"]

def test_parse_list_empty_string():
    assert _parse_list("") == []

def test_parse_optional_int_blank_is_none():
    assert _parse_optional_int("  ") is None

def test_parse_optional_int_parses_value():
    assert _parse_optional_int(" 5 ") == 5

def test_load_config_reads_ini(tmp_path):
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[filter]\n"
        "keywords = Python, 백엔드\n"
        "locations = 서울\n"
        "career_type = 경력\n"
        "exp_min = 1\n"
        "exp_max = 5\n"
        "exclude_keywords = 교육생\n",
        encoding="utf-8",
    )
    cfg = load_config(str(ini))
    assert cfg.KEYWORDS == ["Python", "백엔드"]
    assert cfg.LOCATIONS == ["서울"]
    assert cfg.CAREER_TYPE == "경력"
    assert cfg.EXP_MIN == 1
    assert cfg.EXP_MAX == 5
    assert cfg.EXCLUDE_KEYWORDS == ["교육생"]

def test_load_config_blank_fields_allow_all(tmp_path):
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[filter]\n"
        "keywords =\n"
        "locations =\n"
        "career_type =\n"
        "exp_min =\n"
        "exp_max =\n"
        "exclude_keywords =\n",
        encoding="utf-8",
    )
    cfg = load_config(str(ini))
    assert cfg.KEYWORDS == []
    assert cfg.LOCATIONS == []
    assert cfg.CAREER_TYPE is None
    assert cfg.EXP_MIN is None
    assert cfg.EXP_MAX is None
    assert cfg.EXCLUDE_KEYWORDS == []

def test_load_config_missing_file_allows_all():
    cfg = load_config("nonexistent_config.ini")
    assert cfg.KEYWORDS == []
    assert cfg.CAREER_TYPE is None

def test_load_config_providers_defaults_to_claude_cli():
    cfg = load_config("nonexistent_config.ini")
    assert cfg.PROVIDER_PLANNER == "claude_cli"
    assert cfg.PROVIDER_PLAN_EVALUATOR == "claude_cli"
    assert cfg.PROVIDER_WRITER == "claude_cli"
    assert cfg.PROVIDER_DRAFT_EVALUATOR == "claude_cli"

def test_load_config_providers_reads_ini(tmp_path):
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[providers]\n"
        "planner = codex_cli\n"
        "plan_evaluator = api:anthropic\n"
        "writer = claude_cli\n"
        "draft_evaluator = api:openai\n",
        encoding="utf-8",
    )
    cfg = load_config(str(ini))
    assert cfg.PROVIDER_PLANNER == "codex_cli"
    assert cfg.PROVIDER_PLAN_EVALUATOR == "api:anthropic"
    assert cfg.PROVIDER_WRITER == "claude_cli"
    assert cfg.PROVIDER_DRAFT_EVALUATOR == "api:openai"
