# PROGRESS

## Phase 1 — 프로젝트 뼈대 구성 ✅ (2026-06-30 완료)다

### 구현 내용

| 파일 | 내용 |
|---|---|
| `.gitignore` | `.env`, `output/*`, `venv/`, `__pycache__/` 등 제외 |
| `.env.example` | `SARAMIN_ACCESS_KEY=your_access_key_here` |
| `requirements.txt` | `requests==2.32.3`, `python-dotenv==1.0.1` |
| `config.py` | 필터 변수 기본값 (`KEYWORDS`, `LOCATIONS`, `CAREER_TYPE`, `EXP_MIN/MAX`) |
| `output/.gitkeep` | output 디렉토리 추적용 placeholder |
| `fetch_jobs.py` | `main()` 뼈대 — 실행 시 "준비 완료" 출력 |

### Verify Loop 결과

- Test: `python fetch_jobs.py` → "준비 완료" 출력 ✅
- Review: PLAN.md 범위 내 구현 ✅ (UTF-8 stdout 설정은 Phase 2 한국어 출력 대비 선행)
- Verify: Phase 1 Acceptance Criteria 전항목 충족 ✅

---

## Phase 2 — 이중 소스 수집 및 파일 저장 ✅ (2026-07-09 완료)

### 구현 내용 (`fetch_jobs.py` 전면 재작성)

| 함수 | 역할 |
|---|---|
| `load_config()` | `.env`에서 API 키 로드, 없으면 즉시 종료 |
| `ensure_output_dir()` | `output/` 없으면 자동 생성 |
| `fetch_page(api_key, start)` | 단일 페이지 API 호출, HTTPError 즉시 종료 / 네트워크 오류 1회 재시도 |
| `fetch_all(api_key)` | 페이지네이션 루프로 전체 공고 수집 |
| `ts_to_date(ts)` | Unix timestamp → `YYYY-MM-DD` 변환 |
| `normalize(job)` | API 응답 dict → 내부 dict 변환 |
| `format_block(job)` | 내부 dict → txt 블록 문자열 (SPEC.md 5-1 형식 준수) |
| `load_active_ids(path)` | `jobs_all.txt` 파싱 → `[ID]` 줄 추출 |
| `load_dismissed_ids(path)` | `dismissed_ids.txt` 읽기 |
| `write_jobs(jobs, path)` | `jobs_all.txt` append |
| `print_summary(total, new)` | 조회/신규 저장 건수 출력 |

### 구현 함수 목록

| 함수 | 역할 |
|---|---|
| `ensure_output_dir()` | `output/` 없으면 자동 생성 |
| `fetch_saramin_page(page)` | 사람인 검색 1페이지 HTML 요청, 1회 재시도 |
| `parse_saramin_date(text)` | `"~ 08/06(목)"` → `"2026-08-06"` |
| `normalize_saramin(item)` | BS4 Tag → 내부 dict (`id = "saramin_" + rec_idx`) |
| `fetch_saramin_all()` | 페이지네이션 루프 (최대 10페이지) |
| `fetch_wanted_page(offset)` | 원티드 API 1페이지 JSON 요청, 1회 재시도 |
| `_wanted_experience(from, to)` | `annual_from/to` → 경력 텍스트 |
| `normalize_wanted(item)` | API dict → 내부 dict (`id = "wanted_" + id`) |
| `fetch_wanted_all()` | offset 루프 (최대 100건) |
| `_norm_title(title)` | 공백 제거 + 소문자 (유사도 비교용) |
| `deduplicate_cross_platform(s, w)` | 제목 유사도 ≥ 0.85 AND (마감일/지역 일치) → 중복 제거, 사람인 우선 |
| `fetch_all()` | 두 소스 통합 수집 → cross dedup → 반환 |
| `format_block(job)` | `[출처]`, `[ID]` 포함 txt 블록 |
| `load_active_ids(path)` | `jobs_all.txt` 파싱 → 활성 ID set |
| `load_dismissed_ids(path)` | `dismissed_ids.txt` 읽기 |
| `write_jobs(jobs, path)` | `jobs_all.txt` append |
| `print_summary(total, new)` | 타임스탬프 포함 요약 출력 |

### 단위 테스트 결과 (`pytest tests/ -v`)

**22/22 통과** ✅

