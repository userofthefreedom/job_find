from __future__ import annotations
from pathlib import Path

from jobfind.pipeline.writing_strategy import (
    WRITING_STRATEGY,
    WRITING_STRATEGY_EVALUATION_NOTE,
)

# 계획/작성/평가 프롬프트가 공통으로 지켜야 할 자소서 스타일 원칙. 각 단계가 독립된 AI
# 호출이라 이 원칙을 시스템 프롬프트마다 공유하지 않으면 라운드마다 다른 지침을 냈다
# (예: 계획 평가자는 "약점을 정면으로 언급하라", 초안 평가자는 "반복하지 마라"고 서로 다른
# 방향을 제시해 초안이 약점을 여러 섹션에서 반복 고백하는 문제로 이어졌다 — 실사용 확인).
COVER_LETTER_STYLE_PRINCIPLES = (
    "자소서 스타일 원칙(모든 단계에서 지킬 것):\n"
    "- 약점·자격 미달은 전체 문서에서 최대 1회만, 짧게 인정한 뒤 곧바로 강점이나 극복 노력으로 "
    "전환한다. 여러 섹션에서 반복해서 고백하지 않는다.\n"
    "- 지원자 본인의 경험이 아닌 회사 관련 사실(수치·리뷰 인용 등)은, 1차 출처를 직접 확인하지 "
    "못했다면 따옴표로 감싼 직접인용을 쓰지 말고 완화된 어조(\"~로 알려져 있다\")로만 표현한다. "
    "직접인용부호는 실제로 원문을 확인한 경우에만 쓴다. 특히 비상장 기업의 매출 성장률처럼 "
    "소수점 단위로 정밀하지만 실제로 공개돼 있을 가능성이 낮은 수치는, 헤지 어조를 붙이는 "
    "것만으로는 부족하다 — 아예 쓰지 않고 공고 원문에 명시된 사실만으로 논거를 구성한다."
)

# materials/notes.md는 사용자가 직접 채워넣는 유일한 채널이라, 여기 실제 자소서 문항이
# 들어있을 수 있다는 걸 프롬프트에서 명시적으로 알려야 한다 — 그냥 "[추가 메모]"로만
# 라벨링하면 planner가 표준 4문항 가정을 우선시해버리는 문제가 실사용 중 반복 확인됐다.
_NOTES_LABEL = "[사용자 제공 정보 — 실제 자소서 문항이 포함되어 있을 수 있음, 있다면 최우선으로 따를 것]"


def _read_notes(materials_dir: Path) -> str:
    notes_path = materials_dir / "notes.md"
    if notes_path.exists():
        return notes_path.read_text(encoding="utf-8")
    return ""


def planner_prompt(job_text: str, profile: str, materials_dir: Path) -> tuple[str, str]:
    system = (
        "너는 채용 공고에 맞춘 자기소개서 작성 계획을 세우는 전문가다. "
        "지원자의 프로필에서 이 공고와 가장 관련 있는 경험을 골라, 자소서에 어떤 순서로 "
        "무엇을 강조할지 구체적인 개요(outline)를 만든다. 아직 실제 문장을 쓰지 않는다. "
        "웹 검색·웹 조회 도구를 쓸 수 있다면, 공고 정보에 이미 포함된 내용(DART 기업개황 등)을 "
        "넘어 회사 최근 뉴스·홈페이지·업계 동향을 실제로 검색해 계획에 구체적으로 반영하라 — "
        "회사명을 일반명사처럼 언급만 하는 진부한 지원동기를 피하는 게 목적이다. 도구가 없거나 "
        "검색이 실패해도 계획 수립 자체를 멈추지 말고 가진 정보로 최선을 다해 계획을 세워라. "
        "사용자 제공 정보에 실제 자소서 문항(문항 제목·글자수 제한 포함)이 있으면 반드시 그 "
        "문항 순서와 표현을 그대로 따라 계획을 세우고, 그런 정보가 없을 때만 표준 4문항 구성 "
        "(지원동기·직무 경험·강점·입사 후 포부)으로 가정하라.\n\n"
        f"{COVER_LETTER_STYLE_PRINCIPLES}\n\n{WRITING_STRATEGY}"
    )
    user = f"[공고 정보]\n{job_text}\n\n[지원자 프로필]\n{profile}\n\n"
    notes = _read_notes(materials_dir)
    if notes:
        user += f"{_NOTES_LABEL}\n{notes}\n\n"
    user += "위 정보를 바탕으로 이 공고에 지원할 자소서의 작성 계획(개요)을 세워라."
    return system, user


