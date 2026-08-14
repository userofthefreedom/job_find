from __future__ import annotations
import configparser
from types import SimpleNamespace

CONFIG_PATH = "config.ini"


def _parse_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def load_config(path: str) -> SimpleNamespace:
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    career_type = parser.get("filter", "career_type", fallback="").strip()
    threshold_raw = parser.get("relevance", "threshold", fallback="0.5").strip()
    return SimpleNamespace(
        KEYWORDS=_parse_list(parser.get("filter", "keywords", fallback="")),
        LOCATIONS=_parse_list(parser.get("filter", "locations", fallback="")),
        CAREER_TYPE=career_type or None,
        EXP_MIN=_parse_optional_int(parser.get("filter", "exp_min", fallback="")),
        EXP_MAX=_parse_optional_int(parser.get("filter", "exp_max", fallback="")),
        EXCLUDE_KEYWORDS=_parse_list(parser.get("filter", "exclude_keywords", fallback="")),
        ROLE_DESCRIPTION=parser.get("relevance", "role_description", fallback="").strip(),
        RELEVANCE_MODEL=parser.get(
            "relevance", "model", fallback="jhgan/ko-sroberta-multitask"
        ).strip(),
        RELEVANCE_THRESHOLD=float(threshold_raw) if threshold_raw else 0.5,
    )


config = load_config(CONFIG_PATH)
