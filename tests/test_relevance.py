from __future__ import annotations
import os
import tempfile

import numpy as np

from jobfind.config import config
from jobfind.relevance import evaluate_relevance, rank_jobs, score_axis
from jobfind.storage import DIVIDER


def test_score_axis_empty_query_returns_zeros():
    assert score_axis("", ["아무 공고", "다른 공고"]) == [0.0, 0.0]


def test_score_axis_empty_job_texts_returns_empty():
    assert score_axis("기획", []) == []


class _OneHotModel:
    """텍스트를 vocab 순서의 원-핫 벡터로 인코딩하는 가짜 임베딩 모델.
    같은 텍스트끼리는 유사도 1.0, 다른 텍스트끼리는 0.0이 되어 점수를 예측 가능하게 만든다."""

    def encode(self, texts, normalize_embeddings=True):
        vocab = {t: i for i, t in enumerate(dict.fromkeys(texts))}
        vecs = np.zeros((len(texts), len(vocab)))
        for row, t in enumerate(texts):
            vecs[row, vocab[t]] = 1.0
        return vecs


def test_score_axis_uses_model(monkeypatch):
    import jobfind.relevance as relevance

    monkeypatch.setattr(relevance, "_get_model", lambda name: _OneHotModel())
    scores = score_axis("기획 PM", ["기획 PM", "전혀 다른 공고"])
    assert scores[0] == 1.0
    assert scores[1] == 0.0


def test_rank_jobs_combines_role_and_domain(monkeypatch):
    import jobfind.relevance as relevance

    monkeypatch.setattr(config, "RELEVANCE_ROLES", "기획 PM")
    monkeypatch.setattr(config, "RELEVANCE_DOMAINS", "게임")
    monkeypatch.setattr(relevance, "_get_model", lambda name: _OneHotModel())

    # "게임 기획 PM"은 role/domain 텍스트 각각과 정확히 일치하지 않으므로
    # 실제 원-핫 모델로는 role_scores/domain_scores를 개별 호출로 통제하기 어렵다.
    # score_axis를 직접 스텁으로 대체해 결합 로직만 검증한다.
    monkeypatch.setattr(
        relevance,
        "score_axis",
        lambda query, texts: {
            "기획 PM": [0.9, 0.9, 0.1],
            "게임": [0.9, 0.1, 0.9],
        }[query],
    )
    combined = rank_jobs(["게임 기획 PM", "반도체 개발 PM", "게임 마케팅팀"])
    assert combined == [1.8, 1.0, 1.0]


def _make_block(job_id: str, title: str, keyword: str = "") -> str:
    lines = [DIVIDER, "[ ]", f"[제목]   {title}"]
    if keyword:
        lines.append(f"[직무]   {keyword}")
    lines += [f"[ID]     {job_id}", DIVIDER]
    return "\n".join(lines) + "\n"


def test_evaluate_relevance_keeps_only_top_n(monkeypatch):
    import jobfind.relevance as relevance

    monkeypatch.setattr(config, "RELEVANCE_ROLES", "기획 PM")
    monkeypatch.setattr(config, "RELEVANCE_DOMAINS", "")
    monkeypatch.setattr(config, "RELEVANCE_TOP_N", 2)
    # 세 공고 각각의 결합 점수를 3, 1, 2 순으로 스텁 — 정렬 후 상위 2건만 남아야 한다.
    monkeypatch.setattr(relevance, "rank_jobs", lambda texts: [3.0, 1.0, 2.0][: len(texts)])

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        content = (
            _make_block("saramin_1", "1순위 공고")
            + _make_block("saramin_2", "3순위 공고")
            + _make_block("saramin_3", "2순위 공고")
        )
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        dropped = evaluate_relevance(jobs_path)

        assert dropped == 1
        remaining = open(jobs_path, encoding="utf-8").read()
        assert "saramin_1" in remaining
        assert "saramin_3" in remaining
        assert "saramin_2" not in remaining
        # 순위 밖 공고라도 영구 제외 목록에는 등록하지 않는다
        assert not os.path.exists(os.path.join(tmpdir, "dismissed_ids.txt"))


def test_evaluate_relevance_no_op_when_pool_within_top_n(monkeypatch):
    import jobfind.relevance as relevance

    monkeypatch.setattr(config, "RELEVANCE_ROLES", "기획 PM")
    monkeypatch.setattr(config, "RELEVANCE_TOP_N", 20)
    monkeypatch.setattr(relevance, "rank_jobs", lambda texts: [1.0] * len(texts))

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        content = _make_block("saramin_1", "공고")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        dropped = evaluate_relevance(jobs_path)

        assert dropped == 0
        assert open(jobs_path, encoding="utf-8").read() == content


def test_evaluate_relevance_skips_when_roles_and_domains_blank(monkeypatch):
    monkeypatch.setattr(config, "RELEVANCE_ROLES", "")
    monkeypatch.setattr(config, "RELEVANCE_DOMAINS", "")
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        content = _make_block("saramin_1", "아무 공고")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        dropped = evaluate_relevance(jobs_path)

        assert dropped == 0
        assert open(jobs_path, encoding="utf-8").read() == content


def test_evaluate_relevance_no_file_returns_zero(monkeypatch):
    monkeypatch.setattr(config, "RELEVANCE_ROLES", "기획 PM")
    assert evaluate_relevance("nonexistent.txt") == 0
