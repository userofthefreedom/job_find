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

## 현재 Git 상태

| 항목 | 내용 |
|---|---|
| 브랜치 | `master` |
| 전체 구현 | Phase 1~4 완료 |
| 마지막 커밋 예정 | Phase 4 X 마커 처리 (`fetch_jobs.py`, 테스트, PROGRESS.md) |

---

## 운용 참고

- 전체 Phase 1~4 구현 완료. Windows 작업 스케줄러 등록 후 운용 가능.
- `config.py` 조건 수정 후 재실행하면 바뀐 조건 즉시 반영.
