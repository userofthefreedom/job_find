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


def _run_collect(monkeypatch, tmpdir, fetch_result, filtered=None, jobs_file_content=None):
    jobs_path = os.path.join(tmpdir, "jobs_all.txt")
    dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
    archived_path = os.path.join(tmpdir, "archived_ids.txt")
    run_log_path = os.path.join(tmpdir, "run_log.txt")
    if jobs_file_content is not None:
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(jobs_file_content)
    monkeypatch.setattr(cli, "JOBS_PATH", jobs_path)
    monkeypatch.setattr(cli, "DISMISSED_PATH", dismissed_path)
    monkeypatch.setattr(cli, "ARCHIVED_PATH", archived_path)
    monkeypatch.setattr(cli, "RUN_LOG_PATH", run_log_path)
    monkeypatch.setattr(cli, "fetch_all", lambda skip_ids: fetch_result)
    jobs = fetch_result[0]
    monkeypatch.setattr(cli, "filter_jobs", lambda js: filtered if filtered is not None else js)

    cli.collect()
    return run_log_path, jobs_path, archived_path


def test_collect_no_warnings_on_normal_run(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        run_log_path, _, _ = _run_collect(monkeypatch, tmpdir, ([_job("saramin_1")], False, False, False, False))
        out = capsys.readouterr().out
        assert "[경고]" not in out
        assert "[경고]" not in open(run_log_path, encoding="utf-8").read()


def test_collect_warns_on_saramin_failure(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        run_log_path, _, _ = _run_collect(monkeypatch, tmpdir, ([], True, False, False, False))
        out = capsys.readouterr().out
        assert "[경고]" in out
        assert "사람인 소스 전체 실패" in out
        assert "사람인 소스 전체 실패" in open(run_log_path, encoding="utf-8").read()


def test_collect_warns_on_wanted_failure(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_collect(monkeypatch, tmpdir, ([], False, True, False, False))
        assert "원티드 소스 전체 실패" in capsys.readouterr().out


def test_collect_warns_on_page_cap_hit(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_collect(monkeypatch, tmpdir, ([], False, False, True, False))
        assert "페이지 상한" in capsys.readouterr().out


def test_collect_warns_on_jasoseol_failure(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_collect(monkeypatch, tmpdir, ([], False, False, False, True))
        assert "자소설닷컴 소스 전체 실패" in capsys.readouterr().out


def test_collect_appends_to_run_log_across_runs(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        run_log_path, _, _ = _run_collect(monkeypatch, tmpdir, ([], False, False, False, False))
        _run_collect(monkeypatch, tmpdir, ([], False, False, False, False))
        lines = open(run_log_path, encoding="utf-8").read().splitlines()
        assert len(lines) == 2


# ── Phase 7: 지원 상태 추적 (collect 안에서 처리됨) ──────────────────────────

_DIVIDER = "═" * 48


def _status_block(job_id, status):
    return (
        f"{_DIVIDER}\n[ ]\n[수집일] 2026-08-15\n[출처]   사람인\n[회사]   테스트\n"
        f"[제목]   테스트 공고\n[상태] {status}\n[링크]   https://example.com\n"
        f"[ID]     {job_id}\n{_DIVIDER}\n"
    )


def test_collect_prints_status_summary(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        content = _status_block("saramin_1", "지원함") + _status_block("wanted_2", "면접")
        _run_collect(
            monkeypatch, tmpdir, ([], False, False, False, False), jobs_file_content=content,
        )
        out = capsys.readouterr().out
        assert "[지원 현황]" in out
        assert "지원함 1건" in out
        assert "면접 1건" in out


def test_collect_archives_rejected_and_excludes_from_recollection(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        content = _status_block("saramin_1", "탈락")
        run_log_path, jobs_path, archived_path = _run_collect(
            monkeypatch, tmpdir, ([_job("saramin_1")], False, False, False, False),
            jobs_file_content=content,
        )
        # 탈락 처리로 제거된 뒤, 같은 실행에서 fetch_all이 같은 ID를 다시 돌려줘도
        # archived_ids.txt 덕분에 재추가되지 않아야 한다.
        remaining = open(jobs_path, encoding="utf-8").read()
        assert "saramin_1" not in remaining
        assert "saramin_1" in open(archived_path, encoding="utf-8").read()
