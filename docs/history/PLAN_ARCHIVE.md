> **이 파일은 과거 기록 보관용 전문(全文) 아카이브입니다.** 현재 유효한 계획(전략 요약·미착수
> Phase 5~7)은 `docs/PLAN.md`를 참고하세요. 여기 있는 Phase 1~4·8~15는 전부 완료된 작업의
> 상세 구현 로그이며, 최신 상태 파악에는 필요하지 않습니다.

---

# PLAN — 채용 공고 수집·관련성 랭킹·자소서 초안 작성 도구

_작성일: 2026-06-30 | 최종 수정: 2026-08-14 (v3 재설계 반영) | 기반 문서: PRD.md, SPEC.md_

---

## 구현 전략

전체를 여러 Phase로 나눈다. 각 Phase는 독립적으로 실행·검증 가능한 단위다.
Phase가 끝날 때마다 테스트를 실행하고 사용자 확인 후 다음 Phase로 진행한다.

Phase 1~4는 v1(최초 구현), Phase 8~13은 v3 재설계(2026-08-14, "찾는 과정 발전 + 자소서 초안
작성"으로 범위 확장)로 전부 완료됐다. v2(config.ini 전환, 실데이터 검증 기반 필터 수정)는
별도 Phase 없이 Phase 1~4 결과물에 대한 개선 작업으로 진행되어 `docs/SPEC.md` 변경 이력에
기록되어 있다.

**Phase 5~7(아래)은 2026-07-10에 세운 v3 로드맵 초안으로, 구현에 착수하지 않은 채 남아 있다.**
이후 2026-08-14 세션에서 범위가 훨씬 크게 확장되며 Phase 8~13으로 대체 착수했다. Phase 5~7의
개별 아이디어(실행 로그, 필터 고도화, 지원 상태 추적)는 Phase 8~13이 완료된 지금도 여전히
유효한 개선 후보이지만, 우선순위가 밀려 구현되지 않았다 — 작업 재개 시 이 Phase들을 그대로
이어가거나, 지금 구조(`jobfind/` 패키지)에 맞게 다시 계획해야 한다.

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

## Phase 8 — 패키지 재구조화 ✅ (2026-08-14 완료)

**목표**: `fetch_jobs.py` 단일 스크립트를 `jobfind/` 패키지로 순수 리팩터링 (동작 변경 없음)

### 구현 내용

- `jobfind/{config,dedup,filters,storage}.py`, `jobfind/collectors/{saramin,wanted}.py`로
  기존 함수를 로직 변경 없이 이관
- `jobfind.py`(얇은 진입점) + `jobfind/cli.py`에 `collect` 서브커맨드 구현 — 기존 `main()`과
  동일 동작
- 기존 51개 테스트를 새 모듈 경로에 맞게 이관, 전부 통과
- Windows 작업 스케줄러 무인 실행 원칙을 폐기하고 전부 명령 기반으로 전환 (배경은
  `docs/PRD.md` §1 참고)

### 검증

- `python jobfind.py collect` 실행 결과가 기존 `python fetch_jobs.py`와 동일함을 실데이터로 확인
- 재실행 시 신규 저장 0건 — 중복 방지 로직 정상 동작

---

## Phase 9 — 관련성 평가 ✅ (2026-08-14 완료, 세션 중 재설계됨)

**목표**: `config.ini keywords` 문자열 매칭을 넘어 의미 기반 관련성 평가 추가 (비용 없음)

### 1차 구현 → 재설계

처음에는 `role_description`(자연어 한 문장) + `threshold`(코사인 유사도 임계값) 이진 필터로
구현했으나, 실데이터 검증에서 비슷한 공고끼리도 판정이 갈리고 탈락하면 영구 제외되는 문제가
드러났다. 사용자 요청으로 **직무(`roles`)와 도메인(`domains`)을 분리 입력받아 각각 유사도를
구하고 합산 점수로 정렬해 상위 `top_n`건만 남기는 랭킹 방식**으로 재설계했다 — 순위 밖 공고는
영구 제외되지 않고 다음 수집에서 다시 상위권에 들 수 있다. 상세 명세는 `docs/SPEC.md` §11 참고.

### 검증

- mock 모델로 결합 점수/랭킹/top_n 자르기 로직 단위 테스트
- 실데이터(`roles=기획,PM`, `domains=커머스,화장품`)로 검증: 도메인·직무 둘 다 매칭되는
  공고가 상위권, 하나만 매칭되는 공고가 중위권, 둘 다 약한 공고가 최하위로 정렬됨을 확인

---

## Phase 10 — 수동 추가 + 자소서 선택 마커 + 보충 자료 입력 ✅ (2026-08-14 완료)

### 구현 내용

- `jobfind.py add <url>` — 사람인은 상세 페이지 `og:description` 메타태그(회사/제목/경력/
  지역/마감일)를 파싱, 원티드는 상세 API(`/api/v4/jobs/<id>`)를 호출해 기존
  `normalize_wanted()`를 그대로 재사용. 이미 목록에 있는 공고는 자동으로 건너뜀
- `jobfind/storage.py`에 `is_selected()`(`[자소서]` 마커) 추가
- `jobfind.py select` — `[자소서]` 선택된 공고마다 `output/cover_letters/<ID>/materials/`
  폴더 생성. 4개 초과 선택 시 경고 출력 (강제 차단은 `write` 단계에서)
- 보충 자료(이미지·`notes.md`)는 사용자가 `materials/`에 직접 넣어두는 방식 — 자동 수집
  기능은 만들지 않음 (파일명이 임의여도 상관없이 폴더 안 전부를 계획 단계에서 읽음)

### 검증

- 실제 사람인/원티드 URL로 추가 → 재추가 시 중복 스킵 확인, 잘못된 URL은 명확한 에러 메시지
- `[자소서]` 마커 → `select` → `materials/` 폴더 생성까지 실제로 실행해 확인

---

## Phase 11 — Provider 추상화 계층 ✅ (2026-08-14 완료)

### 구현 내용

- `jobfind/providers/{base,claude_cli,codex_cli,api}.py` —
  `Provider.run(system_prompt, user_prompt, images=None) -> str` 인터페이스로 4개 백엔드 통일
- `config.ini [providers]`에서 계획/계획평가/작성/초안평가 역할별로 다른 백엔드 조합 가능

### 검증 (실제 `claude` CLI로 mock 없이 확인)

- 텍스트 전용 호출: JSON 응답의 `result` 필드에서 정상적으로 텍스트 추출됨
- 이미지 포함 호출: `cwd`를 materials 폴더로 잡고 `--allowedTools Read`만 열어주니 실제
  이미지를 읽고 반영한 답변을 줌 (격리 설계 확인)
- `codex` CLI는 이 환경에 설치돼 있지 않아 미검증 — 공개된 `codex exec` 규약 기준으로만
  작성 (미결 사항, `docs/PRD.md` OQ4)
- **비용 관련 발견**: `claude_cli`는 매 호출마다 Claude Code 자체 시스템 프롬프트/툴 정의
  오버헤드로 약 9천 토큰이 캐시 생성으로 잡힌다 (`--bare`는 OAuth 로그인과 호환 안 돼 못 씀).
  "API 키 없이 공짜"라는 가정과 달리 구독 요금제에 따라 실질적 과금/한도 소모가 될 수 있음

---

## Phase 12 — 자소서 오케스트레이션 파이프라인 ✅ (2026-08-14 완료, 세션 중 보강됨)

### 구현 내용

- `profile.md`(사용자 이력, `.gitignore` 대상) + `profile.md.example` 템플릿
- `jobfind/pipeline/prompts.py` — 계획/계획평가/작성/초안평가 4개 역할 프롬프트
- `jobfind/pipeline/orchestrator.py` — `run_for_job()`: 계획 → 계획평가 →
  (NEEDS_REVISION이면 재작성) → 작성 → 초안평가, 결과를
  `output/cover_letters/<ID>/{plan,plan_review,draft,draft_review}.md`에 저장
- `jobfind.py write` 커맨드로 전체 파이프라인 실행

### 실데이터 검증 1회차 — 품질 이슈 발견

실제 공고 1건에 `claude_cli`로 전체 파이프라인을 실행해보니, 격리된 평가 agent가 실제로
날카로운 피드백(진부한 표현·업계 용어 부재·정량 데이터 부족 지적)을 냈고 `NEEDS_REVISION`
재작성 루프도 정상 동작했다. 다만 계획평가·초안평가 양쪽 모두 "planner/writer가 목록 페이지
요약 정보만 보고 작성했다"는 같은 근본 문제를 지적 — writer가 실제로 `WebFetch`를 시도했으나
`--allowedTools ""`로 막혀 있어 실패, 대신 지어내지 않고 정직하게 한계를 밝히는 것으로 대응함.

### 보강 — 공고 상세 설명 fetch 추가

처음엔 provider의 `WebFetch` 툴을 열어주는 방식을 검토했으나, provider마다 다르게 동작해야
하는 문제가 있어 대신 **서버 측(Python)에서 한 번 가져와 `job_text`에 얹는 방식**으로
변경했다 — provider 종류와 무관하게 동일하게 동작한다 (`fetch_posting_text()`).

- 원티드: 상세 API의 `detail.intro/main_tasks/requirements/preferred_points/benefits`를
  그대로 활용 (`fetch_wanted_description()`) — 실제로 잘 동작함
- 사람인: 정적 페이지 요청 + `BeautifulSoup.get_text()`를 먼저 시도했으나, 본문이
  자바스크립트로 렌더링돼 헤더/내비게이션 텍스트만 잡힌다는 걸 실제로 확인 — 노이즈만
  추가하는 꼴이라 **빈 문자열 반환으로 되돌림** (알려진 한계, `docs/PRD.md` OQ5)

### 실데이터 검증 2회차 — 개선 확인

같은 방식으로 원티드 공고 1건을 재검증: 계획평가·초안 모두 실제 회사명("주밍코리아")·업무
내용("특허/IP 담당")·자격요건을 구체적으로 반영한 결과로 확인됨. 사람인 공고는 기존과
동일(더 나빠지지 않음).

### 완료 기준

- mock provider로 파이프라인 단위 테스트(134개) + 실제 `claude_cli`로 공고 2건(사람인 1 +
  원티드 1) end-to-end 실행 검증 완료
- 검증에 사용한 `jobs_all.txt` 마커·`profile.md`·`output/cover_letters/`는 매번 원상복구함

---

## Phase 13 — 문서 정리 ✅ (2026-08-14 완료)

`CLAUDE.md`, `README.md`, `docs/PRD.md`, `docs/SPEC.md`, `docs/PLAN.md`(이 문서)를 v3 재설계
결과에 맞게 갱신. 상세 변경 내용은 각 문서의 변경 이력/최종 수정일 참고.

---

## Phase 14 — 실사용 피드백 반영 ✅ (2026-08-14 완료)

**배경**: Phase 8~13 완료 후 실제로 사용자의 진짜 이력서·자소서(PDF 2건)를 `profile.md`에
반영하고, 실제 4개 공고를 골라 전체 파이프라인(`collect`→`evaluate`→`select`→`write`)을
끝까지 돌려봤다. 그 결과를 바탕으로 사용자가 제기한 3가지 개선 요청을 처리했다.

### 1. `config.ini` → `.env` 통합

"`config.ini`도 결국 사람이 직접 입력해야 하는 파일이니, `.env`로 합치는 게 맞다"는 피드백을
반영. `jobfind/config.py`의 `load_config()`를 `configparser` 기반에서 `os.environ`(+
`python-dotenv`) 기반으로 재작성하고, `config.ini`는 삭제했다. `.env.example`에 필터·관련성·
provider·API 키 전체 항목을 문서화해 템플릿으로 남겼다.

- `CLAUDE.md` Security Rules를 "API 키 값은 Claude가 채우지 않는다"로 범위를 좁혀 명시 —
  일반 설정 값(필터/관련성/provider)은 사용자가 명시적으로 요청한 마이그레이션 작업의
  일부로 Claude가 수정할 수 있음을 구분했다.
- 테스트: `tests/test_config.py`를 tmp_path INI 작성 방식에서 `monkeypatch.setenv`/`delenv`
  방식으로 전면 재작성.

### 2. 관련성 랭킹 품질 개선 시도

실사용 검증에서 `roles=기획, PM` / `domains=IT, 웹, 앱`로 `evaluate`를 돌렸더니, "재무기획
팀원 채용"(순수 사무/회계 직무)이 실제 IT PM 공고보다 상위에 랭크되는 문제가 관찰됐다.

- **원인 진단**: `rank_jobs()`가 `role_score + domain_score` 단순 합산이라, `roles`
  텍스트와 문자열만 우연히 겹치는 공고("재무기획"의 "기획")가 domain_score 없이도
  role_score 하나만으로 상위에 오를 수 있었다.
- **수정**: roles/domains 둘 다 설정된 경우 `role_score * domain_score`(곱셈)로 결합하도록
  변경 — 한쪽이 0에 가까우면 총점도 낮아지게 함. 하나만 설정된 경우는 기존처럼 합산(사실상
  단일 축)으로 유지.
- **실측으로 확인한 한계**: 실제 텍스트로 두 방식을 직접 계산해봤더니, 이번 사례에서는
  `RELEVANCE_DOMAINS="IT, 웹, 앱"`에 대한 도메인 점수 자체가 사무행정 공고(0.499)와 진짜
  IT PM 공고(0.425~0.535) 사이에 뚜렷한 차이가 없어, 곱셈으로 바꿔도 순위가 크게 달라지지
  않았다. 도메인 질의를 문장형으로 바꿔봐도("IT 서비스, 웹 서비스, 모바일 앱 개발 회사")
  개선되지 않음을 확인 — 원인은 결합식이 아니라 `jhgan/ko-sroberta-multitask`가 짧은 공고
  제목에서 이 정도 추상도의 도메인을 구분하는 판별력 자체가 약한 것으로 보인다. 곱셈 결합은
  그 자체로 정당한 개선(도메인이 뚜렷이 갈리는 경우엔 실제로 효과가 있음, 단위 테스트로
  검증)이지만 이 근본 원인까지 해결하지는 못한다 — 사용자에게 이 실측 결과를 투명하게
  공유하고, 다른 임베딩 모델 시도나 `job_text`에 회사명 포함 등은 후속 과제로 남겼다.
- Wanted 목록 API의 `category_tags`가 태그 이름이 아닌 숫자 ID만 제공해 저비용으로 활용할
  방법이 없음을 확인, 이번 범위에서는 보류.

### 3. 자소서가 실제 공고 문항에 답하도록 개선

- **조사**: 사람인 상세 페이지의 데스크톱/모바일 버전을 모두 정적으로 가져와 확인한 결과,
  두 버전 다 담당업무·자격요건·자소서 문항 등 실제 본문은 자바스크립트 렌더링으로만
  채워지고, 정적 HTML에는 헤더/내비게이션과 일부 요약 필드(급여·직급·근무일수 등)만 있음을
  재확인했다. `application/ld+json` 구조화 데이터나 호출 가능한 내부 API도 발견하지 못함 —
  헤드리스 브라우저(Playwright 등) 없이는 이 한계를 근본적으로 해결할 수 없다고 결론.
- **수정**: `writer_prompt`의 시스템 프롬프트에 "공고 정보가 부족해도 초안 작성을 거부하지
  마라 — 표준 구성으로라도 반드시 실제 초안을 작성하고, 가정한 부분은 본문과 분리된 안내
  문구로만 남겨라"는 지시를 추가. 실사용 검증에서 같은 조건(사람인, 상세 설명 없음)의 공고
  2건 중 1건은 초안을 작성했지만 1건은 "정보가 부족해 못 쓰겠다"며 완전히 거부하는 등 동작이
  일관되지 않았던 문제를 해결.
- **보류(사용자 확인 필요)**: 사람인 JD 본문 자체를 가져오려면 Playwright 등 헤드리스 브라우저
  도입이 필요하다 — 새 의존성(브라우저 바이너리 포함 수백 MB)과 복잡도가 상당하고, 그렇게
  해도 실제 자소서 문항이 외부 회사 자체 사이트로 연결되는 경우까지는 해결 못 할 수 있어
  사용자에게 별도로 확인 후 진행 여부를 결정하기로 함.

### 검증

- 137개 → 141개로 늘어난 테스트 전부 통과 (env 로딩, 곱셈 결합, `[자소서]` 보호 회귀
  테스트, writer 프롬프트 지시 포함).
- 실데이터로 `.env` 마이그레이션 후 `collect`/`evaluate` 정상 동작 확인, 실제 공고 텍스트로
  결합식 전후 점수를 직접 계산해 위 한계를 실측으로 확인.

---

## Phase 15 — 모델/리서치 고도화 ✅ (2026-08-14 완료)

**배경**: Phase 14 실사용 검증 이후 사용자가 다시 세 가지 개선을 요청했다: (1) 공고 수집
자체가 부정확하면 이후 단계가 다 무의미하니 관련성 평가 모델을 재검토/교체, (2) 자소서
작성이 실제 자소서 문항을 반영할 수 있는 방안 검토(자소설닷컴처럼 문항을 직접 제공하는
경로로 바꾸는 것도 검토), (3) 자소서 작성에서 가장 힘든 "기업·직무·문항에 맞춘 자료 조사"
자체를 자동화할 방안(뉴스·기업 홈페이지·DART 사업보고서 등) 검토. `AskUserQuestion`으로
방향을 좁힌 결과: 자소설닷컴 연동은 보류(직접 복사·붙여넣기 유지), DART 연동과 planner
웹 검색 허용은 둘 다 진행하기로 확정됐다.

### 1. 관련성 임베딩 모델 교체

Phase 14에서 이미 "곱셈 결합으로 바꿔도 모델 자체의 도메인 판별력이 약해 한계가 남는다"고
실측으로 확인해둔 문제를 이번에 정면으로 다뤘다.

- 실제 수집된 공고 제목 텍스트로 여러 모델의 domain_score 분포를 직접 계산해 비교했다
  (모델 카드 설명이 아니라 실측 기준).
  - `jhgan/ko-sroberta-multitask`(기존): 도메인 점수가 0.4~0.5대로 좁게 몰림 — 사무행정
    공고와 실제 IT PM 공고를 구분하지 못함.
  - `intfloat/multilingual-e5-base`: 처음엔 `"query: "`/`"passage: "` prefix 없이 테스트해
    불공정하게 낮은 점수가 나왔음을 인지하고, prefix를 올바르게 적용해 재측정 — 그래도
    도메인 점수 spread가 0.042로 더 나빴다. 일반적으로 평가가 좋은 모델이어도 이 짧은
    한국어 텍스트 도메인 분류 용도에는 안 맞는다는 것을 실측으로 확인 후 기각.
  - `snunlp/KR-SBERT-V40K-klueNLI-augSTS`(신규 채택): 실측 기준 기존 대비 약 3배 개선된
    도메인 점수 spread.
- `jobfind/config.py`의 `RELEVANCE_MODEL` 기본값, `.env`/`.env.example`을 교체.
- **정직하게 남긴 한계**: 이 교체는 "기존보다 개선"이지 "완벽한 도메인 판별"이 아니다.
  짧은 공고 제목만으로는 어떤 사전학습 임베딩 모델도 완벽을 보장하지 않는다는 점은
  `docs/SPEC.md` §11-3에 이미 있는 실측 한계 서술과 여전히 함께 유효하다.

### 2. 자소설닷컴 연동 조사 및 보류

- `C:\Users\SSAFY\Pictures\Screenshots`의 `sosal` 스크린샷을 참고해 자소설닷컴이 자소서
  문항을 직접 노출하는 방식을 조사했다: 정적 fetch, `__NEXT_DATA__` JSON 파싱, Next.js
  `_next/data` SSR 엔드포인트 추정, REST API 패턴 추정을 모두 시도했으나 완전한 답을 얻지
  못했다. 실제 API 구조를 확인하려면 라이브 브라우저 네트워크 검사가 필요한데, 이 환경에서는
  `mcp__claude-in-chrome` 확장이 연결되지 않아("Browser extension is not connected.")
  완료하지 못했다.
- 기술적 한계 외에 정책적 고려도 있다 — 자소설닷컴은 채용 공고 자체가 아니라 그 사이트가
  직접 정리·큐레이션한 부가 콘텐츠(자소서 문항)를 제공한다. 공개 채용 공고를 모으는 것과
  제3자가 가공한 콘텐츠를 스크래핑하는 것은 성격이 다르다고 판단해, 기술 문제와 별개로도
  신중히 접근할 사안으로 사용자에게 그대로 제시했다.
- `AskUserQuestion`으로 사용자에게 확인한 결과: "보류 — 지금처럼 직접 복사·붙여넣기" 선택.
  자소서 문항은 계속 `output/cover_letters/<공고ID>/materials/notes.md`에 사용자가 직접
  옮겨 적어 계획 단계에서 참고하는 기존 방식을 유지한다.

### 3. 기업 리서치 자동화 — DART 연동 + planner 웹 검색

**DART(전자공시시스템) 오픈API 연동** (`jobfind/dart.py`, 신설)

- DART OpenAPI를 WebFetch/WebSearch로 조사해 실제 엔드포인트 형태를 확인: `corpCode.xml`
  (전체 상장기업 목록, ZIP+XML — 회사명으로 검색하려면 먼저 이 목록에서 corp_code를
  찾아야 함)과 `company.json`(corp_code로 조회하는 기업 개황 — 대표자·설립일·시장구분·
  주소·홈페이지 등).
- `fetch_company_profile(company_name)`: `.env`의 `DART_API_KEY`가 없거나 회사명이 비어
  있으면 즉시 빈 문자열 반환. 있으면 `corpCode.xml`을 내려받아(7일 캐시,
  `output/.dart_corp_codes.json`) "(주)"/"㈜"/"주식회사" 등 법인 표기를 정규화한 뒤 정확히
  일치하는 회사명을 찾고, 찾으면 `company.json`으로 개황을 조회해 텍스트로 포맷한다.
- 못 찾거나 조회 실패(상태 코드 `!= "000"`, 네트워크 오류 등)는 전부 빈 문자열 반환으로
  처리한다 — 비상장 스타트업처럼 DART에 없는 회사가 훨씬 많으므로, "실패"가 아니라
  "정상적으로 해당 없음"으로 취급해 파이프라인을 막지 않는다.
- `orchestrator.run_for_job()`에서 `fetch_posting_text()` 보강 다음에 `job_text`에
  이어붙인다 (`docs/SPEC.md` §13-1, §13-5).
- **미검증 사항(정직하게 기록)**: 이 프로젝트를 만든 환경에 실제 `DART_API_KEY`가 없어
  `tests/test_dart.py`의 12개 테스트는 전부 `requests.get`/`_load_corp_codes`를 모킹한
  단위 테스트다. 실제 키로 검증되지 않았다는 점을 README/SPEC/PRD에 명시했다.

**planner의 웹 검색·웹 조회 허용**

- `Provider.run()` 프로토콜에 `extra_tools: list[str] | None = None` 파라미터를 추가.
  `claude_cli`에서만 실제로 `--allowedTools`에 반영되고(이미지로 인한 `Read`와 결합될 수
  있음, 순서는 `extra_tools` 먼저 + `Read` 나중), `codex_cli`/`api:*`는 인자만 받고 무시한다
  (실제 대응하는 서버사이드 도구 제어 수단이 없음).
- `orchestrator.py`에 `PLANNER_RESEARCH_TOOLS = ["WebSearch", "WebFetch"]`를 정의하고
  planner 호출(초안 계획 + 재작성 계획)에만 전달, plan_evaluator/writer/draft_evaluator는
  그대로 `None`.
- `prompts.planner_prompt()`/`planner_revision_prompt()`의 시스템 프롬프트에 "웹 검색·웹
  조회 도구를 쓸 수 있다면 회사 최근 뉴스·홈페이지·업계 동향을 실제로 검색해 계획에
  구체적으로 반영하라 — 도구가 없거나 검색이 실패해도 계획 수립 자체를 멈추지 말라"는
  지시를 추가.
- **실제 검증**: mock이 아니라 실제 `claude -p --allowedTools "WebSearch"` 호출로 검증
  완료 — 응답 JSON의 `webSearchRequests: 1` 필드로 실제 검색이 일어났음을 확인했고, 검색을
  포함한 호출의 비용이 미포함 대비 약 1.5~2배(실측: $0.133 vs 평소 $0.06~0.09대)로 늘어남을
  측정해 README §8(비용)에 반영했다.

### 검증

- 161개 테스트 전부 통과 (관련성 모델 기본값 변경, `jobfind/dart.py` 12개 신규 테스트,
  provider `extra_tools` 관련 신규 테스트, orchestrator의 기업 개황 보강/웹 검색 도구 부여
  회귀 테스트 포함).
- 관련성 모델 교체는 실제 `evaluate` 실행으로 검증(`jobs_all.txt` 백업 후 재실행, 결과
  대조 후 원본 복원). planner 웹 검색 허용은 실제 `claude -p` 호출로 검증. DART 연동은 실제
  API 키가 없어 모킹으로만 검증 — 위에 명시한 대로 미검증 상태를 그대로 남긴다.

---

## 파일 생성 순서 요약

| Phase | 생성 / 수정 파일 |
|---|---|
| 1 | `.gitignore`, `.env.example`, `requirements.txt`, `config.py`, `fetch_jobs.py` (뼈대) |
| 2 | `fetch_jobs.py` (API 조회·저장·중복 제거) |
| 3 | `fetch_jobs.py` (필터 함수 추가) |
| 4 | `fetch_jobs.py` (X 마커 처리 추가) |
| 5 (미착수) | `fetch_jobs.py` (실행 로그·이상 감지 추가) — Phase 8~13에 우선순위 밀림 |
| 6 (미착수) | `fetch_jobs.py`, `config.ini`, `docs/SPEC.md` (필터 로직 확장) — Phase 8~13에 우선순위 밀림 |
| 7 (미착수) | `fetch_jobs.py`, `docs/SPEC.md` (상태 마커 추가) — Phase 8~13에 우선순위 밀림 |
| 8 | `jobfind/` 패키지 전체(신설), `fetch_jobs.py`/`tests/test_fetch_jobs.py` 삭제 |
| 9 | `jobfind/relevance.py`, `config.ini` |
| 10 | `jobfind/{collectors/*,selection.py,storage.py,cli.py}` |
| 11 | `jobfind/providers/`, `config.ini`, `.env.example` |
| 12 | `jobfind/pipeline/`, `profile.md.example`, `.gitignore` |
| 13 | `CLAUDE.md`, `README.md`, `docs/PRD.md`, `docs/SPEC.md`, `docs/PLAN.md`(이 문서) |
| 14 | `jobfind/config.py`(env 기반 재작성), `.env`/`.env.example`, `config.ini`(삭제), `jobfind/relevance.py`(곱셈 결합 + [자소서] 보호), `jobfind/pipeline/prompts.py`(writer 지시 보강), 문서 전체 |
| 15 | `jobfind/config.py`(RELEVANCE_MODEL 기본값 교체), `jobfind/dart.py`(신설), `jobfind/providers/{base,claude_cli,codex_cli,api}.py`(extra_tools 추가), `jobfind/pipeline/orchestrator.py`(company_profile 보강 + PLANNER_RESEARCH_TOOLS), `jobfind/pipeline/prompts.py`(planner 웹 검색 지시), `.env`/`.env.example`(RELEVANCE_MODEL·DART_API_KEY), `tests/test_dart.py`(신설), 문서 전체 |

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
| 2026-07-10 | v3 로드맵 초안 추가 — Phase 5(안정성/신뢰성) · Phase 6(필터/매칭 고도화) · Phase 7(지원 상태 추적) 계획 수립(구현 미착수); "미구현 (Phase 2 이후 검토)" 항목을 Phase 5~7로 흡수·대체 |
| 2026-08-14 | v3 재설계 착수 — "찾는 과정 발전 + 자소서 초안 작성"으로 범위 확장, Phase 5~7 로드맵 초안 대신 Phase 8~13으로 신규 계획·전부 구현 완료(패키지 재구조화, 관련성 랭킹, 수동추가/자소서 선택, provider 추상화, 자소서 파이프라인, 문서 정리). 세부 내용은 위 Phase 8~13 섹션 참고 |
| 2026-08-14 | Phase 14 추가 — 실사용(진짜 이력서·실제 공고 4건 end-to-end 실행) 피드백 3건 반영: config.ini→.env 통합, 관련성 결합식 합→곱 수정(+ 임베딩 모델 도메인 판별력 한계 실측 확인), writer 초안 작성 거부 방지. 세부 내용은 위 Phase 14 섹션 참고 |
| 2026-08-14 | Phase 15 추가 — 모델/리서치 고도화 3건 반영: 관련성 임베딩 모델을 실측 비교로 교체(jhgan → snunlp, 도메인 판별력 약 3배 개선), 자소설닷컴 연동 조사 후 기술적+정책적 이유로 보류, DART 오픈API 연동 신설(상장기업 개황 자동 조회, 실키 미검증) + planner에 WebSearch/WebFetch 허용(실제 호출로 검증, 비용 약 1.5~2배). 세부 내용은 위 Phase 15 섹션 참고 |
