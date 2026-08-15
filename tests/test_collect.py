from __future__ import annotations
import os
import tempfile

import jobfind.cli as cli


def _job(job_id, title="백엔드 개발자"):
    return {
        "id": job_id, "source": "사람인", "company": "테스트", "title": title,
        "location": "서울", "job_type": "", "experience": "경력무관", "keyword": "",
        "url": "https://example.com", "deadline": "",
    }


def _run_collect(monkeypatch, tmpdir, fetch_result, filtered=None):
    jobs_path = os.path.join(tmpdir, "jobs_all.txt")
    dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
    run_log_path = os.path.join(tmpdir, "run_log.txt")
    monkeypatch.setattr(cli, "JOBS_PATH", jobs_path)
    monkeypatch.setattr(cli, "DISMISSED_PATH", dismissed_path)
    monkeypatch.setattr(cli, "RUN_LOG_PATH", run_log_path)
    monkeypatch.setattr(cli, "fetch_all", lambda: fetch_result)
    jobs = fetch_result[0]
    monkeypatch.setattr(cli, "filter_jobs", lambda js: filtered if filtered is not None else js)

    cli.collect()
    return run_log_path


def test_collect_no_warnings_on_normal_run(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        run_log_path = _run_collect(monkeypatch, tmpdir, ([_job("saramin_1")], False, False, False))
        out = capsys.readouterr().out
        assert "[경고]" not in out
        assert "[경고]" not in open(run_log_path, encoding="utf-8").read()


def test_collect_warns_on_saramin_failure(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        run_log_path = _run_collect(monkeypatch, tmpdir, ([], True, False, False))
        out = capsys.readouterr().out
        assert "[경고]" in out
        assert "사람인 소스 전체 실패" in out
        assert "사람인 소스 전체 실패" in open(run_log_path, encoding="utf-8").read()


def test_collect_warns_on_wanted_failure(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_collect(monkeypatch, tmpdir, ([], False, True, False))
        assert "원티드 소스 전체 실패" in capsys.readouterr().out


def test_collect_warns_on_page_cap_hit(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_collect(monkeypatch, tmpdir, ([], False, False, True))
        assert "페이지 상한" in capsys.readouterr().out


def test_collect_appends_to_run_log_across_runs(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        run_log_path = _run_collect(monkeypatch, tmpdir, ([], False, False, False))
        _run_collect(monkeypatch, tmpdir, ([], False, False, False))
        lines = open(run_log_path, encoding="utf-8").read().splitlines()
        assert len(lines) == 2
