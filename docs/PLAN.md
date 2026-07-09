# PLAN — 사람인 채용 공고 자동 수집기

_작성일: 2026-06-30 | 기반 문서: PRD.md, SPEC.md_

---

## 구현 전략

전체를 여러 Phase로 나눈다. 각 Phase는 독립적으로 실행·검증 가능한 단위다.
Phase가 끝날 때마다 테스트를 실행하고 사용자 확인 후 다음 Phase로 진행한다.

Phase 1~4는 v1(최초 구현), Phase 5~7은 v3 로드맵(2026-07-10 계획, 구현 미착수)이다.
v2(config.ini 전환, 실데이터 검증 기반 필터 수정)는 별도 Phase 없이 Phase 1~4 결과물에 대한
개선 작업으로 진행되어 `docs/SPEC.md` 변경 이력에 기록되어 있다.

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

## Phase 2 — 이중 소스 수집 및 파일 저장

**목표**: 사람인 스크래핑 + 원티드 API 호출 → 결과를 `jobs_all.txt`에 저장 (필터 없이 전량)

### 작업 목록

- [ ] `ensure_output_dir()` — `output/` 없으면 생성
- [ ] `fetch_saramin_page(page)` — 사람인 검색 페이지 1페이지 HTML 요청, HTTP 오류 1회 재시도
- [ ] `fetch_saramin_all()` — 페이지네이션 루프, `normalize_saramin()` 적용, 내부 dict 리스트 반환
- [ ] `normalize_saramin(item)` — HTML 파싱 결과 → 내부 dict (`id` = `"saramin_" + rec_idx`)
- [ ] `fetch_wanted_page(offset)` — 원티드 API 1페이지 JSON 요청, HTTP 오류 1회 재시도
- [ ] `fetch_wanted_all()` — offset 루프, `normalize_wanted()` 적용, 내부 dict 리스트 반환
- [ ] `normalize_wanted(item)` — JSON 응답 → 내부 dict (`id` = `"wanted_" + id`)
- [ ] `_norm_title()` + `deduplicate_cross_platform(saramin, wanted)` — 제목 유사도 ≥ 0.85 AND (마감일·지역 일치) → 중복 제거, 사람인 우선
- [ ] `fetch_all()` — `deduplicate_cross_platform(fetch_saramin_all(), fetch_wanted_all())` 반환
- [ ] `format_block(job)` — 내부 dict → txt 블록 문자열 (`[출처]`, `[ID]` 줄 포함)
- [ ] `write_jobs(jobs)` — `jobs_all.txt`에 append
- [ ] `load_active_ids()` — `jobs_all.txt` 파싱, `[ID]` 줄 추출
- [ ] `load_dismissed_ids()` — `dismissed_ids.txt` 읽기
- [ ] 중복 건너뜀 로직 — `skip_ids = active | dismissed`
- [ ] `print_summary()` — 조회/저장 건수 콘솔 출력

### 완료 기준

```powershell
python fetch_jobs.py
# output/jobs_all.txt 에 사람인·원티드 공고 블록이 생성됨
# [출처] 줄로 소스 구분 가능
# 같은 날 두 번 실행해도 중복 추가 없음 (ID prefix로 소스별 구분)
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
  ├─ [초기화] output/ 확인
  │
  ├─ [X 마커] jobs_all.txt 에서 [X] 블록 탐색
  │             → 해당 ID를 dismissed_ids.txt 에 추가
  │             → [X] 블록 제거 후 파일 재작성
  │
  ├─ [중복 기준] active_ids + dismissed_ids 합산
  │
  ├─ [수집] 사람인 스크래핑 + 원티드 API 페이지네이션 전체 조회
  │
  ├─ [필터] config.ini 조건 적용 (키워드·지역·경력유형·경력연차)
  │
  ├─ [저장] skip_ids 에 없는 공고만 jobs_all.txt 에 append
  │
  └─ [요약] 조회 N건 | X 처리 M건 | 필터 통과 K건 | 신규 저장 J건
```

---

## Phase 5 — 안정성/신뢰성 (v3, 예정)

**목표**: Task Scheduler 무인 실행 중 조용히 실패해도 놓치지 않도록 실행 기록·이상 감지 추가

### 작업 목록 (예정)

- [ ] `RUN_LOG_PATH = "output/run_log.txt"` 상수 추가
- [ ] `print_summary()` 확장 — 콘솔 출력과 동시에 `run_log.txt`에 한 줄 append
- [ ] 소스 전체 실패 감지 — 사람인·원티드 중 하나라도 0건(요청 자체 실패)이면 `[경고]` 태그로 로그 강조
- [ ] 사람인 페이지 상한(현재 10페이지/400건) 도달 감지 — 마지막 페이지까지 40건 꽉 채운 채 끝나면 "더 많은 공고가 있을 수 있음" 경고 로그
- [ ] 페이지 상한 자체를 올릴지는 실행 시간 제약(PRD 비기능요구사항: 60초 이내)과 트레이드오프이므로 착수 시 재논의

### 완료 기준 (예정)

```
python fetch_jobs.py
# output/run_log.txt 에 실행 시각 + 조회/필터통과/신규저장 건수가 누적 기록됨
# 사람인 또는 원티드가 실패하면 로그에 [경고] 표시
```

