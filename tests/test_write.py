from __future__ import annotations

import jobfind.cli as cli


def test_write_no_selection_prints_guidance(monkeypatch, capsys):
    monkeypatch.setattr(cli, "selected_ids", lambda path: [])
    cli.write()
    assert "[자소서]로 표시" in capsys.readouterr().out

def test_write_over_limit_refuses(monkeypatch, capsys):
    monkeypatch.setattr(cli, "selected_ids", lambda path: ["a", "b", "c", "d", "e"])
    cli.write()
    out = capsys.readouterr().out
    assert "[오류]" in out
    assert "최대 4개" in out

def test_write_runs_pipeline_for_each_selected_job(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "selected_ids", lambda path: ["saramin_1", "wanted_2"])
    monkeypatch.setattr(cli, "find_block", lambda path, job_id: f"block for {job_id}")
    monkeypatch.setattr(cli, "run_for_job", lambda job_id, block: calls.append((job_id, block)))

    cli.write()

    assert calls == [("saramin_1", "block for saramin_1"), ("wanted_2", "block for wanted_2")]
    out = capsys.readouterr().out
    assert "saramin_1" in out
    assert "wanted_2" in out
    assert "자소서 작성 완료" in out

def test_write_skips_job_not_found_in_file(monkeypatch, capsys):
    monkeypatch.setattr(cli, "selected_ids", lambda path: ["saramin_1"])
    monkeypatch.setattr(cli, "find_block", lambda path, job_id: None)
    monkeypatch.setattr(cli, "run_for_job", lambda job_id, block: (_ for _ in ()).throw(AssertionError("should not run")))

    cli.write()

    assert "찾을 수 없어 건너뜀" in capsys.readouterr().out
