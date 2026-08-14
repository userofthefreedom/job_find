from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path


class CodexCliProvider:
    """OpenAI Codex CLI(`codex exec`)를 헤드리스로 호출하는 provider.

    이 프로젝트를 만든 환경에는 codex CLI가 설치되어 있지 않아 실제 플래그를
    실행으로 검증하지 못했다. 공개된 `codex exec <prompt>` 비대화형 실행
    방식을 기준으로 작성했으며, 실제 사용 전 `codex --help`로 아래 명령/플래그를
    재확인하고 필요하면 이 파일을 맞춰 수정해야 한다.
    """

    def run(self, system_prompt: str, user_prompt: str, images: list[Path] | None = None) -> str:
        images = images or []
        cwd = str(images[0].parent) if images else tempfile.gettempdir()
        prompt = f"{system_prompt}\n\n{user_prompt}"
        if images:
            names = "\n".join(f"- {img.name}" for img in images)
            prompt += f"\n\n다음 이미지 파일을 읽고 참고하라 (현재 작업 폴더 기준 경로):\n{names}"

        cmd = ["codex", "exec", prompt]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", timeout=180, cwd=cwd,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "codex CLI를 찾을 수 없습니다. 설치 후 `codex --help`로 실제 플래그를 "
                "확인하고 jobfind/providers/codex_cli.py를 맞춰 수정하세요."
            ) from e
        if result.returncode != 0:
            raise RuntimeError(f"codex CLI 실행 실패: {result.stderr.strip()}")
        return result.stdout.strip()
