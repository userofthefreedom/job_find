# PLAN — 사람인 채용 공고 자동 수집기

_작성일: 2026-06-30 | 기반 문서: PRD.md, SPEC.md_

---

## 구현 전략

전체를 4개 Phase로 나눈다. 각 Phase는 독립적으로 실행·검증 가능한 단위다.
Phase가 끝날 때마다 테스트를 실행하고 사용자 확인 후 다음 Phase로 진행한다.

---

## Phase 1 — 프로젝트 초기 설정

**목표**: 코드 없이 실행 가능한 프로젝트 뼈대 완성

### 작업 목록

- [ ] `.gitignore` 생성 (`.env`, `output/`, `venv/`, `__pycache__/`)
- [ ] `.env.example` 생성
- [ ] `requirements.txt` 생성 (`requests==2.32.3`, `python-dotenv==1.0.1`)
- [ ] `config.py` 생성 — 필터 변수 기본값 포함
- [ ] `output/` 디렉토리 placeholder 생성 (`.gitkeep`)
- [ ] `fetch_jobs.py` 생성 — `main()` 뼈대만 (실행 시 "준비 완료" 출력)

### 완료 기준

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt   # 오류 없이 설치
python fetch_jobs.py              # "준비 완료" 출력
```

---

## Phase 2 — API 조회 및 파일 저장

**목표**: 사람인 API 호출 → 결과를 `jobs_all.txt`에 저장 (필터 없이 전량)

### 작업 목록

- [ ] `load_config()` — `.env`에서 API 키 로드, 없으면 오류 후 종료
- [ ] `ensure_output_dir()` — `output/` 없으면 생성
- [ ] `fetch_page(start)` — 단일 페이지 API 호출, HTTP 오류 처리 (1회 재시도)
- [ ] `fetch_all()` — 페이지네이션 루프로 전체 공고 수집
- [ ] `normalize(job)` — API 응답 → 내부 dict 변환
- [ ] `format_block(job)` — 내부 dict → txt 블록 문자열 변환 (`[ID]` 줄 포함)
- [ ] `write_jobs(jobs)` — `jobs_all.txt`에 append
- [ ] `load_active_ids()` — `jobs_all.txt` 파싱, `[ID]` 줄 추출
- [ ] `load_dismissed_ids()` — `dismissed_ids.txt` 읽기
- [ ] 중복 건너뜀 로직 — `skip_ids = active | dismissed`
- [ ] `print_summary()` — 조회/저장 건수 콘솔 출력

### 완료 기준

```powershell
python fetch_jobs.py
# output/jobs_all.txt 에 공고 블록이 생성됨
# 같은 날 두 번 실행해도 중복 추가 없음
```

---

## Phase 3 — 필터링

**목표**: `config.py` 조건에 맞는 공고만 저장

### 작업 목록

- [ ] `filter_keywords(job)` — `title` / `keyword` 필드에 `KEYWORDS` 포함 여부
- [ ] `filter_location(job)` — `location` 에 `LOCATIONS` 포함 여부
- [ ] `filter_career_type(job)` — `experience` 에 `CAREER_TYPE` 문자열 포함 여부
- [ ] `filter_exp_range(job)` — `experience`에서 숫자 추출 후 `EXP_MIN`/`EXP_MAX` 비교
  - 추출 불가(경력무관 등) → 통과
- [ ] `filter_jobs(jobs)` — 위 4개 필터를 AND 조건으로 묶어 적용
- [ ] `fetch_jobs.py`의 메인 흐름에 `filter_jobs()` 삽입

### 완료 기준

```python
# config.py 조건 예시
KEYWORDS  = ["Python", "백엔드"]
LOCATIONS = ["서울"]
CAREER_TYPE = "경력"
EXP_MIN, EXP_MAX = 1, 5
```

```powershell
python fetch_jobs.py
# jobs_all.txt 에 조건에 맞는 공고만 저장됨
# 콘솔에 "조회: N건 | 필터 통과: M건 | 신규 저장: K건" 출력됨
```

---

## Phase 4 — X 마커 처리

**목표**: 사용자가 표시한 X 마커 공고를 파일에서 제거하고 영구 제외

### 작업 목록

- [ ] `parse_blocks(text)` — `jobs_all.txt` 전체 텍스트를 블록 리스트로 파싱
  - 블록 경계: `═` 48개로만 이루어진 줄
- [ ] `is_dismissed(block)` — 블록 내 `[X]` 또는 `[x]` 줄 존재 여부 확인
- [ ] `extract_id(block)` — 블록에서 `[ID]` 줄 파싱해 ID 문자열 반환
  - `[ID]` 없는 블록 → `None` 반환, 보존 처리
- [ ] `append_dismissed_ids(ids)` — 추출한 ID → `dismissed_ids.txt` append
- [ ] `rewrite_jobs_file(blocks)` — X 마커 블록 제거 후 나머지로 파일 덮어쓰기
- [ ] `process_x_markers()` — 위 함수들을 묶어 실행 흐름의 2단계에 삽입
- [ ] 콘솔 출력: `[X] 처리: N건 제거됨`

### 완료 기준

```
# jobs_all.txt 에 [X] 줄 추가 후 실행
python fetch_jobs.py
# → [X] 블록이 파일에서 사라짐
# → 해당 ID가 dismissed_ids.txt 에 추가됨
# → 이후 실행에서 해당 공고가 다시 저장되지 않음
```

---

## 전체 실행 흐름 (Phase 4 완료 후)

```
python fetch_jobs.py
  │
  ├─ [초기화] API 키 로드, output/ 확인
  │
  ├─ [X 마커] jobs_all.txt 에서 [X] 블록 탐색
  │             → 해당 ID를 dismissed_ids.txt 에 추가
  │             → [X] 블록 제거 후 파일 재작성
  │
  ├─ [중복 기준] active_ids + dismissed_ids 합산
  │
  ├─ [수집] 사람인 API 페이지네이션 전체 조회
  │
  ├─ [필터] config.py 조건 적용 (키워드·지역·경력유형·경력연차)
  │
  ├─ [저장] skip_ids 에 없는 공고만 jobs_all.txt 에 append
  │
  └─ [요약] 조회 N건 | X 처리 M건 | 필터 통과 K건 | 신규 저장 J건
```

---

## 파일 생성 순서 요약

| Phase | 생성 / 수정 파일 |
|---|---|
| 1 | `.gitignore`, `.env.example`, `requirements.txt`, `config.py`, `fetch_jobs.py` (뼈대) |
| 2 | `fetch_jobs.py` (API 조회·저장·중복 제거) |
| 3 | `fetch_jobs.py` (필터 함수 추가) |
| 4 | `fetch_jobs.py` (X 마커 처리 추가) |

---

## 미구현 (Phase 2 이후 검토)

- `dismissed_ids.txt`가 수만 건 이상으로 커졌을 때 set 대신 SQLite로 전환
- `config.py` 조건 변경 이력 추적
- 알림 기능 (이메일, 카카오톡 등)

---

## 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-06-30 | 최초 작성 |
