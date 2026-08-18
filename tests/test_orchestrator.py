from __future__ import annotations

import jobfind.pipeline.orchestrator as orch


class _ScriptedProvider:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def run(self, system_prompt, user_prompt, images=None, extra_tools=None):
        self.calls.append({
            "system": system_prompt, "user": user_prompt,
            "images": images, "extra_tools": extra_tools,
        })
        return self._responses.pop(0)


def _setup(monkeypatch, tmp_path, responses, profile_text="프로필 내용"):
    profile_path = tmp_path / "profile.md"
    profile_path.write_text(profile_text, encoding="utf-8")
    cover_dir = tmp_path / "cover_letters"
    monkeypatch.setattr(orch, "PROFILE_PATH", str(profile_path))
    monkeypatch.setattr(orch, "COVER_LETTERS_DIR", str(cover_dir))
    monkeypatch.setattr(orch, "fetch_company_profile", lambda name: "")

    fake = _ScriptedProvider(responses)
    monkeypatch.setattr(orch, "get_provider", lambda spec: fake)
    return fake, cover_dir


def test_run_for_job_no_revision_needed(monkeypatch, tmp_path):
    fake, cover_dir = _setup(
        monkeypatch, tmp_path,
        responses=["계획 초안", "OK\n좋습니다", "자소서 초안", "OK\n좋은 초안입니다"],
    )

    result = orch.run_for_job("saramin_1", "공고 텍스트")

    assert result["plan"] == "계획 초안"
    assert result["plan_review"] == "OK\n좋습니다"
    assert result["draft"] == "자소서 초안"
    assert result["draft_review"] == "OK\n좋은 초안입니다"
    assert len(fake.calls) == 4  # 재작성 없이 4단계만 호출됨

    job_dir = cover_dir / "saramin_1"
    assert (job_dir / "plan.md").read_text(encoding="utf-8") == "계획 초안"
    assert (job_dir / "plan_review.md").read_text(encoding="utf-8") == "OK\n좋습니다"
    assert (job_dir / "draft.md").read_text(encoding="utf-8") == "자소서 초안"
    assert (job_dir / "draft_review.md").read_text(encoding="utf-8") == "OK\n좋은 초안입니다"

def test_run_for_job_revises_plan_when_needed(monkeypatch, tmp_path):
    fake, cover_dir = _setup(
        monkeypatch, tmp_path,
        responses=[
            "계획 v1",
            "NEEDS_REVISION\n더 구체적으로",
            "계획 v2 (개선됨)",
            "자소서 초안",
            "OK\n좋음",
        ],
    )

    result = orch.run_for_job("saramin_1", "공고 텍스트")

    assert result["plan"] == "계획 v2 (개선됨)"
    assert len(fake.calls) == 5  # planner 두 번(초안+재작성) + 나머지 3단계
    revision_call = fake.calls[2]
    assert "계획 v1" in revision_call["user"]
    assert "더 구체적으로" in revision_call["user"]

    job_dir = cover_dir / "saramin_1"
    assert (job_dir / "plan.md").read_text(encoding="utf-8") == "계획 v2 (개선됨)"

def test_run_for_job_revises_draft_when_needed(monkeypatch, tmp_path):
    fake, cover_dir = _setup(
        monkeypatch, tmp_path,
        responses=[
            "계획",
            "OK\n좋습니다",
            "초안 v1",
            "NEEDS_REVISION\n단점을 반복하지 마라",
            "초안 v2 (개선됨)",
            "OK\n좋음",
        ],
    )

    result = orch.run_for_job("saramin_1", "공고 텍스트")

    assert result["draft"] == "초안 v2 (개선됨)"
    assert result["draft_review"] == "OK\n좋음"
    assert len(fake.calls) == 6  # 계획+계획평가+초안+초안평가 + 초안 재작성+재평가
    revision_call = fake.calls[4]
    assert "초안 v1" in revision_call["user"]
    assert "단점을 반복하지 마라" in revision_call["user"]

    job_dir = cover_dir / "saramin_1"
    assert (job_dir / "draft.md").read_text(encoding="utf-8") == "초안 v2 (개선됨)"
    assert (job_dir / "draft_review.md").read_text(encoding="utf-8") == "OK\n좋음"


def test_run_for_job_does_not_loop_past_one_draft_revision(monkeypatch, tmp_path):
    fake, _ = _setup(
        monkeypatch, tmp_path,
        responses=[
            "계획",
            "OK",
            "초안 v1",
            "NEEDS_REVISION\n피드백1",
            "초안 v2",
            "NEEDS_REVISION\n피드백2",
        ],
    )

    result = orch.run_for_job("saramin_1", "공고 텍스트")

    assert result["draft"] == "초안 v2"
    assert result["draft_review"] == "NEEDS_REVISION\n피드백2"
    assert len(fake.calls) == 6  # 재작성은 최대 1회까지만


def test_run_for_job_passes_material_images_only_to_planner(monkeypatch, tmp_path):
    fake, cover_dir = _setup(
        monkeypatch, tmp_path,
        responses=["계획", "OK", "초안", "OK"],
    )
    materials_dir = cover_dir / "saramin_1" / "materials"
    materials_dir.mkdir(parents=True)
    img = materials_dir / "1.png"
    img.write_bytes(b"fake")

    orch.run_for_job("saramin_1", "공고 텍스트")

    planner_call, plan_eval_call, writer_call, draft_eval_call = fake.calls
    assert planner_call["images"] == [img]
    assert plan_eval_call["images"] is None
    assert writer_call["images"] is None
    assert draft_eval_call["images"] is None

