from __future__ import annotations
from pathlib import Path
from typing import Protocol


class Provider(Protocol):
    def run(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[Path] | None = None,
        extra_tools: list[str] | None = None,
    ) -> str:
        """system_prompt/user_prompt(+선택적 images)로 한 번의 격리된 호출을 실행하고
        생성된 텍스트를 반환한다. 호출마다 이전 대화 맥락을 공유하지 않는다.

        extra_tools는 claude_cli에서만 실제로 동작하는 선택적 힌트다(예: ["WebSearch",
        "WebFetch"]로 회사 리서치를 허용). 이를 지원하지 않는 provider는 그냥 무시한다."""
        ...


def get_provider(spec: str) -> Provider:
    if spec == "claude_cli":
        from jobfind.providers.claude_cli import ClaudeCliProvider

        return ClaudeCliProvider()
    if spec == "codex_cli":
        from jobfind.providers.codex_cli import CodexCliProvider

        return CodexCliProvider()
    if spec.startswith("api:"):
        from jobfind.providers.api import ApiProvider

        return ApiProvider(spec.split(":", 1)[1])
    raise ValueError(f"알 수 없는 provider입니다: {spec!r}")
