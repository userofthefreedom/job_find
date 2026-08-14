from __future__ import annotations
import os
from functools import lru_cache

from jobfind.config import config
from jobfind.storage import extract_field, is_dismissed, is_selected, parse_blocks, rewrite_jobs_file


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
    """직무(roles) 점수와 도메인(domains) 점수를 결합한 순위 점수를 반환한다.

    roles/domains 둘 다 설정된 경우 곱으로 결합한다 — 한쪽 점수가 0에 가까우면 다른 쪽이
    아무리 높아도 전체 점수가 낮아지도록 해, "직무 태그에 우연히 겹치는 단어가 있을 뿐
    도메인은 전혀 안 맞는" 공고가 상위에 오르는 것을 막는다 (예: roles="기획"일 때 "재무기획"
    처럼 문자열만 겹치고 도메인 관련성이 0에 가까운 공고가 실사용 중 최상위로 오른 문제가
    실제로 있었다 — 단순 합산이었을 때는 role_score 하나만 높아도 총점이 커졌었다).

    roles/domains 중 하나만 설정된 경우, 비어 있는 축은 0으로 고정되어 곱셈이 전부 0이
    되므로 그 경우엔 합산으로 처리해 설정된 축만으로 순위를 매긴다.
    """
    role_scores = score_axis(config.RELEVANCE_ROLES, job_texts)
    domain_scores = score_axis(config.RELEVANCE_DOMAINS, job_texts)
    if config.RELEVANCE_ROLES and config.RELEVANCE_DOMAINS:
        return [r * d for r, d in zip(role_scores, domain_scores)]
    return [r + d for r, d in zip(role_scores, domain_scores)]


def evaluate_relevance(jobs_path: str) -> int:
    """jobs_all.txt의 활성 공고를 직무·도메인 관련성 순으로 정렬해 상위 top_n건만 남긴다.

    순위 밖으로 밀린 공고는 [X] 마커와 달리 영구 제외(dismissed_ids)하지 않는다 — 다음
    수집에서 경쟁 구도가 바뀌면 다시 상위권에 들 수 있어야 하기 때문이다.

    [자소서]로 이미 선택된 공고는 랭킹 대상에서 제외하고 항상 보존한다 — 순위 밖으로 밀려
    파일에서 사라지면 select로 준비해둔 materials/ 폴더나 진행 중이던 자소서 작업과의 연결이
    끊겨버리기 때문이다 (실사용 재평가에서 발견된 문제, docs/PLAN.md 참고).
    """
    if not (config.RELEVANCE_ROLES or config.RELEVANCE_DOMAINS) or not os.path.exists(jobs_path):
        return 0

    with open(jobs_path, encoding="utf-8") as f:
        blocks = parse_blocks(f.read())

    dismissed_blocks = [b for b in blocks if is_dismissed(b)]
    protected_blocks = [b for b in blocks if not is_dismissed(b) and is_selected(b)]
    active = [b for b in blocks if not is_dismissed(b) and not is_selected(b)]

    job_texts = [
        _job_text(extract_field(b, "[제목]"), extract_field(b, "[직무]")) for b in active
    ]
    scores = rank_jobs(job_texts)

    ranked = sorted(zip(active, scores), key=lambda pair: pair[1], reverse=True)
    keep = [block for block, _ in ranked[: config.RELEVANCE_TOP_N]]
    dropped = len(ranked) - len(keep)

    # 아무것도 잘리지 않아도 순위 순서를 파일에 반영해야 하므로 항상 다시 쓴다
    rewrite_jobs_file(protected_blocks + keep + dismissed_blocks, jobs_path)
    print(f"[관련성 평가] 관련성 순 정렬 완료, 상위 {len(keep)}건 유지, {dropped}건 순위 밖으로 제외 "
          f"({len(protected_blocks)}건은 [자소서] 선택으로 보존)")
    return dropped
