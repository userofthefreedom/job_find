from __future__ import annotations
import base64
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_MODEL = "claude-sonnet-5"
_OPENAI_MODEL = "gpt-4o"
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _guess_media_type(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix.lower(), "image/png")


def _encode_image(path: Path) -> tuple[str, str]:
    return _guess_media_type(path), base64.b64encode(path.read_bytes()).decode("ascii")


class ApiProvider:
    """Anthropic/OpenAI Messages·Chat Completions API를 requests로 직접 호출하는 provider.
    키는 .env의 ANTHROPIC_API_KEY / OPENAI_API_KEY에서 읽는다 (호출당 과금 발생)."""

    def __init__(self, backend: str):
        if backend not in ("anthropic", "openai"):
            raise ValueError(f"알 수 없는 api provider입니다: {backend!r}")
        self.backend = backend

    def run(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[Path] | None = None,
        extra_tools: list[str] | None = None,
    ) -> str:
        # extra_tools(예: WebSearch)는 직접 API 호출에 대응하는 서버사이드 도구 연동이
        # 없어 지금은 무시한다 — 인터페이스 호환을 위해 인자만 받는다.
        images = images or []
        if self.backend == "anthropic":
            return self._run_anthropic(system_prompt, user_prompt, images)
        return self._run_openai(system_prompt, user_prompt, images)

    def _run_anthropic(self, system_prompt: str, user_prompt: str, images: list[Path]) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY가 .env에 설정되어 있지 않습니다.")

        content: list[dict] = [{"type": "text", "text": user_prompt}]
        for img in images:
            media_type, data = _encode_image(img)
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            })

        resp = requests.post(
            _ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": _ANTHROPIC_MODEL,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": content}],
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(block.get("text", "") for block in data.get("content", []))

    def _run_openai(self, system_prompt: str, user_prompt: str, images: list[Path]) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

        content: list[dict] = [{"type": "text", "text": user_prompt}]
        for img in images:
            media_type, data = _encode_image(img)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{data}"},
            })

        resp = requests.post(
            _OPENAI_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": _OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
