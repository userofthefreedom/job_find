from __future__ import annotations

from jobfind.dedup import _norm_title, deduplicate_cross_platform


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