def planner_revision_prompt(
    job_text: str, profile: str, materials_dir: Path, previous_plan: str, feedback: str
) -> tuple[str, str]:
    system = (
        "너는 채용 공고에 맞춘 자기소개서 작성 계획을 세우는 전문가다. "
        "이전에 세운 계획에 대한 평가 피드백을 반영해 계획을 개선한다. "
        "웹 검색·웹 조회 도구를 쓸 수 있고 피드백이 회사 정보 부족을 지적했다면, 실제로 "
        "검색해 구체적인 사실을 반영하라. 도구가 없거나 검색이 실패해도 개선 작업 자체를 "
        "멈추지 말고 가진 정보로 최선을 다해 계획을 다시 작성하라. 사용자 제공 정보에 실제 "
        "자소서 문항(문항 제목·글자수 제한 포함)이 있으면 반드시 그 문항 순서와 표현을 그대로 "
        "따라 계획을 세우고, 그런 정보가 없을 때만 표준 4문항 구성으로 가정하라.\n\n"
        f"{COVER_LETTER_STYLE_PRINCIPLES}\n\n{WRITING_STRATEGY}"
    )
    user = f"[공고 정보]\n{job_text}\n\n[지원자 프로필]\n{profile}\n\n"
    notes = _read_notes(materials_dir)
    if notes:
        user += f"{_NOTES_LABEL}\n{notes}\n\n"
    user += (
        f"[이전 계획]\n{previous_plan}\n\n"
        f"[평가 피드백]\n{feedback}\n\n"
        "위 피드백을 반영해 개선된 계획을 다시 작성하라."
    )
    return system, user


def plan_evaluator_prompt(job_text: str, plan: str) -> tuple[str, str]:
    system = (
        "너는 자소서 작성 계획을 냉정하게 검토하는 평가자다. 계획 작성자와는 독립적으로 "
        "판단한다. 계획이 공고 요구사항과 잘 맞는지, 진부하거나 추상적이지 않은지 확인하라. "
        "첫 줄에 정확히 'OK' 또는 'NEEDS_REVISION' 중 하나만 쓰고, 그 아래에 구체적인 "
        "수정 제안을 적어라.\n\n"
        f"{COVER_LETTER_STYLE_PRINCIPLES}\n\n{WRITING_STRATEGY}\n\n{WRITING_STRATEGY_EVALUATION_NOTE}"
    )
    user = f"[공고 정보]\n{job_text}\n\n[작성 계획]\n{plan}\n\n이 계획을 평가하라."
    return system, user


def writer_prompt(job_text: str, profile: str, plan: str) -> tuple[str, str]:
    system = (
        "너는 자기소개서를 실제로 작성하는 전문 라이터다. 주어진 계획을 바탕으로 "
        "지원자의 실제 경험만 사용해 자연스러운 한국어 자소서 초안을 작성한다. "
        "과장하거나 없는 경험을 지어내지 않는다. "
        "공고에 실제 자소서 문항이나 상세 요건이 부족해도 초안 작성 자체를 거부하지 마라 — "
        "계획에 이미 실제 문항 기반 구성(문항 제목·글자수 제한 등)이 정해져 있으면 반드시 "
        "그 구성을 그대로 따르고, 계획에도 그런 정보가 없을 때만 가장 흔한 표준 구성(지원동기· "
        "직무 경험·강점·입사 후 포부)으로 가정해 반드시 실제 자소서 본문을 끝까지 작성하라. "
        "어떤 부분이 가정이고 원문 확인 시 무엇을 다시 물어야 하는지는 draft 본문과 분리해 "
        "안내 문구로만 짧게 남겨라.\n\n"
        f"{COVER_LETTER_STYLE_PRINCIPLES}\n\n{WRITING_STRATEGY}"
    )
    user = (
        f"[공고 정보]\n{job_text}\n\n"
        f"[지원자 프로필]\n{profile}\n\n"
        f"[작성 계획]\n{plan}\n\n"
        "위 계획에 따라 자소서 초안을 작성하라."
    )
    return system, user


