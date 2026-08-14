from __future__ import annotations
import os

from jobfind.storage import extract_id, is_selected, parse_blocks

COVER_LETTERS_DIR = "output/cover_letters"
MAX_SELECTED = 4


def selected_ids(jobs_path: str) -> list[str]:
    if not os.path.exists(jobs_path):
        return []
    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())
    ids = []
    for block in blocks:
        if is_selected(block):
            id_ = extract_id(block)
            if id_:
                ids.append(id_)
    return ids


def sync_materials_folders(jobs_path: str) -> tuple[int, bool]:
    """[자소서]로 선택된 공고마다 materials/ 폴더를 만든다.

    반환값: (선택된 공고 수, 4개 초과 여부). 4개를 넘겨도 폴더는 전부 만들되,
    write 단계에서 사용자가 마커를 정리하도록 초과 여부만 알려준다.
    """
    ids = selected_ids(jobs_path)
    for id_ in ids:
        os.makedirs(os.path.join(COVER_LETTERS_DIR, id_, "materials"), exist_ok=True)
    return len(ids), len(ids) > MAX_SELECTED
