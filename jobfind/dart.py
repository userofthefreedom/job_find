from __future__ import annotations
import io
import json
import os
import time
import zipfile
from xml.etree import ElementTree

import requests

_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
_COMPANY_URL = "https://opendart.fss.or.kr/api/company.json"
_CACHE_PATH = "output/.dart_corp_codes.json"
_CACHE_MAX_AGE = 7 * 24 * 3600  # 7일 — corpCode.xml은 전체 상장·등록기업 목록이라 자주 안 바뀜
_MARKET_LABELS = {
    "Y": "유가증권시장 상장",
    "K": "코스닥 상장",
    "N": "코넥스 상장",
    "E": "기타(비상장 등)",
}


def _api_key() -> str:
    return os.environ.get("DART_API_KEY", "").strip()


def _download_corp_codes(api_key: str) -> dict[str, str]:
    resp = requests.get(_CORP_CODE_URL, params={"crtfc_key": api_key}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_bytes = zf.read(zf.namelist()[0])
    root = ElementTree.fromstring(xml_bytes)
    codes: dict[str, str] = {}
    for el in root.findall("list"):
        name = (el.findtext("corp_name") or "").strip()
        code = (el.findtext("corp_code") or "").strip()
        if name and code:
            codes[name] = code
    return codes


def _load_corp_codes(api_key: str) -> dict[str, str]:
    if os.path.exists(_CACHE_PATH) and time.time() - os.path.getmtime(_CACHE_PATH) < _CACHE_MAX_AGE:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    codes = _download_corp_codes(api_key)
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False)
    return codes


def _normalize_company_name(name: str) -> str:
    for token in ("(주)", "㈜", "주식회사"):
        name = name.replace(token, "")
    return name.strip()


def find_corp_code(company_name: str, api_key: str) -> str | None:
    codes = _load_corp_codes(api_key)
    target = _normalize_company_name(company_name)
    if not target:
        return None
    for name, code in codes.items():
        if _normalize_company_name(name) == target:
            return code
    return None


def format_company_profile(data: dict) -> str:
    lines = []
    if data.get("ceo_nm"):
        lines.append(f"대표자: {data['ceo_nm']}")
    if data.get("est_dt"):
        lines.append(f"설립일: {data['est_dt']}")
    if data.get("corp_cls"):
        lines.append(f"시장 구분: {_MARKET_LABELS.get(data['corp_cls'], data['corp_cls'])}")
    if data.get("adres"):
        lines.append(f"주소: {data['adres']}")
    if data.get("hm_url"):
        lines.append(f"홈페이지: {data['hm_url']}")
    if not lines:
        return ""
    return "[DART 기업개황]\n" + "\n".join(lines)


def fetch_company_profile(company_name: str) -> str:
    """DART에 등록된 기업이면 대표자·설립일·시장구분·홈페이지 등 개황을 텍스트로 반환한다.

    DART_API_KEY가 없거나, 회사를 못 찾거나, 조회에 실패하면 빈 문자열을 반환한다 —
    비상장 스타트업 등 DART에 없는 회사가 훨씬 많으므로 실패를 정상 경로로 취급한다.
    """
    api_key = _api_key()
    if not api_key or not company_name:
        return ""
    try:
        corp_code = find_corp_code(company_name, api_key)
        if not corp_code:
            return ""
        resp = requests.get(
            _COMPANY_URL,
            params={"crtfc_key": api_key, "corp_code": corp_code},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return ""

    if data.get("status") != "000":
        return ""
    return format_company_profile(data)
