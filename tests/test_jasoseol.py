from __future__ import annotations

from jobfind.collectors.jasoseol import (
    fetch_jasoseol_all,
    fetch_jasoseol_calendar,
    fetch_jasoseol_detail,
    normalize_jasoseol,
)


class _FakeResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status = status

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


_EVENT = {
    "id": 105532,
    "title": "2026년 8월 신입/경력 채용",
    "company_group": {"name": "안랩"},
    "start_time": "2026-06-17T00:00:00.000+09:00",
    "end_time": "2026-08-14T11:32:41.000+09:00",
}

_DETAIL = {
    "employments": [
        {"field": "IT 인프라 운영(M365)", "self_introduction_type": "고정질문"},
        {"field": "SCM", "self_introduction_type": "고정질문"},
        {"field": "원격 관제", "self_introduction_type": "자율질문"},
    ]
}


# ── normalize_jasoseol ───────────────────────────────────────────────────────

def test_normalize_jasoseol_basic():
    job = normalize_jasoseol(_EVENT, _DETAIL)
    assert job is not None
    assert job["id"] == "jasoseol_105532"
    assert job["source"] == "자소설닷컴"
    assert job["company"] == "안랩"
    assert job["title"] == "2026년 8월 신입/경력 채용"
    assert job["location"] == ""
    assert job["experience"] == ""
    assert "IT 인프라 운영(M365)" in job["keyword"]
    assert "SCM" in job["keyword"]
    assert "원격 관제" in job["keyword"]
    assert job["url"] == "https://jasoseol.com/recruit?ec=105532"
    assert job["deadline"] == "2026-08-14"


def test_normalize_jasoseol_only_fixed_question_roles_flagged():
    job = normalize_jasoseol(_EVENT, _DETAIL)
    assert set(job["essay_roles"]) == {"IT 인프라 운영(M365)", "SCM"}


def test_normalize_jasoseol_no_essay_roles_key_when_none_fixed():
    detail = {"employments": [{"field": "원격 관제", "self_introduction_type": "자율질문"}]}
    job = normalize_jasoseol(_EVENT, detail)
    assert "essay_roles" not in job


def test_normalize_jasoseol_missing_detail_still_returns_job():
    job = normalize_jasoseol(_EVENT, None)
    assert job is not None
    assert job["keyword"] == ""
    assert "essay_roles" not in job


def test_normalize_jasoseol_missing_company_returns_none():
    event = {**_EVENT, "company_group": {"name": ""}}
    assert normalize_jasoseol(event, _DETAIL) is None


def test_normalize_jasoseol_missing_key_returns_none():
    assert normalize_jasoseol({"id": 1}, None) is None


# ── fetch_jasoseol_calendar ───────────────────────────────────────────────────

def test_fetch_jasoseol_calendar_returns_employment_list(monkeypatch):
    import jobfind.collectors.jasoseol as mod

    monkeypatch.setattr(
        mod.requests, "post",
        lambda *a, **kw: _FakeResponse({"employment": [_EVENT]}),
    )
    result = fetch_jasoseol_calendar("2026-08-01", "2026-08-31")
    assert result == [_EVENT]


def test_fetch_jasoseol_calendar_request_failure_returns_none(monkeypatch):
    import jobfind.collectors.jasoseol as mod
    import requests

    def _raise(*a, **kw):
        raise requests.RequestException("boom")

    monkeypatch.setattr(mod.requests, "post", _raise)
    assert fetch_jasoseol_calendar("2026-08-01", "2026-08-31") is None


# ── fetch_jasoseol_detail ─────────────────────────────────────────────────────

def test_fetch_jasoseol_detail_returns_json(monkeypatch):
    import jobfind.collectors.jasoseol as mod

    monkeypatch.setattr(mod.requests, "get", lambda *a, **kw: _FakeResponse(_DETAIL))
    assert fetch_jasoseol_detail(105532) == _DETAIL


def test_fetch_jasoseol_detail_request_failure_returns_none(monkeypatch):
    import jobfind.collectors.jasoseol as mod
    import requests

    def _raise(*a, **kw):
        raise requests.RequestException("boom")

    monkeypatch.setattr(mod.requests, "get", _raise)
    assert fetch_jasoseol_detail(105532) is None


# ── fetch_jasoseol_all (Phase 23: 신규 회사만 상세조회) ─────────────────────

def test_fetch_jasoseol_all_skips_detail_fetch_for_known_ids(monkeypatch):
    import jobfind.collectors.jasoseol as mod

    monkeypatch.setattr(mod, "fetch_jasoseol_calendar", lambda start, end: [_EVENT])
    calls = []
    monkeypatch.setattr(
        mod, "fetch_jasoseol_detail",
        lambda ec_id: calls.append(ec_id) or _DETAIL,
    )

    jobs, failed = fetch_jasoseol_all({"jasoseol_105532"})

    assert jobs == []
    assert failed is False
    assert calls == []  # 이미 아는 회사라 상세조회 자체가 발생하지 않음


def test_fetch_jasoseol_all_fetches_detail_for_new_ids(monkeypatch):
    import jobfind.collectors.jasoseol as mod

    monkeypatch.setattr(mod, "fetch_jasoseol_calendar", lambda start, end: [_EVENT])
    calls = []
    monkeypatch.setattr(
        mod, "fetch_jasoseol_detail",
        lambda ec_id: calls.append(ec_id) or _DETAIL,
    )

    jobs, failed = fetch_jasoseol_all(set())

    assert len(jobs) == 1
    assert jobs[0]["id"] == "jasoseol_105532"
    assert calls == [105532]


def test_fetch_jasoseol_all_calendar_failure_reports_request_failed(monkeypatch):
    import jobfind.collectors.jasoseol as mod

    monkeypatch.setattr(mod, "fetch_jasoseol_calendar", lambda start, end: None)

    jobs, failed = fetch_jasoseol_all(set())

    assert jobs == []
    assert failed is True
