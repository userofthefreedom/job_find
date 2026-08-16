from __future__ import annotations

from jobfind.bundle_detection import is_bundled_posting


def _job_stub(**kwargs):
    base = {"title": "", "keyword": ""}
    return {**base, **kwargs}


def test_detects_gongchae_title():
    assert is_bundled_posting(_job_stub(title="2026년 하반기 신입 공채 (전 부문)"))


def test_detects_bumun_byeol_title():
    assert is_bundled_posting(_job_stub(title="직군별 채용 - 백엔드/프론트엔드/기획"))


def test_detects_numbered_bumun_title():
    assert is_bundled_posting(_job_stub(title="5개 부문 동시 채용"))


def test_normal_single_role_posting_not_flagged():
    job = _job_stub(title="Python 백엔드 개발자", keyword="Python, Django")
    assert not is_bundled_posting(job)


def test_many_similar_tags_alone_not_flagged():
    # 실데이터 검증(Phase 19)에서 단일 직무 공고도 유사 태그를 여러 개 붙이는 경우가
    # 흔함을 확인 — 태그 개수만으로는 판별하지 않는다.
    job = _job_stub(title="영업 담당자 채용", keyword="솔루션기술영업, 영업, 영업기획, 판매, IT·통신기기판매")
    assert not is_bundled_posting(job)


def test_empty_job_not_flagged():
    assert not is_bundled_posting(_job_stub())
