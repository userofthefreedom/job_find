from __future__ import annotations
import os
import tempfile

import numpy as np

from jobfind.config import config
from jobfind.relevance import evaluate_relevance, score_relevance
from jobfind.storage import DIVIDER


def test_score_relevance_empty_role_description_passes_all(monkeypatch):
    monkeypatch.setattr(config, "ROLE_DESCRIPTION", "")
    assert score_relevance("", ["아무 공고", "다른 공고"]) == [1.0, 1.0]


def test_score_relevance_empty_job_texts_returns_empty():
    assert score_relevance("서비스 기획", []) == []


def test_score_relevance_uses_model(monkeypatch):
    import jobfind.relevance as relevance

    class _FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            # role_description(첫 항목)과 정확히 같은 텍스트면 유사도 1.0,
            # 아니면 0.0이 되도록 간단한 원-핫 벡터를 구성한다.
            vocab = {t: i for i, t in enumerate(dict.fromkeys(texts))}
            vecs = np.zeros((len(texts), len(vocab)))
            for row, t in enumerate(texts):
                vecs[row, vocab[t]] = 1.0
            return vecs

    monkeypatch.setattr(relevance, "_get_model", lambda name: _FakeModel())
    scores = score_relevance("서비스 기획자", ["서비스 기획자", "전혀 다른 공고"])
    assert scores[0] == 1.0
    assert scores[1] == 0.0


def _make_block(job_id: str, title: str, keyword: str = "") -> str:
    lines = [DIVIDER, "[ ]", f"[제목]   {title}"]
    if keyword:
        lines.append(f"[직무]   {keyword}")
    lines += [f"[ID]     {job_id}", DIVIDER]
    return "\n".join(lines) + "\n"


def test_evaluate_relevance_removes_low_score_jobs(monkeypatch):
    import jobfind.relevance as relevance

    monkeypatch.setattr(config, "ROLE_DESCRIPTION", "서비스 기획")
    monkeypatch.setattr(config, "RELEVANCE_THRESHOLD", 0.5)
    monkeypatch.setattr(
        relevance, "score_relevance", lambda role, texts: [0.9, 0.1][: len(texts)]
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        content = _make_block("saramin_1", "서비스 기획자") + _make_block("wanted_2", "물류 창고 관리")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        removed = evaluate_relevance(jobs_path, dismissed_path)

        assert removed == 1
        remaining = open(jobs_path, encoding="utf-8").read()
        assert "saramin_1" in remaining
        assert "wanted_2" not in remaining
        assert "wanted_2" in open(dismissed_path, encoding="utf-8").read()


def test_evaluate_relevance_skips_when_role_description_blank(monkeypatch):
    monkeypatch.setattr(config, "ROLE_DESCRIPTION", "")
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_path = os.path.join(tmpdir, "jobs_all.txt")
        dismissed_path = os.path.join(tmpdir, "dismissed_ids.txt")
        content = _make_block("saramin_1", "아무 공고")
        with open(jobs_path, "w", encoding="utf-8") as f:
            f.write(content)

        removed = evaluate_relevance(jobs_path, dismissed_path)

        assert removed == 0
        assert open(jobs_path, encoding="utf-8").read() == content


def test_evaluate_relevance_no_file_returns_zero(monkeypatch):
    monkeypatch.setattr(config, "ROLE_DESCRIPTION", "서비스 기획")
    assert evaluate_relevance("nonexistent.txt", "nonexistent2.txt") == 0