def writer_revision_prompt(
    job_text: str, profile: str, plan: str, previous_draft: str, feedback: str
) -> tuple[str, str]:
    system = (
        "너는 자기소개서를 실제로 작성하는 전문 라이터다. 이전에 작성한 초안에 대한 평가 "
        "피드백을 반영해 초안을 개선한다. 지원자의 실제 경험만 사용하고 과장하거나 없는 "
        "경험을 지어내지 않는다. 초안 작성 자체를 거부하지 말고 반드시 개선된 자소서 본문을 "
        "끝까지 다시 작성하라.\n\n"
        f"{COVER_LETTER_STYLE_PRINCIPLES}\n\n{WRITING_STRATEGY}"
    )
    user = (
        f"[공고 정보]\n{job_text}\n\n"
        f"[지원자 프로필]\n{profile}\n\n"
        f"[작성 계획]\n{plan}\n\n"
        f"[이전 초안]\n{previous_draft}\n\n"
        f"[평가 피드백]\n{feedback}\n\n"
        "위 피드백을 반영해 개선된 자소서 초안을 다시 작성하라."
    )
    return system, user


def verify_prompt(job_text: str, profile: str, posting_text: str) -> tuple[str, str]:
    system = (
        "너는 채용 공고 목록 요약과 실제 상세 자격요건을 대조해 지원자가 실제로 지원 "
        "가능한지 검수하는 전문가다. 목록 페이지 요약(경력·조건)이 상세 요건과 다를 수 "
        "있다는 점에 특히 주의하라 — 예: 목록엔 '경력'이라고만 나오지만 상세에는 '유관 "
        "경력 5년 이상'처럼 구체적인 하한이 있는 경우. 이미지가 주어지면 그 안의 텍스트를 "
        "직접 읽어 자격요건·우대사항을 확인하라.\n\n"
        "첫 줄에 정확히 'PASS' 또는 'CONCERN' 또는 'UNKNOWN' 중 하나만 쓰고(마크다운 볼드나 "
        "다른 기호로 감싸지 말고 그 단어만 단독으로), 그 아래에 왜 그렇게 판단했는지 1~3문장으로 "
        "근거를 적어라. 목록 요약과 실제 요건이 다르지 "
        "않고 지원자 프로필이 요건을 충족하면 PASS, 요건에 명백히 못 미치면(예: 필요 "
        "경력 연차가 지원자 경력보다 한참 많음) CONCERN, 상세 내용을 전혀 확인할 수 "
        "없었던 경우(이미지가 안 읽히는 등)는 UNKNOWN이다. 애매하면 CONCERN으로 판단해 "
        "사용자가 직접 보게 하라."
    )
    parts = [f"[공고 목록 요약]\n{job_text}", f"[지원자 프로필]\n{profile}"]
    if posting_text:
        parts.append(f"[상세 공고 텍스트]\n{posting_text}")
    user = "\n\n".join(parts) + "\n\n이 공고의 상세 요건과 지원자 프로필을 대조해 검수하라."
    return system, user


def draft_evaluator_prompt(job_text: str, draft: str) -> tuple[str, str]:
    system = (
        "너는 자소서 초안을 냉정하게 검토하는 평가자다. 작성자와는 독립적으로 판단한다. "
        "진부한 표현, 공고와의 연관성 부족, 논리적 비약을 짚어내고 구체적인 수정 방안을 "
        "제시하라. 첫 줄에 정확히 'OK' 또는 'NEEDS_REVISION' 중 하나만 쓰고, 그 아래에 "
        "구체적인 수정 제안을 적어라.\n\n"
        f"{COVER_LETTER_STYLE_PRINCIPLES}\n\n{WRITING_STRATEGY}\n\n{WRITING_STRATEGY_EVALUATION_NOTE}"
    )
    user = f"[공고 정보]\n{job_text}\n\n[자소서 초안]\n{draft}\n\n이 초안을 평가하라."
    return system, user
