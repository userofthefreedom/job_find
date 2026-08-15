# PROGRESS

_요약본 — 전체 세션별 상세 기록은 `docs/history/PROGRESS.md` 참고_

## 완료 현황

| Phase | 내용 | 상태 |
|---|---|---|
| 1~4 (v1) | 프로젝트 뼈대, 이중 소스 수집(사람인+원티드), 필터링, X 마커 | ✅ 완료 |
| 8 | `fetch_jobs.py` 단일 스크립트 → `jobfind/` 패키지 재구조화 | ✅ 완료 |
| 9 | HF 임베딩 기반 관련성 평가(직무x도메인 랭킹) 추가 | ✅ 완료 |
| 10 | 수동 추가(`add`) + 자소서 선택 마커(`select`) | ✅ 완료 |
| 11 | AI provider 추상화 계층(`claude_cli`/`codex_cli`/`api:*`) | ✅ 완료 |
| 12 | 자소서 오케스트레이션 파이프라인(`write`) | ✅ 완료 |
| 13 | 문서 정리(v3 재설계 반영) | ✅ 완료 |
| 14 | 실사용 피드백 3건 반영(`.env` 통합, 관련성 결합식 수정, writer 작성거부 방지) | ✅ 완료 |
| 15 | 관련성 모델 교체, DART 연동, planner 웹 검색 허용 | ✅ 완료 |
| 5~7 (구 v3 로드맵) | 실행 로그/이상 감지, 필터 고도화, 지원 상태 추적 | ⏳ 미착수 (`docs/PLAN.md` 참고) |

## 현재 Git 상태

- 브랜치: `master`
- 마지막 커밋: `4ccd548` "Phase 15: 관련성 모델 교체 + DART 연동 + planner 웹 검색 허용"
- 전체 구현: Phase 1~4·8~15 완료. Phase 5~7만 미착수.

## 운용 참고

- Windows 작업 스케줄러 무인 실행은 v3에서 폐기 — `python jobfind.py <command>`를 사용자가 직접 실행한다 (`README.md` 참고).
- `.env` 조건 수정 후 재실행하면 바뀐 조건 즉시 반영.
- 각 Phase의 구현 세부사항·검증 로그·시행착오 기록은 `docs/history/PROGRESS.md`에 그대로 보존돼 있다.
