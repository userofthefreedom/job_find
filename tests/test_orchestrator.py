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
