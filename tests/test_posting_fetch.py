from __future__ import annotations

import jobfind.pipeline.orchestrator as orch


def test_fetch_posting_text_empty_url_returns_empty():
    assert orch.fetch_posting_text("") == ""

def test_fetch_posting_text_saramin_returns_empty(monkeypatch):
    # 사람인은 상세 본문이 JS 렌더링이라 정적 스크래핑으로 가져올 수 없는 알려진 한계
    def fail_if_called(job_id):
        raise AssertionError("사람인 URL에서는 fetch_wanted_description을 호출하면 안 됨")

    monkeypatch.setattr(orch, "fetch_wanted_description", fail_if_called)
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=54736780"
    assert orch.fetch_posting_text(url) == ""

def test_fetch_posting_text_wanted_delegates_to_collector(monkeypatch):
    captured = {}

    def fake_fetch(job_id):
        captured["job_id"] = job_id
        return "상세 설명 텍스트"

    monkeypatch.setattr(orch, "fetch_wanted_description", fake_fetch)
    text = orch.fetch_posting_text("https://www.wanted.co.kr/wd/380759")

    assert text == "상세 설명 텍스트"
    assert captured["job_id"] == "380759"
