from __future__ import annotations

import jobfind.dart as dart


def test_normalize_company_name_strips_legal_entity_tokens():
    assert dart._normalize_company_name("(주)블루엠텍") == "블루엠텍"
    assert dart._normalize_company_name("㈜블루엠텍") == "블루엠텍"
    assert dart._normalize_company_name("주식회사블루엠텍") == "블루엠텍"
    assert dart._normalize_company_name("블루엠텍") == "블루엠텍"


def test_find_corp_code_matches_after_normalization(monkeypatch):
    monkeypatch.setattr(dart, "_load_corp_codes", lambda api_key: {"블루엠텍": "00123456"})
    assert dart.find_corp_code("(주)블루엠텍", "key") == "00123456"


def test_find_corp_code_no_match_returns_none(monkeypatch):
    monkeypatch.setattr(dart, "_load_corp_codes", lambda api_key: {"블루엠텍": "00123456"})
    assert dart.find_corp_code("전혀다른회사", "key") is None


def test_find_corp_code_empty_name_returns_none(monkeypatch):
    monkeypatch.setattr(dart, "_load_corp_codes", lambda api_key: {"블루엠텍": "00123456"})
    assert dart.find_corp_code("", "key") is None


def test_format_company_profile_includes_available_fields():
    data = {
        "ceo_nm": "홍길동",
        "est_dt": "20100101",
        "corp_cls": "K",
        "adres": "서울시 강남구",
        "hm_url": "example.com",
    }
    text = dart.format_company_profile(data)
    assert "[DART 기업개황]" in text
    assert "대표자: 홍길동" in text
    assert "설립일: 20100101" in text
    assert "코스닥 상장" in text
    assert "서울시 강남구" in text
    assert "example.com" in text


def test_format_company_profile_empty_when_no_fields():
    assert dart.format_company_profile({}) == ""


def test_fetch_company_profile_no_api_key_returns_empty(monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    assert dart.fetch_company_profile("블루엠텍") == ""


def test_fetch_company_profile_no_company_name_returns_empty(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "key")
    assert dart.fetch_company_profile("") == ""


def test_fetch_company_profile_unmatched_company_returns_empty(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "key")
    monkeypatch.setattr(dart, "find_corp_code", lambda name, api_key: None)
    assert dart.fetch_company_profile("모르는회사") == ""


def test_fetch_company_profile_success(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "key")
    monkeypatch.setattr(dart, "find_corp_code", lambda name, api_key: "00123456")

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "000", "ceo_nm": "홍길동", "corp_cls": "Y"}

    monkeypatch.setattr(dart.requests, "get", lambda url, params, timeout: _FakeResponse())

    text = dart.fetch_company_profile("(주)블루엠텍")
    assert "대표자: 홍길동" in text
    assert "유가증권시장 상장" in text


def test_fetch_company_profile_bad_status_returns_empty(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "key")
    monkeypatch.setattr(dart, "find_corp_code", lambda name, api_key: "00123456")

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "013", "message": "조회된 데이터가 없습니다."}

    monkeypatch.setattr(dart.requests, "get", lambda url, params, timeout: _FakeResponse())
    assert dart.fetch_company_profile("(주)블루엠텍") == ""


def test_fetch_company_profile_network_error_returns_empty(monkeypatch):
    import requests as requests_module

    monkeypatch.setenv("DART_API_KEY", "key")
    monkeypatch.setattr(dart, "find_corp_code", lambda name, api_key: "00123456")

    def raise_error(url, params, timeout):
        raise requests_module.RequestException("boom")

    monkeypatch.setattr(dart.requests, "get", raise_error)
    assert dart.fetch_company_profile("(주)블루엠텍") == ""
