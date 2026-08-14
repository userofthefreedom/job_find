from __future__ import annotations
import os
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()


def _parse_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def load_config() -> SimpleNamespace:
    career_type = os.environ.get("FILTER_CAREER_TYPE", "").strip()
    top_n_raw = os.environ.get("RELEVANCE_TOP_N", "20").strip()
    return SimpleNamespace(
        KEYWORDS=_parse_list(os.environ.get("FILTER_KEYWORDS", "")),
        LOCATIONS=_parse_list(os.environ.get("FILTER_LOCATIONS", "")),
        CAREER_TYPE=career_type or None,
        EXP_MIN=_parse_optional_int(os.environ.get("FILTER_EXP_MIN", "")),
        EXP_MAX=_parse_optional_int(os.environ.get("FILTER_EXP_MAX", "")),
        EXCLUDE_KEYWORDS=_parse_list(os.environ.get("FILTER_EXCLUDE_KEYWORDS", "")),
        RELEVANCE_ROLES=os.environ.get("RELEVANCE_ROLES", "").strip(),
        RELEVANCE_DOMAINS=os.environ.get("RELEVANCE_DOMAINS", "").strip(),
        RELEVANCE_MODEL=os.environ.get(
            "RELEVANCE_MODEL", "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
        ).strip(),
        RELEVANCE_TOP_N=int(top_n_raw) if top_n_raw else 20,
        PROVIDER_PLANNER=os.environ.get("PROVIDER_PLANNER", "claude_cli").strip(),
        PROVIDER_PLAN_EVALUATOR=os.environ.get(
            "PROVIDER_PLAN_EVALUATOR", "claude_cli"
        ).strip(),
        PROVIDER_WRITER=os.environ.get("PROVIDER_WRITER", "claude_cli").strip(),
        PROVIDER_DRAFT_EVALUATOR=os.environ.get(
            "PROVIDER_DRAFT_EVALUATOR", "claude_cli"
        ).strip(),
    )


config = load_config()
