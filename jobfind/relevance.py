from __future__ import annotations
import os
from functools import lru_cache

from jobfind.config import config
from jobfind.storage import (
    append_dismissed_ids,
    extract_field,
    extract_id,
    is_dismissed,
    parse_blocks,
    rewrite_jobs_file,
)


@lru_cache(maxsize=1)
def _get_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _job_text(title: str, keyword: str) -> str:
    return f"{title} {keyword}".strip()


def score_relevance(role_description: str, job_texts: list[str]) -> list[float]:
    """role_description과 각 job_texts의 코사인 유사도(0~1)를 반환한다."""
    if not role_description or not job_texts:
        return [1.0] * len(job_texts)
    model = _get_model(config.RELEVANCE_MODEL)
    embeddings = model.encode([role_description] + job_texts, normalize_embeddings=True)
    role_vec, job_vecs = embeddings[0], embeddings[1:]
    return [float(vec @ role_vec) for vec in job_vecs]


def evaluate_relevance(jobs_path: str, dismissed_path: str) -> int:
    """jobs_all.txt의 각 활성 블록을 role_description과 비교해 무관한 공고를 제거한다.

    keywords 1차 필터를 통과한 공고 중에서도 threshold 미만인 것만 걸러내는
    2차(격리된) 필터다. role_description이 비어 있으면 아무것도 하지 않는다.
    """
    if not config.ROLE_DESCRIPTION or not os.path.exists(jobs_path):
        return 0

    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())

    active = [b for b in blocks if not is_dismissed(b)]
    job_texts = [
        _job_text(extract_field(b, "[제목]"), extract_field(b, "[직무]")) for b in active
    ]
    scores = score_relevance(config.ROLE_DESCRIPTION, job_texts)

    keep: list[str] = []
    removed_ids: list[str] = []
    for block, score in zip(active, scores):
        if score >= config.RELEVANCE_THRESHOLD:
            keep.append(block)
            continue
        id_ = extract_id(block)
        if id_:
            removed_ids.append(id_)
        else:
            keep.append(block)  # ID 없는 손상 블록은 보존 (X 마커 처리와 동일한 안전장치)

    if removed_ids:
        dismissed_blocks = [b for b in blocks if is_dismissed(b)]
        append_dismissed_ids(removed_ids, dismissed_path)
        rewrite_jobs_file(keep + dismissed_blocks, jobs_path)
        print(f"[관련성 평가] {len(removed_ids)}건 제거됨")
    return len(removed_ids)