- `parse_saramin_date` — 정상값 / 빈값 / 패턴 없음 ✅
- `_wanted_experience` — 경력무관 / 신입 / 경력범위 ✅
- `normalize_saramin` — mock HTML 파싱, value 누락 시 None ✅
- `normalize_wanted` — 정상값 / null deadline / key 누락 시 None ✅
- `format_block` — `[출처]`, `[ID]` prefix, 빈 keyword/deadline 줄 생략 ✅
- `load_active_ids` — saramin_/wanted_ prefix ID 추출 ✅
- `load_dismissed_ids` — 파일 읽기 ✅
- `deduplicate_cross_platform` — 동일 제목+마감일 제거 / 다른 공고 유지 / 마감일+지역 모두 다를 때 유지 ✅

---

## Phase 3 — 필터링 ✅ (2026-07-09 완료)

### 구현 내용 (`fetch_jobs.py`에 필터 섹션 추가)

| 함수 | 역할 |
|---|---|
| `filter_keywords(job)` | `KEYWORDS` 중 하나라도 title/keyword에 포함 → 통과 (대소문자 무시) |
| `filter_location(job)` | `LOCATIONS` 중 하나라도 location에 포함 → 통과 |
| `filter_career_type(job)` | `CAREER_TYPE`이 experience에 포함 → 통과 (None이면 전체 허용) |
| `filter_exp_range(job)` | experience에서 숫자 추출 후 `[EXP_MIN, EXP_MAX]`와 범위 겹침 비교. 추출 불가 → 통과 |
| `filter_jobs(jobs)` | 위 4개 AND 조건 적용 |

- `print_summary` 시그니처 변경: `(total, filtered, new)` → 콘솔 출력 `조회 N건 | 필터 통과 M건 | 신규 저장 K건`
- `main()` 에 `filter_jobs()` 삽입

### 단위 테스트 결과 (`pytest tests/ -v`)

**39/39 통과** ✅ (Phase 2 22개 + Phase 3 17개)

- `filter_keywords` — 제목 일치 / keyword 필드 일치 / 불일치 / 빈 리스트 / 대소문자 무시 ✅
- `filter_location` — 일치 / 불일치 / 빈 리스트 ✅
- `filter_career_type` — None 전체허용 / 일치 / 불일치 ✅
- `filter_exp_range` — 둘 다 None / 숫자 없음(경력무관) / 범위 겹침 / 범위 미겹침 / 단일 숫자 ✅
- `filter_jobs` — AND 조건 복합 테스트 ✅

---

## Phase 4 — X 마커 처리 ✅ (2026-07-09 완료)

### 구현 내용 (`fetch_jobs.py`에 X 마커 섹션 추가)

| 함수 | 역할 |
|---|---|
| `parse_blocks(text)` | 전체 텍스트를 `═×48` 경계 기준 블록 리스트로 파싱 |
| `is_dismissed(block)` | 블록 내 `[X]` 줄 존재 여부 확인 (대소문자 무시) |
| `extract_id(block)` | `[ID]` 줄에서 ID 문자열 추출, 없으면 `None` 반환 |
| `append_dismissed_ids(ids, path)` | 추출한 ID → `dismissed_ids.txt` append |
| `rewrite_jobs_file(blocks, path)` | 남은 블록으로 `jobs_all.txt` 덮어쓰기 |
| `process_x_markers(jobs_path, dismissed_path)` | 위 함수들 통합 실행, 제거 건수 반환 |

- `main()` 최초 단계에 `process_x_markers()` 삽입
- `print_summary` 시그니처 변경: `(total, x_removed, filtered, new)` → `X 처리: N건` 포함 출력
- `[X]` 있어도 `[ID]` 없는 블록은 보존 (안전장치)

### 단위 테스트 결과 (`pytest tests/ -v`)

**51/51 통과** ✅ (Phase 2 22개 + Phase 3 17개 + Phase 4 12개)

- `parse_blocks` — 정상 블록 분리 / 블록 2개 / 빈 파일 / 짝 안 맞는 구분자 무시 ✅
- `is_dismissed` — `[X]` 포함 / 미포함 / `[x]` 소문자 ✅
- `extract_id` — ID 있음 / 없음 ✅
- `process_x_markers` — 파일 없음 / X 블록 제거+dismissed 기록 / `[X]` 있지만 `[ID]` 없는 블록 보존 / 정상 블록 보존 ✅

