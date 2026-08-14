from __future__ import annotations
import os
import tempfile

from jobfind.selection import selected_ids, sync_materials_folders
from jobfind.storage import DIVIDER


def _make_block(job_id: str, selected: bool = False) -> str:
    lines = [DIVIDER, "[자소서]" if selected else "[ ]", f"[제목]   테스트 공고", f"[ID]     {job_id}", DIVIDER]
    return "\n".join(lines) + "\n"


def test_selected_ids_returns_only_marked():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        content = _make_block("saramin_1", selected=True) + _make_block("wanted_2")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)
        assert selected_ids(jobs_path) == ["saramin_1"]


def test_selected_ids_missing_file_returns_empty():
    assert selected_ids("nonexistent.txt") == []


def test_sync_materials_folders_creates_dirs_and_flags_over_limit(monkeypatch):
    import jobfind.selection as selection

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        cover_dir = os.path.join(tmpdir, "cover_letters")
        monkeypatch.setattr(selection, "COVER_LETTERS_DIR", cover_dir)

        content = "".join(
            _make_block(f"saramin_{i}", selected=True) for i in range(5)
        )
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        count, over_limit = sync_materials_folders(jobs_path)

        assert count == 5
        assert over_limit is True
        for i in range(5):
            assert os.path.isdir(os.path.join(cover_dir, f"saramin_{i}", "materials"))


def test_sync_materials_folders_within_limit(monkeypatch):
    import jobfind.selection as selection

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        cover_dir = os.path.join(tmpdir, "cover_letters")
        monkeypatch.setattr(selection, "COVER_LETTERS_DIR", cover_dir)

        content = _make_block("saramin_1", selected=True)
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        count, over_limit = sync_materials_folders(jobs_path)

        assert count == 1
        assert over_limit is False
        assert os.path.isdir(os.path.join(cover_dir, "saramin_1", "materials"))
