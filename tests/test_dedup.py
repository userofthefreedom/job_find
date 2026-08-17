from __future__ import annotations

import jobfind.dedup as dedup_mod
from jobfind.dedup import _norm_title, deduplicate_cross_platform, fetch_all


def _job(source, title, deadline="2026-08-31", location="서울", job_id="x"):
    return {"id": job_id, "source": source, "title": title,
            "deadline": deadline, "location": location}

def test_dedup_removes_exact_title_same_deadline():
    s = [_job("사람인", "Python 백엔드 개발자", job_id="saramin_1")]
    w = [_job("원티드", "Python 백엔드 개발자", job_id="wanted_1")]
    result = deduplicate_cross_platform(s, w)
    ids = [j["id"] for j in result]
    assert "saramin_1" in ids
    assert "wanted_1" not in ids

def test_dedup_keeps_different_job():
    s = [_job("사람인", "Python 백엔드 개발자", job_id="saramin_1")]
    w = [_job("원티드", "Java 백엔드 개발자", job_id="wanted_2")]
    result = deduplicate_cross_platform(s, w)
    assert len(result) == 2

def test_dedup_keeps_if_different_deadline_and_location():
    s = [_job("사람인", "Python 백엔드 개발자", deadline="2026-08-31", location="서울", job_id="saramin_1")]
    w = [_job("원티드", "Python 백엔드 개발자", deadline="2026-09-30", location="부산", job_id="wanted_1")]
    result = deduplicate_cross_platform(s, w)
    assert len(result) == 2

def test_norm_title_strips_spaces_and_lowercases():
    assert _norm_title("Python 백엔드  개발자") == "python백엔드개발자"


# ── fetch_all (Phase 5: 소스별 실패/상한 신호 전달, Phase 23: 자소설닷컴 추가) ──

def test_fetch_all_propagates_failure_and_cap_signals(monkeypatch):
    s = [_job("사람인", "백엔드 개발자", job_id="saramin_1")]
    w = [_job("원티드", "프론트엔드 개발자", job_id="wanted_1")]
    monkeypatch.setattr(dedup_mod, "fetch_saramin_all", lambda: (s, True, True))
    monkeypatch.setattr(dedup_mod, "fetch_wanted_all", lambda: (w, False))
    monkeypatch.setattr(dedup_mod, "fetch_jasoseol_all", lambda skip_ids: ([], True))

    jobs, saramin_failed, wanted_failed, page_cap_hit, jasoseol_failed = fetch_all(set())

    ids = [j["id"] for j in jobs]
    assert "saramin_1" in ids and "wanted_1" in ids
    assert saramin_failed is True
    assert wanted_failed is False
    assert page_cap_hit is True
    assert jasoseol_failed is True


def test_fetch_all_no_warnings_on_normal_run(monkeypatch):
    monkeypatch.setattr(dedup_mod, "fetch_saramin_all", lambda: ([], False, False))
    monkeypatch.setattr(dedup_mod, "fetch_wanted_all", lambda: ([], False))
    monkeypatch.setattr(dedup_mod, "fetch_jasoseol_all", lambda skip_ids: ([], False))

    jobs, saramin_failed, wanted_failed, page_cap_hit, jasoseol_failed = fetch_all(set())

    assert jobs == []
    assert (saramin_failed, wanted_failed, page_cap_hit, jasoseol_failed) == (False, False, False, False)


def test_fetch_all_includes_jasoseol_jobs_without_cross_dedup(monkeypatch):
    j = [_job("자소설닷컴", "2026년 신입/경력 채용", job_id="jasoseol_1")]
    monkeypatch.setattr(dedup_mod, "fetch_saramin_all", lambda: ([], False, False))
    monkeypatch.setattr(dedup_mod, "fetch_wanted_all", lambda: ([], False))
    monkeypatch.setattr(dedup_mod, "fetch_jasoseol_all", lambda skip_ids: (j, False))

    jobs, *_ = fetch_all(set())

    assert [job["id"] for job in jobs] == ["jasoseol_1"]


def test_fetch_all_passes_skip_ids_to_jasoseol(monkeypatch):
    received = {}
    monkeypatch.setattr(dedup_mod, "fetch_saramin_all", lambda: ([], False, False))
    monkeypatch.setattr(dedup_mod, "fetch_wanted_all", lambda: ([], False))

    def fake_jasoseol(skip_ids):
        received["skip_ids"] = skip_ids
        return [], False

    monkeypatch.setattr(dedup_mod, "fetch_jasoseol_all", fake_jasoseol)

    fetch_all({"jasoseol_1"})

    assert received["skip_ids"] == {"jasoseol_1"}
