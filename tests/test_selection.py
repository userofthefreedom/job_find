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
            # _make_block에는 [회사]가 없어 폴더명이 <ID>_<제목>이 된다 (Phase 22)
            assert os.path.isdir(os.path.join(cover_dir, f"saramin_{i}_테스트 공고", "materials"))


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
        assert os.path.isdir(os.path.join(cover_dir, "saramin_1_테스트 공고", "materials"))


# ── notes.md 자동 생성 (Phase 22) ───────────────────────────────────────────

def test_sync_materials_folders_creates_notes_template(monkeypatch):
    import jobfind.selection as selection

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        cover_dir = os.path.join(tmpdir, "cover_letters")
        monkeypatch.setattr(selection, "COVER_LETTERS_DIR", cover_dir)

        content = _make_block("saramin_1", selected=True)
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        sync_materials_folders(jobs_path)

        notes_path = os.path.join(cover_dir, "saramin_1_테스트 공고", "materials", "notes.md")
        assert os.path.exists(notes_path)
        assert "자소설닷컴" in open(notes_path, encoding="utf-8").read()


def test_sync_materials_folders_does_not_overwrite_existing_notes(monkeypatch):
    import jobfind.selection as selection

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        cover_dir = os.path.join(tmpdir, "cover_letters")
        monkeypatch.setattr(selection, "COVER_LETTERS_DIR", cover_dir)

        content = _make_block("saramin_1", selected=True)
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        materials_dir = os.path.join(cover_dir, "saramin_1_테스트 공고", "materials")
        os.makedirs(materials_dir)
        notes_path = os.path.join(materials_dir, "notes.md")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write("사용자가 이미 적어둔 내용")

        sync_materials_folders(jobs_path)

        assert open(notes_path, encoding="utf-8").read() == "사용자가 이미 적어둔 내용"