---

## Phase 6 — 필터/매칭 고도화 (v3, 예정)

**목표**: 실 데이터 검증(2026-07-10)에서 확인된 필터 정밀도 문제를 추가로 개선

### 작업 목록 (예정)

- [ ] `filter_exp_range()` — overlap(겹치면 통과) → containment(공고 요구 범위가 내 범위 안에 완전히 포함되어야 통과) 방식 재검토.
      v2 마무리 시점에 "일단 이 상태로 두자"고 보류한 안건 — 착수 전 실제 원하는 동작(지원 가능한 시니어 공고까지 넓게 볼지, 내 연차대만 좁게 볼지)을 사용자에게 재확인
- [ ] `career_type` 다중 선택 지원 — `config.ini`에서 쉼표로 여러 값(예: `신입, 경력무관`) 지정 가능하도록 `load_config()`/`filter_career_type()` 확장. 기존 `_CAREER_EQUIVALENTS` 동등어 테이블과의 결합 방식 설계 필요
- [ ] 회사 블랙리스트 — `config.ini`에 `exclude_companies` 옵션 추가, `filter_jobs()`에 필터 함수 추가
- [ ] 마감임박 표시 — `format_block()`의 `[마감]` 줄에 D-day 표시(예: `2026-07-15 (D-3)`) 추가

### 완료 기준 (예정)

- 필터 변경 시 이번 v2 검증 때 썼던 방식대로 `fetch_saramin_all()`/`fetch_wanted_all()`로 실 데이터를 가져와 필터 전후 결과를 수동 대조해 정밀도/재현율 재확인
- `python -m pytest tests/ -v` 회귀 테스트 통과

---

## Phase 7 — 공고 관리: 지원 상태 추적 (v3, 예정)

**목표**: 기존 `[X]`(제거) 마커는 유지하고, 지원 상태(지원함/면접/합격/탈락)를 기록할 수 있게 확장

### 설계가 필요한 미결 사항 (착수 전 확정 필요)

- 마커 문법 — 기존 `[ ]` 자리에 상태 텍스트를 직접 적게 할지(`[지원함]`), `[X]`와 별개로 새 줄(`[상태]`)을 추가할지. 후자가 X 마커 로직과 안 겹쳐서 더 안전
- "탈락" 상태 처리 — `[X]`처럼 파일에서 제거하고 별도 기록(`archived_ids.txt`?)으로 옮길지, 파일에 남겨두고 상태만 표시할지
- "지원함/면접/합격"은 `jobs_all.txt`에 계속 남아 있어야 확인 가능 — `process_x_markers()`처럼 매 실행마다 스캔하되 제거는 하지 않고 상태만 읽어 콘솔 요약에 반영(예: "지원함 3건, 면접 1건")하는 정도가 적절해 보임
- 상태 변경 이력(언제 바뀌었는지)까지 추적할지는 범위 밖 — 단순 텍스트 파일 기반 "스크립트 수준 프로젝트" 원칙과 충돌

### 작업 목록 (착수 시 위 미결 사항 확정 후 구체화)

- [ ] 상태 마커 파싱 함수 추가 (`parse_blocks()` 재사용)
- [ ] `format_block()` 출력에 상태 마커 반영
- [ ] `docs/SPEC.md` §4-5(X 마커 처리 명세)를 상태 마커까지 포괄하도록 확장

---

## 파일 생성 순서 요약

| Phase | 생성 / 수정 파일 |
|---|---|
| 1 | `.gitignore`, `.env.example`, `requirements.txt`, `config.py`, `fetch_jobs.py` (뼈대) |
| 2 | `fetch_jobs.py` (API 조회·저장·중복 제거) |
| 3 | `fetch_jobs.py` (필터 함수 추가) |
| 4 | `fetch_jobs.py` (X 마커 처리 추가) |
| 5 (예정) | `fetch_jobs.py` (실행 로그·이상 감지 추가) |
| 6 (예정) | `fetch_jobs.py`, `config.ini`, `docs/SPEC.md` (필터 로직 확장) |
| 7 (예정) | `fetch_jobs.py`, `docs/SPEC.md` (상태 마커 추가) |

> Phase 1은 원래 `config.py`로 시작했으나, v2에서 `config.ini`(INI, `configparser` 기반)로 전환됨 — 자세한 내용은 `docs/SPEC.md` 변경 이력 참고.

---

## 범위 밖 (v3에도 포함 안 함)

- 로컬 알림(Windows 토스트 포함 모든 형태) — `docs/PRD.md` §4 비목표와 겹쳐서 보류
- 타 채용사이트(잡코리아 등) 연동
- 복수 검색 프로필(여러 config를 동시에 실행)

---

## 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-06-30 | 최초 작성 |
| 2026-07-09 | Phase 2 전환 — 사람인 공식 API → 사람인 스크래핑 + 원티드 비공식 API; 전체 실행 흐름 업데이트 |
| 2026-07-10 | v3 로드맵 추가 — Phase 5(안정성/신뢰성) · Phase 6(필터/매칭 고도화) · Phase 7(지원 상태 추적) 계획 수립(구현 미착수); "미구현 (Phase 2 이후 검토)" 항목을 Phase 5~7로 흡수·대체 |
