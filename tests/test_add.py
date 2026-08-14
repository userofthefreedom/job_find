from __future__ import annotations
import os
import tempfile

import jobfind.cli as cli
from jobfind.cli import _parse_manual_url, add_job


# ── _parse_manual_url ─────────────────────────────────────────────────────────

def test_parse_manual_url_saramin():
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=54736780"
    assert _parse_manual_url(url) == ("saramin", "54736780")

def test_parse_manual_url_wanted():
    url = "https://www.wanted.co.kr/wd/380759"
    assert _parse_manual_url(url) == ("wanted", "380759")

def test_parse_manual_url_unsupported():
    assert _parse_manual_url("https://example.com/jobs/123") is None


# ── add_job ────────────────────────────────────────────────────────────────────

_JOB = {
    "id": "saramin_999",
    "source": "사람인",
    "company": "테스트컴퍼니",
    "title": "백엔드 개발자",
    "location": "서울",
    "job_type": "",
    "experience": "경력무관",
    "keyword": "",
    "url": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999",
    "deadline": "",
}


def test_add_job_unsupported_url(monkeypatch, capsys):
    add_job("https://example.com/jobs/123")
    assert "지원하지 않는 URL" in capsys.readouterr().out


def test_add_job_writes_new_job(monkeypatch, capsys):
    monkeypatch.setattr(cli, "fetch_saramin_detail", lambda job_id: _JOB)
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        monkeypatch.setattr(cli, "JOBS_PATH", jobs_path)
        monkeypatch.setattr(cli, "DISMISSED_PATH", dismissed_path)

        add_job("https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999")

        assert "saramin_999" in open(jobs_path, encoding="utf-8").read()
        assert "공고 추가됨" in capsys.readouterr().out


def test_add_job_skips_duplicate(monkeypatch, capsys):
    monkeypatch.setattr(cli, "fetch_saramin_detail", lambda job_id: _JOB)
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        monkeypatch.setattr(cli, "JOBS_PATH", jobs_path)
        monkeypatch.setattr(cli, "DISMISSED_PATH", dismissed_path)

        add_job("https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999")
        capsys.readouterr()
        add_job("https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999")

        assert "이미 목록에 있는 공고" in capsys.readouterr().out
        content = open(jobs_path, encoding="utf-8").read()
        assert content.count("saramin_999") == 1


def test_add_job_fetch_failure(monkeypatch, capsys):
    monkeypatch.setattr(cli, "fetch_saramin_detail", lambda job_id: None)
    add_job("https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999")
    assert "가져오지 못했습니다" in capsys.readouterr().out
