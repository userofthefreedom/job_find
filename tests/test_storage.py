from __future__ import annotations
import os
import tempfile

from jobfind.storage import (
    DIVIDER,
    extract_id,
    format_block,
    is_dismissed,
    load_active_ids,
    load_dismissed_ids,
    parse_blocks,
    process_x_markers,
)

# ── format_block ──────────────────────────────────────────────────────────────

_JOB = {
    "id": "saramin_12345",
    "source": "사람인",
    "company": "테스트컴퍼니",
    "title": "Python 백엔드 개발자",
    "location": "서울",
    "job_type": "정규직",
    "experience": "경력 3~5년",
    "keyword": "Python, Django",
    "url": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345",
    "deadline": "2026-08-31",
}

def test_format_block_contains_required_fields():
    block = format_block(_JOB)
    assert "[출처]   사람인" in block
    assert "[ID]     saramin_12345" in block
    assert "[제목]   Python 백엔드 개발자" in block
    assert "[직무]   Python, Django" in block
    assert "[마감]   2026-08-31" in block
    assert block.startswith("═")
    assert block.rstrip().endswith("═" * 48)

def test_format_block_skips_empty_keyword():
    job = {**_JOB, "keyword": ""}
    block = format_block(job)
    assert "[직무]" not in block

def test_format_block_skips_empty_deadline():
    job = {**_JOB, "deadline": ""}
    block = format_block(job)
    assert "[마감]" not in block

def test_format_block_id_is_last_content_line():
    block = format_block(_JOB)
    lines = [l for l in block.strip().splitlines() if l.strip()]
    assert lines[-2].startswith("[ID]")  # last content line before closing divider

def test_format_block_includes_empty_check_marker():
    block = format_block(_JOB)
    lines = block.splitlines()
    assert lines[1] == "[ ]"  # 구분선 바로 다음 줄에 체크용 빈 마커


# ── load_active_ids ───────────────────────────────────────────────────────────

def test_load_active_ids():
    content = (
        "════\n[수집일] 2026-07-09\n[ID]     saramin_111\n════\n"
        "════\n[수집일] 2026-07-09\n[ID]     wanted_222\n════\n"
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        ids = load_active_ids(path)
        assert ids == {"saramin_111", "wanted_222"}
    finally:
        os.unlink(path)

def test_load_active_ids_missing_file():
    assert load_active_ids("nonexistent.txt") == set()


# ── load_dismissed_ids ────────────────────────────────────────────────────────

def test_load_dismissed_ids():
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write("saramin_999\nwanted_888\n")
        path = f.name
    try:
        assert load_dismissed_ids(path) == {"saramin_999", "wanted_888"}
    finally:
        os.unlink(path)


# ── parse_blocks ──────────────────────────────────────────────────────────────

def _make_block(job_id: str, x_marker: bool = False) -> str:
    lines = [DIVIDER, f"[수집일] 2026-07-09"]
    if x_marker:
        lines.append("[X]")
    lines += [f"[제목]   테스트 공고", f"[ID]     {job_id}", DIVIDER]
    return "\n".join(lines) + "\n"

def test_parse_blocks_single():
    text = _make_block("saramin_1")
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert "saramin_1" in blocks[0]

def test_parse_blocks_multiple():
    text = _make_block("saramin_1") + _make_block("wanted_2")
    blocks = parse_blocks(text)
    assert len(blocks) == 2

def test_parse_blocks_empty():
    assert parse_blocks("") == []


# ── is_dismissed ──────────────────────────────────────────────────────────────

def test_is_dismissed_upper():
    assert is_dismissed(_make_block("saramin_1", x_marker=True))

def test_is_dismissed_lower():
    block = _make_block("saramin_1").replace(DIVIDER + "\n[수집일]", DIVIDER + "\n[x]\n[수집일]")
    assert is_dismissed(block)

def test_is_dismissed_no_marker():
    assert not is_dismissed(_make_block("saramin_1"))


# ── extract_id ────────────────────────────────────────────────────────────────

def test_extract_id_found():
    assert extract_id(_make_block("saramin_99")) == "saramin_99"

def test_extract_id_not_found():
    block = DIVIDER + "\n[제목] 뭔가\n" + DIVIDER
    assert extract_id(block) is None


# ── process_x_markers ─────────────────────────────────────────────────────────

def test_process_x_markers_removes_block_and_records_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")

        normal = _make_block("saramin_1")
        marked = _make_block("wanted_2", x_marker=True)
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(normal + marked)

        count = process_x_markers(jobs_path, dismissed_path)

        assert count == 1
        remaining = open(jobs_path, encoding="utf-8").read()
        assert "saramin_1" in remaining
        assert "wanted_2" not in remaining
        dismissed = open(dismissed_path, encoding="utf-8").read()
        assert "wanted_2" in dismissed

def test_process_x_markers_no_file_returns_zero():
    assert process_x_markers("nonexistent.txt", "nonexistent2.txt") == 0

def test_process_x_markers_no_marker_does_nothing():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        content = _make_block("saramin_1") + _make_block("wanted_2")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)
        count = process_x_markers(jobs_path, dismissed_path)
        assert count == 0
        assert not os.path.exists(dismissed_path)
        assert open(jobs_path, encoding="utf-8").read() == content

def test_process_x_markers_block_without_id_preserved():
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        no_id_block = DIVIDER + "\n[X]\n[제목] 손상된 블록\n" + DIVIDER + "\n"
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(no_id_block)
        count = process_x_markers(jobs_path, dismissed_path)
        assert count == 0  # [ID] 없으므로 제거하지 않음
