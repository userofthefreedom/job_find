from __future__ import annotations
import os
import tempfile

import jobfind.cli as cli
from jobfind.storage import DIVIDER


def _block(job_id: str, bundled: bool = False, essay_roles: bool = False) -> str:
    lines = [DIVIDER, "[자소서]"]
    if bundled:
        lines.append("[공채후보] 복수 직무 묶음 공고일 수 있음")
    if essay_roles:
        lines.append("[자소서문항] SCM — 실제 문항 문구는 자소설닷컴에서 직접 확인")
    lines += [f"[제목]   테스트 공고", f"[ID]     {job_id}", DIVIDER]
    return "\n".join(lines) + "\n"


def _run_select(monkeypatch, tmpdir, content):
    jobs_path = os.path.join(tmpdir, "jobs_all.txt")
    with open(jobs_path, "w", encoding="utf-8") as f:
        f.write(content)
    monkeypatch.setattr(cli, "JOBS_PATH", jobs_path)
    monkeypatch.setattr("jobfind.selection.COVER_LETTERS_DIR", os.path.join(tmpdir, "cover_letters"))
    cli.select()


def test_select_notes_bundled_candidate(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_select(monkeypatch, tmpdir, _block("saramin_1", bundled=True))
        out = capsys.readouterr().out
        assert "[공채후보]" in out
        assert "세부 직무" in out


def test_select_no_bundle_notice_for_normal_posting(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_select(monkeypatch, tmpdir, _block("saramin_1", bundled=False))
        out = capsys.readouterr().out
        assert "[공채후보]" not in out


def test_select_notes_essay_roles_present(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_select(monkeypatch, tmpdir, _block("jasoseol_1", essay_roles=True))
        out = capsys.readouterr().out
        assert "[자소서문항]" in out
        assert "직접 확인" in out


def test_select_no_essay_roles_notice_for_normal_posting(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_select(monkeypatch, tmpdir, _block("saramin_1", essay_roles=False))
        out = capsys.readouterr().out
        assert "[자소서문항]" not in out
