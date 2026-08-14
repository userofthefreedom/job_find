from __future__ import annotations
import json
from pathlib import Path

import pytest

from jobfind.providers.api import ApiProvider
from jobfind.providers.base import get_provider
from jobfind.providers.claude_cli import ClaudeCliProvider
from jobfind.providers.codex_cli import CodexCliProvider


# ── get_provider ──────────────────────────────────────────────────────────────

def test_get_provider_claude_cli():
    assert isinstance(get_provider("claude_cli"), ClaudeCliProvider)

def test_get_provider_codex_cli():
    assert isinstance(get_provider("codex_cli"), CodexCliProvider)

def test_get_provider_api_anthropic():
    provider = get_provider("api:anthropic")
    assert isinstance(provider, ApiProvider)
    assert provider.backend == "anthropic"

def test_get_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_provider("unknown")


# ── ClaudeCliProvider ────────────────────────────────────────────────────────

class _FakeCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def test_claude_cli_provider_returns_result_text(monkeypatch):
    import jobfind.providers.claude_cli as mod

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeCompletedProcess(json.dumps({"is_error": False, "result": "PONG"}))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    text = ClaudeCliProvider().run("system", "user prompt")
    assert text == "PONG"
    assert "--allowedTools" in captured["cmd"]
    assert captured["kwargs"]["cwd"] != ""

def test_claude_cli_provider_with_images_enables_read_tool(monkeypatch, tmp_path):
    import jobfind.providers.claude_cli as mod

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeCompletedProcess(json.dumps({"is_error": False, "result": "설명"}))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    img = tmp_path / "1.png"
    img.write_bytes(b"fake")

    text = ClaudeCliProvider().run("system", "user prompt", images=[img])

    assert text == "설명"
    idx = captured["cmd"].index("--allowedTools")
    assert captured["cmd"][idx + 1] == "Read"
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert "1.png" in captured["cmd"][2]  # 프롬프트에 이미지 파일명이 안내됨

def test_claude_cli_provider_raises_on_is_error(monkeypatch):
    import jobfind.providers.claude_cli as mod

    monkeypatch.setattr(
        mod.subprocess, "run",
        lambda cmd, **kw: _FakeCompletedProcess(json.dumps({"is_error": True, "result": "실패 사유"})),
    )
    with pytest.raises(RuntimeError, match="실패 사유"):
        ClaudeCliProvider().run("system", "user")

def test_claude_cli_provider_raises_on_nonzero_returncode(monkeypatch):
    import jobfind.providers.claude_cli as mod

    monkeypatch.setattr(
        mod.subprocess, "run",
        lambda cmd, **kw: _FakeCompletedProcess("", returncode=1, stderr="command not found"),
    )
    with pytest.raises(RuntimeError, match="command not found"):
        ClaudeCliProvider().run("system", "user")


# ── CodexCliProvider ─────────────────────────────────────────────────────────

def test_codex_cli_provider_returns_stdout(monkeypatch):
    import jobfind.providers.codex_cli as mod

    monkeypatch.setattr(
        mod.subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess("결과 텍스트\n")
    )
    assert CodexCliProvider().run("system", "user") == "결과 텍스트"

def test_codex_cli_provider_missing_binary_raises_clear_error(monkeypatch):
    import jobfind.providers.codex_cli as mod

    def raise_not_found(cmd, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr(mod.subprocess, "run", raise_not_found)
    with pytest.raises(RuntimeError, match="codex CLI를 찾을 수 없습니다"):
        CodexCliProvider().run("system", "user")


# ── ApiProvider ──────────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_api_provider_anthropic_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        ApiProvider("anthropic").run("system", "user")

def test_api_provider_anthropic_returns_text(monkeypatch):
    import jobfind.providers.api as mod

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"content": [{"type": "text", "text": "안녕하세요"}]})

    monkeypatch.setattr(mod.requests, "post", fake_post)
    text = ApiProvider("anthropic").run("system prompt", "user prompt")

    assert text == "안녕하세요"
    assert captured["json"]["system"] == "system prompt"

def test_api_provider_anthropic_with_image(monkeypatch, tmp_path):
    import jobfind.providers.api as mod

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["json"] = json
        return _FakeResponse({"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr(mod.requests, "post", fake_post)
    img = tmp_path / "1.png"
    img.write_bytes(b"fakepngbytes")

    ApiProvider("anthropic").run("system", "user", images=[img])

    content = captured["json"]["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image"
    assert content[1]["source"]["media_type"] == "image/png"

def test_api_provider_openai_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        ApiProvider("openai").run("system", "user")

def test_api_provider_openai_returns_text(monkeypatch):
    import jobfind.providers.api as mod

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"choices": [{"message": {"content": "hello"}}]})

    monkeypatch.setattr(mod.requests, "post", fake_post)
    assert ApiProvider("openai").run("system", "user") == "hello"

def test_api_provider_invalid_backend_raises():
    with pytest.raises(ValueError):
        ApiProvider("unknown")