def test_run_for_job_missing_profile_uses_empty_string(monkeypatch, tmp_path):
    cover_dir = tmp_path / "cover_letters"
    monkeypatch.setattr(orch, "PROFILE_PATH", str(tmp_path / "nonexistent_profile.md"))
    monkeypatch.setattr(orch, "COVER_LETTERS_DIR", str(cover_dir))
    monkeypatch.setattr(orch, "fetch_company_profile", lambda name: "")
    fake = _ScriptedProvider(["계획", "OK", "초안", "OK"])
    monkeypatch.setattr(orch, "get_provider", lambda spec: fake)

    orch.run_for_job("saramin_1", "공고 텍스트")

    assert orch.load_profile() == ""

def test_run_for_job_enriches_job_text_with_company_profile(monkeypatch, tmp_path):
    fake, _ = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    monkeypatch.setattr(orch, "fetch_company_profile", lambda name: "[DART 기업개황]\n대표자: 홍길동")

    job_text = "[회사]   (주)예시기업\n[제목]   백엔드 개발자"
    orch.run_for_job("saramin_1", job_text)

    for call in fake.calls:
        assert "[DART 기업개황]" in call["user"]
        assert "대표자: 홍길동" in call["user"]

def test_run_for_job_skips_company_profile_when_not_found(monkeypatch, tmp_path):
    fake, _ = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    monkeypatch.setattr(orch, "fetch_company_profile", lambda name: "")

    job_text = "[회사]   (주)예시기업\n[제목]   백엔드 개발자"
    orch.run_for_job("saramin_1", job_text)

    for call in fake.calls:
        assert "[DART 기업개황]" not in call["user"]

def test_run_for_job_grants_research_tools_only_to_planner(monkeypatch, tmp_path):
    fake, _ = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])

    orch.run_for_job("saramin_1", "공고 텍스트")

    planner_call, plan_eval_call, writer_call, draft_eval_call = fake.calls
    assert planner_call["extra_tools"] == orch.PLANNER_RESEARCH_TOOLS
    assert plan_eval_call["extra_tools"] is None
    assert writer_call["extra_tools"] is None
    assert draft_eval_call["extra_tools"] is None

def test_run_for_job_grants_research_tools_on_plan_revision_too(monkeypatch, tmp_path):
    fake, _ = _setup(
        monkeypatch, tmp_path,
        responses=["계획 v1", "NEEDS_REVISION\n피드백", "계획 v2", "초안", "OK"],
    )

    orch.run_for_job("saramin_1", "공고 텍스트")

    revision_call = fake.calls[2]
    assert revision_call["extra_tools"] == orch.PLANNER_RESEARCH_TOOLS

def test_run_for_job_enriches_job_text_with_fetched_posting(monkeypatch, tmp_path):
    fake, _ = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    monkeypatch.setattr(orch, "fetch_posting_text", lambda url: "실제 공고 상세 내용입니다")

    job_text = "[제목]   백엔드 개발자\n[링크]   https://example.com/job/1"
    orch.run_for_job("saramin_1", job_text)

    for call in fake.calls:
        assert "실제 공고 상세 내용입니다" in call["user"]

def test_run_for_job_skips_enrichment_when_fetch_fails(monkeypatch, tmp_path):
    fake, _ = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    monkeypatch.setattr(orch, "fetch_posting_text", lambda url: "")

    job_text = "[제목]   백엔드 개발자\n[링크]   https://example.com/job/1"
    orch.run_for_job("saramin_1", job_text)

    for call in fake.calls:
        assert "[공고 상세 설명]" not in call["user"]


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        pass


def test_run_for_job_downloads_saramin_detail_images(monkeypatch, tmp_path):
    fake, cover_dir = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    monkeypatch.setattr(
        orch, "fetch_saramin_images", lambda rec_idx: ["https://img.saramin/a.png", "https://img.saramin/b.jpg"]
    )
    monkeypatch.setattr(orch.requests, "get", lambda url, **kw: _FakeResponse(url.encode()))

    job_text = "[링크]   https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345"
    orch.run_for_job("saramin_12345", job_text)

    materials_dir = cover_dir / "saramin_12345" / "materials"
    downloaded = sorted(materials_dir.glob("saramin_detail_*"))
    assert [p.name for p in downloaded] == ["saramin_detail_0.png", "saramin_detail_1.jpg"]

    planner_call = fake.calls[0]
    assert planner_call["images"] == downloaded


def test_run_for_job_skips_saramin_download_for_non_saramin_url(monkeypatch, tmp_path):
    fake, cover_dir = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    called = []
    monkeypatch.setattr(orch, "fetch_saramin_images", lambda rec_idx: called.append(rec_idx) or [])

    job_text = "[링크]   https://www.wanted.co.kr/wd/999"
    orch.run_for_job("wanted_999", job_text)

    assert called == []
    materials_dir = cover_dir / "wanted_999" / "materials"
    assert not list(materials_dir.glob("saramin_detail_*")) if materials_dir.exists() else True


def test_run_for_job_does_not_redownload_existing_saramin_images(monkeypatch, tmp_path):
    fake, cover_dir = _setup(monkeypatch, tmp_path, responses=["계획", "OK", "초안", "OK"])
    materials_dir = cover_dir / "saramin_12345" / "materials"
    materials_dir.mkdir(parents=True)
    (materials_dir / "saramin_detail_0.png").write_bytes(b"already downloaded")

    monkeypatch.setattr(orch, "fetch_saramin_images", lambda rec_idx: ["https://img.saramin/a.png"])
    get_calls = []
    monkeypatch.setattr(
        orch.requests, "get", lambda url, **kw: get_calls.append(url) or _FakeResponse(b"new")
    )

    job_text = "[링크]   https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345"
    orch.run_for_job("saramin_12345", job_text)

    assert get_calls == []
    assert (materials_dir / "saramin_detail_0.png").read_bytes() == b"already downloaded"
