from __future__ import annotations
import os

from jobfind.storage import cover_letter_folder_name, extract_id, is_selected, parse_blocks

COVER_LETTERS_DIR = "output/cover_letters"
MAX_SELECTED = 4

NOTES_TEMPLATE = """# 자소서 문항 메모

## 실제 자소서 문항 (있다면 여기에 그대로 붙여넣기)
사람인·원티드 공고는 대부분 실제 자소서 문항(질문·글자수 제한)을 제공하지 않습니다.
자소설닷컴(jasoseol.com) 등에서 지원할 회사가 문항을 별도로 공개하고 있다면 브라우저로 직접
열어 확인하고, 문항 제목·글자수 제한까지 아래에 그대로 옮겨 적으세요. 여기 적힌 문항이 있으면
write 단계가 표준 4문항 구성보다 이 내용을 우선 반영합니다.

(문항 없음 — 표준 구성으로 작성됨)

## 기타 참고 메모
(자유롭게 추가)
"""


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


def _ensure_notes_template(materials_dir: str) -> None:
    """이미 있으면 건드리지 않는다 — 사용자가 채워둔 내용을 덮어쓰면 안 되므로(Phase 22)."""
    notes_path = os.path.join(materials_dir, "notes.md")
    if not os.path.exists(notes_path):
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(NOTES_TEMPLATE)


def sync_materials_folders(jobs_path: str) -> tuple[int, bool]:
    """[자소서]로 선택된 공고마다 <ID>_<회사명>_<직무명> 폴더(Phase 22)에 materials/ 폴더와
    notes.md 템플릿을 준비한다.

    반환값: (선택된 공고 수, 4개 초과 여부). 4개를 넘겨도 폴더는 전부 만들되,
    write 단계에서 사용자가 마커를 정리하도록 초과 여부만 알려준다.
    """
    if not os.path.exists(jobs_path):
        return 0, False
    with open(jobs_path, encoding="utf-8") as f:
        blocks = [b for b in parse_blocks(f.read()) if is_selected(b)]
    for block in blocks:
        id_ = extract_id(block)
        if not id_:
            continue
        materials_dir = os.path.join(
            COVER_LETTERS_DIR, cover_letter_folder_name(id_, block), "materials"
        )
        os.makedirs(materials_dir, exist_ok=True)
        _ensure_notes_template(materials_dir)
    return len(blocks), len(blocks) > MAX_SELECTED
