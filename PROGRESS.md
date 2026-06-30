# PROGRESS

## Phase 1 — 프로젝트 뼈대 구성 ✅ (2026-06-30 완료)

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

## Phase 2 — API 조회 및 파일 저장 🔄 (2026-06-30 구현 완료, API 검증 대기)

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

### 단위 테스트 결과 (API 키 없이 실행)

- `ts_to_date` — 정상값 / 빈값 / 잘못된값 처리 ✅
- `normalize` — mock API 응답으로 필드 매핑 확인 ✅
- `format_block` — DIVIDER 포함, `[ID]` 줄 위치, keyword 없을 때 `[직무]` 줄 생략 ✅
- `load_active_ids` — 저장된 블록에서 ID 추출 ✅
- 중복 방지 — 동일 job 2회 저장 시 skip_ids로 차단 ✅
- 빈 keyword / 빈 deadline → 해당 줄 전체 생략 ✅

### 미완료 (다음 세션에서 시작)

- 실제 API 호출 후 `output/jobs_all.txt` 생성 확인
- 같은 날 2회 실행 시 중복 없음 확인
- Phase 2 Acceptance Criteria 최종 통과 후 커밋

---

## 현재 Git 상태 (2026-06-30 세션 종료 시점)

| 항목 | 내용 |
|---|---|
| 브랜치 | `master` |
| 워킹 트리 | 클린 (미커밋 변경 없음) |
| 마지막 커밋 | `37eaf5e` — `26.06.30 phase 2 start` (fetch_jobs.py Phase 2 구현) |
| 그 전 커밋 | `e393d7c` — `26.06.30 Phase 1 - 프로젝트 뼈대 구성&review` |

---

## 다음 세션 주의사항

1. **API 키 먼저** — `.env` 파일 생성 후 `python fetch_jobs.py` 실행. `.env`는 `.gitignore`에 포함되어 있어 커밋되지 않음.
2. **Phase 2 Verify Loop 완료** — API 실행 결과 확인 후 PLAN.md 완료 기준 충족 여부 판단. 통과해야 Phase 3 진행 가능.
3. **venv 재생성 불필요** — `venv/`는 이미 로컬에 있음. `.\venv\Scripts\Activate.ps1` 또는 `.\venv\Scripts\python.exe`로 바로 실행.
4. **Phase 3는 필터링** — `config.py` 조건 4개(키워드·지역·경력유형·경력연차)를 AND로 묶는 `filter_jobs()` 추가. `fetch_jobs.py`만 수정.
