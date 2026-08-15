from __future__ import annotations

import jobfind.verification as ver
from jobfind.storage import DIVIDER


class _ScriptedProvider:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def run(self, system_prompt, user_prompt, images=None, extra_tools=None):
        self.calls.append({"system": system_prompt, "user": user_prompt, "images": images})
        return self._responses.pop(0)


def _block(marker, id_, title="테스트 공고", link="https://www.wanted.co.kr/wd/1", extra=""):
    return (
        f"{DIVIDER}\n{marker}\n[수집일] 2026-08-15\n[출처]   원티드\n[회사]   테스트컴퍼니\n"
        f"[제목]   {title}\n[링크]   {link}\n{extra}[ID]     {id_}\n{DIVIDER}\n"
    )


def _setup(monkeypatch, tmp_path, jobs_text, responses, profile_text="프로필"):
    jobs_path = tmp_path / "jobs_all.txt"
    jobs_path.write_text(jobs_text, encoding="utf-8")

    monkeypatch.setattr(ver, "load_profile", lambda: profile_text)
    monkeypatch.setattr(ver, "gather_evidence", lambda url, job_id: ("상세 텍스트", []))
    fake = _ScriptedProvider(responses)
    monkeypatch.setattr(ver, "get_provider", lambda spec: fake)
    return str(jobs_path), fake


def test_verify_jobs_pass_verdict_appends_note(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path, fake = _setup(
        monkeypatch, tmp_path, jobs_text, responses=["PASS\n요건을 충족합니다"]
    )

    counts = ver.verify_jobs(jobs_path)

    assert counts == {"checked": 1, "pass": 1, "concern": 0, "unknown": 0}
    result = open(jobs_path, encoding="utf-8").read()
    assert "[검수] PASS: 요건을 충족합니다" in result
    assert len(fake.calls) == 1


def test_verify_jobs_concern_verdict(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path, _ = _setup(
        monkeypatch, tmp_path, jobs_text,
        responses=["CONCERN\n실제로는 경력 5년 이상 필요"],
    )

    counts = ver.verify_jobs(jobs_path)

    assert counts["concern"] == 1
    assert "[검수] CONCERN: 실제로는 경력 5년 이상 필요" in open(jobs_path, encoding="utf-8").read()


def test_verify_jobs_invalid_verdict_falls_back_to_unknown(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path, _ = _setup(monkeypatch, tmp_path, jobs_text, responses=["뭔가 이상한 응답"])

    counts = ver.verify_jobs(jobs_path)

    assert counts["unknown"] == 1
    assert "[검수] UNKNOWN" in open(jobs_path, encoding="utf-8").read()


def test_verify_jobs_skips_already_verified_block(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1", extra="[검수] PASS: 이미 확인함\n")
    jobs_path, fake = _setup(monkeypatch, tmp_path, jobs_text, responses=[])

    counts = ver.verify_jobs(jobs_path)

    assert counts == {"checked": 0, "pass": 0, "concern": 0, "unknown": 0}
    assert len(fake.calls) == 0
    assert "[검수] PASS: 이미 확인함" in open(jobs_path, encoding="utf-8").read()


def test_verify_jobs_skips_dismissed_block(monkeypatch, tmp_path):
    jobs_text = _block("[X]", "wanted_1")
    jobs_path, fake = _setup(monkeypatch, tmp_path, jobs_text, responses=[])

    counts = ver.verify_jobs(jobs_path)

    assert counts == {"checked": 0, "pass": 0, "concern": 0, "unknown": 0}
    assert len(fake.calls) == 0


def test_verify_jobs_provider_failure_leaves_block_unverified(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path = tmp_path / "jobs_all.txt"
    jobs_path.write_text(jobs_text, encoding="utf-8")

    monkeypatch.setattr(ver, "load_profile", lambda: "프로필")
    monkeypatch.setattr(ver, "gather_evidence", lambda url, job_id: ("", []))

    class _Boom:
        def run(self, *a, **kw):
            raise RuntimeError("provider down")

    monkeypatch.setattr(ver, "get_provider", lambda spec: _Boom())

    counts = ver.verify_jobs(str(jobs_path))

    assert counts == {"checked": 0, "pass": 0, "concern": 0, "unknown": 0}
    result = open(jobs_path, encoding="utf-8").read()
    assert "[검수]" not in result  # 실패한 공고는 다음 실행에서 재시도 가능해야 함


def test_verify_jobs_strips_markdown_bold_from_verdict(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path, _ = _setup(
        monkeypatch, tmp_path, jobs_text, responses=["**CONCERN**\n실무 경력 요건 미달"]
    )

    counts = ver.verify_jobs(jobs_path)

    assert counts["concern"] == 1
    result = open(jobs_path, encoding="utf-8").read()
    assert "[검수] CONCERN: 실무 경력 요건 미달" in result
    # 메모는 항상 한 줄이어야 [ID] 줄 위치 등 블록 형식이 안 깨진다
    note_line = next(ln for ln in result.splitlines() if ln.startswith("[검수]"))
    assert note_line.count("\n") == 0


def test_verify_jobs_uses_last_verdict_on_self_correction(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path, _ = _setup(
        monkeypatch, tmp_path, jobs_text,
        responses=["PASS\n없음(수정: 아래 CONCERN 참고)\n\nCONCERN\n\n실제로는 경력 미달"],
    )

    counts = ver.verify_jobs(jobs_path)

    assert counts["concern"] == 1
    assert counts["pass"] == 0


def test_verify_jobs_no_file_returns_zero_counts(tmp_path):
    counts = ver.verify_jobs(str(tmp_path / "nonexistent.txt"))
    assert counts == {"checked": 0, "pass": 0, "concern": 0, "unknown": 0}


def test_verify_jobs_note_inserted_before_id_line(monkeypatch, tmp_path):
    jobs_text = _block("[ ]", "wanted_1")
    jobs_path, _ = _setup(monkeypatch, tmp_path, jobs_text, responses=["PASS\n근거"])

    ver.verify_jobs(jobs_path)

    lines = open(jobs_path, encoding="utf-8").read().splitlines()
    id_line_idx = next(i for i, ln in enumerate(lines) if ln.startswith("[ID]"))
    assert lines[id_line_idx - 1].startswith("[검수]")


# ── gather_evidence ──────────────────────────────────────────────────────────

def test_gather_evidence_wanted_uses_description(monkeypatch):
    import jobfind.verification as mod

    monkeypatch.setattr(mod, "fetch_wanted_description", lambda job_id: f"상세-{job_id}")

    text, images = mod.gather_evidence("https://www.wanted.co.kr/wd/123", "wanted_123")

    assert text == "상세-123"
    assert images == []


def test_gather_evidence_saramin_downloads_images(monkeypatch, tmp_path):
    import jobfind.verification as mod

    monkeypatch.setattr(mod, "fetch_saramin_images", lambda rec_idx: ["https://img.example/a.png"])
    monkeypatch.setattr(mod.tempfile, "gettempdir", lambda: str(tmp_path))

    class _FakeImgResponse:
        content = b"fake-image-bytes"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(mod.requests, "get", lambda *a, **kw: _FakeImgResponse())

    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=54740848"
    text, images = mod.gather_evidence(url, "saramin_54740848")

    assert text == ""
    assert len(images) == 1
    assert images[0].read_bytes() == b"fake-image-bytes"


def test_gather_evidence_unknown_source_returns_empty(monkeypatch):
    import jobfind.verification as mod

    text, images = mod.gather_evidence("https://example.com/job/1", "job_1")

    assert text == ""
    assert images == []
