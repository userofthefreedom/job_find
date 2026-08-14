from __future__ import annotations
import json
import subprocess
import tempfile
from pathlib import Path


class ClaudeCliProvider:
    """Claude Code CLI(`claude -p`)를 헤드리스로 호출하는 provider.

    호출마다 독립된 subprocess라 이전 대화 맥락을 공유하지 않는다 (격리 보장).
    cwd를 이 프로젝트 밖(images가 있으면 그 materials 폴더, 없으면 임시 폴더)으로
    잡아 이 프로젝트의 CLAUDE.md·코드가 우연히 프롬프트에 섞여 들어가지 않게 한다.
    """

    def run(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[Path] | None = None,
        extra_tools: list[str] | None = None,
    ) -> str:
        images = images or []
        extra_tools = extra_tools or []
        cwd = str(images[0].parent) if images else tempfile.gettempdir()
        prompt = user_prompt
        allowed = list(extra_tools)
        if images:
            names = "\n".join(f"- {img.name}" for img in images)
            prompt += f"\n\n다음 이미지 파일을 Read 툴로 읽고 참고하라 (현재 작업 폴더 기준 경로):\n{names}"
            allowed.append("Read")

        cmd = [
            "claude", "-p", prompt,
            "--append-system-prompt", system_prompt,
            "--output-format", "json",
            "--allowedTools", " ".join(allowed),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=cwd,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI 실행 실패: {result.stderr.strip()}")
        payload = json.loads(result.stdout)
        if payload.get("is_error"):
            raise RuntimeError(f"claude CLI 오류: {payload.get('result')}")
        return payload.get("result", "")