---

## Phase 8 — 패키지 재구조화 ✅ (2026-08-14 완료)

`fetch_jobs.py` 단일 스크립트를 `jobfind/` 패키지로 순수 리팩터링(로직 변경 없음). `config.py`,
`collectors/{saramin,wanted}.py`, `dedup.py`, `filters.py`, `storage.py`, `cli.py`로 분리하고
`jobfind.py`를 진입점으로 뒀다. 기존 51개 테스트를 새 경로로 이관해 전부 통과, 실제
`python jobfind.py collect` 실행 결과가 기존 스크립트와 동일함을 확인.

---

## Phase 9 — 관련성 평가 ✅ (2026-08-14 완료)

`jobfind/relevance.py`에 HF 임베딩(`jhgan/ko-sroberta-multitask`) 기반 관련성 평가 추가.
`config.ini [relevance]`에 `roles`(직무)/`domains`(도메인)/`top_n`을 입력하면 결합 점수로
정렬해 상위 `top_n`건만 남긴다. 처음 구현한 `role_description`+`threshold` 이진 필터는
실데이터 검증에서 비슷한 공고끼리 판정이 갈리는 문제가 있어 랭킹 방식으로 재설계했다.

### 테스트 결과

76개 통과. mock 모델로 결합 점수/랭킹/top_n 로직 검증.

---

## Phase 10 — 수동 추가 + 자소서 선택 마커 ✅ (2026-08-14 완료)

- `jobfind.py add <url>` — 사람인은 `og:description` 메타태그, 원티드는 상세 API로 단건 조회
- `jobfind.py select` — `[자소서]` 마커된 공고에 `output/cover_letters/<ID>/materials/` 폴더 준비

### 테스트 결과

92개 통과. 실제 URL로 추가/중복 스킵/materials 폴더 생성까지 실데이터로 확인.

---

## Phase 11 — Provider 추상화 계층 ✅ (2026-08-14 완료)

`jobfind/providers/{claude_cli,codex_cli,api}.py` — `Provider.run(system, user, images) -> str`
인터페이스로 4개 백엔드(`claude_cli`/`codex_cli`/`api:anthropic`/`api:openai`) 통일.
`claude -p`는 mock 없이 실제 호출로 텍스트/이미지 양쪽 경로 검증 완료. `codex_cli`는 미설치
환경이라 공개 규약 기준으로만 작성.

### 테스트 결과

110개 통과.

---

## Phase 12 — 자소서 오케스트레이션 파이프라인 ✅ (2026-08-14 완료)

`jobfind/pipeline/{prompts,orchestrator}.py` — 선택된 공고마다 계획 → 계획평가 →
(NEEDS_REVISION이면 재작성) → 작성 → 초안평가를 실행, `output/cover_letters/<ID>/`에 저장.
실데이터 검증(claude_cli, 실제 공고 2건)에서 격리된 평가 agent가 실제로 구체적인 피드백을
냈고, 재작성 루프도 정상 동작함을 확인. 검증 중 "planner/writer가 목록 요약만 보고 작성해
품질이 떨어진다"는 문제를 발견해 `fetch_posting_text()`(원티드 상세 API 활용, 사람인은 JS
렌더링 한계로 미적용)를 추가로 구현.

### 테스트 결과

135개 통과.

---

## Phase 13 — 문서 정리 ✅ (2026-08-14 완료)

`CLAUDE.md`/`README.md`/`docs/PRD.md`/`docs/SPEC.md`/`docs/PLAN.md`/`docs/PROGRESS.md`(이 문서)를
v3 재설계(Phase 8~13) 결과에 맞게 갱신.

---

## 현재 Git 상태

| 항목 | 내용 |
|---|---|
| 브랜치 | `master` |
| 전체 구현 | Phase 1~4(v1) + Phase 8~13(v3 재설계) 완료. Phase 5~7(v3 로드맵 초안)은 미착수 |

---

## 운용 참고

- 전체 Phase 1~4·8~13 구현 완료. Windows 작업 스케줄러 무인 실행은 v3에서 폐기 —
  `python jobfind.py <command>`를 사용자가 직접 실행한다 (`README.md` 참고).
- `config.ini` 조건 수정 후 재실행하면 바뀐 조건 즉시 반영.
