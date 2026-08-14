from __future__ import annotations
import os
from functools import lru_cache

from jobfind.config import config
from jobfind.storage import extract_field, is_dismissed, parse_blocks, rewrite_jobs_file


@lru_cache(maxsize=1)
def _get_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _job_text(title: str, keyword: str) -> str:
    return f"{title} {keyword}".strip()


def score_axis(query: str, job_texts: list[str]) -> list[float]:
    """query와 각 job_texts의 코사인 유사도(0~1)를 반환한다. query가 비어 있으면 전부 0."""
    if not query or not job_texts:
        return [0.0] * len(job_texts)
    model = _get_model(config.RELEVANCE_MODEL)
    embeddings = model.encode([query] + job_texts, normalize_embeddings=True)
    query_vec, job_vecs = embeddings[0], embeddings[1:]
    return [float(vec @ query_vec) for vec in job_vecs]


def rank_jobs(job_texts: list[str]) -> list[float]:
    """직무(roles) 점수 + 도메인(domains) 점수를 더한 결합 점수를 반환한다.

    둘 다 가까운 공고가 최상위, 하나만 가까운 공고가 그 다음 순위가 되도록 단순 합산한다.
    roles/domains 중 비어 있는 축은 0으로 처리되어 나머지 축만으로 순위가 매겨진다.
    """
    role_scores = score_axis(config.RELEVANCE_ROLES, job_texts)
    domain_scores = score_axis(config.RELEVANCE_DOMAINS, job_texts)
    return [r + d for r, d in zip(role_scores, domain_scores)]


def evaluate_relevance(jobs_path: str) -> int:
    """jobs_all.txt의 활성 공고를 직무·도메인 관련성 순으로 정렬해 상위 top_n건만 남긴다.

    순위 밖으로 밀린 공고는 [X] 마커와 달리 영구 제외(dismissed_ids)하지 않는다 — 다음
    수집에서 경쟁 구도가 바뀌면 다시 상위권에 들 수 있어야 하기 때문이다.
    """
    if not (config.RELEVANCE_ROLES or config.RELEVANCE_DOMAINS) or not os.path.exists(jobs_path):
        return 0

    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())

    active = [b for b in blocks if not is_dismissed(b)]
    dismissed_blocks = [b for b in blocks if is_dismissed(b)]
    job_texts = [
        _job_text(extract_field(b, "[제목]"), extract_field(b, "[직무]")) for b in active
    ]
    scores = rank_jobs(job_texts)

    ranked = sorted(zip(active, scores), key=lambda pair: pair[1], reverse=True)
    keep = [block for block, _ in ranked[: config.RELEVANCE_TOP_N]]
    dropped = len(ranked) - len(keep)

    # 아무것도 잘리지 않아도 순위 순서를 파일에 반영해야 하므로 항상 다시 쓴다
    rewrite_jobs_file(keep + dismissed_blocks, jobs_path)
    print(f"[관련성 평가] 관련성 순 정렬 완료, 상위 {len(keep)}건 유지, {dropped}건 순위 밖으로 제외")
    return dropped
