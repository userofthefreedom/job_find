# CLAUDE.md

## Project Overview

사람인 공개 검색 페이지 스크래핑과 원티드 비공식 API로 채용 공고를 가져와 사용자가 정의한
조건(직무·지역·경력 등)에 맞는 공고만 필터링하고, 로컬 임베딩 모델로 관련성 순위를 매기고,
선택한 공고에 대해 AI가 자소서 초안까지 작성해주는 CLI 도구.

- **완전 명령 기반**: v1~v2의 Windows 작업 스케줄러 무인 실행은 폐기했다(`docs/PLAN.md`
  Phase 8 변경 이력 참고). 수집부터 자소서 작성까지 전부 `python jobfind.py <command>`로
  사용자가 직접 트리거한다.
- **AI provider 다각화**: 자소서 파이프라인의 각 역할(계획/계획평가/작성/초안평가)은
  Claude CLI(`claude -p`) · Codex CLI(`codex exec`) · Anthropic/OpenAI API 중 `.env`에서
  선택한 백엔드로 동작한다. 어디서 실행하든(터미널/IDE 확장/대화 중 요청) 동일한 CLI
  진입점을 쓰므로 실행 위치는 자유롭다.
- **관련성 평가는 비용 없는 로컬 HuggingFace 임베딩 모델**로 처리한다 (LLM 호출 아님).
- 사람인·원티드 두 플랫폼에서 공고 수집, 결과를 단일 파일(`output/jobs_all.txt`)에 통합해
  누적 기록한다.

## Tech Stack

- **Language**: Python 3.11+
- **Job data source**:
  - 사람인 공개 검색 페이지 스크래핑 (`https://www.saramin.co.kr/zf_user/search/recruit`)
    - HTML 파싱: `beautifulsoup4`
  - 원티드 비공식 API (`https://www.wanted.co.kr/api/v4/jobs`, 상세는 `/api/v4/jobs/<id>`)
  - HTTP 통신: `requests`
- **관련성 평가**: `sentence-transformers` + 사전학습 한국어 문장 임베딩 모델
  (`snunlp/KR-SBERT-V40K-klueNLI-augSTS`, 최초 실행 시 자동 다운로드). 파인튜닝은 하지 않음 —
  자세한 배경은 `docs/PLAN.md` Phase 9·15 참고 (원래 `jhgan/ko-sroberta-multitask`였으나
  Phase 15에서 실측 비교 후 도메인 판별력이 더 나은 이 모델로 교체)
- **AI provider**: `jobfind/providers/`에 4개 백엔드
  - `claude_cli`: `claude -p` subprocess 헤드리스 호출 (이미 로그인된 세션 사용, API 키 불필요).
    자소서 계획(planner) 단계에는 `--allowedTools`로 `WebSearch`/`WebFetch`를 열어줘 회사
    뉴스·홈페이지를 직접 검색하게 한다 (Phase 15, 호출당 비용/시간 증가 트레이드오프 있음)
  - `codex_cli`: `codex exec` subprocess 헤드리스 호출 (실제 플래그 미검증 — `docs/PLAN.md`
    Phase 11 리스크 참고). extra_tools(WebSearch 등)는 인터페이스 호환을 위해 받되 무시함
  - `api:anthropic` / `api:openai`: `requests`로 Messages/Chat Completions API 직접 호출
    (`.env`의 `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` 사용, 호출당 과금). extra_tools는 대응하는
    서버사이드 툴 연동이 없어 무시함
- **DART(전자공시) 연동**: `jobfind/dart.py` — `DART_API_KEY`가 있으면 자소서 계획 단계에
  상장기업 개황(대표자·설립일·시장구분·홈페이지)을 자동 반영. 무료·즉시발급 공식 API지만
  비상장 회사는 커버 안 됨 (Phase 15)
- **Config / secrets**: `python-dotenv` — 필터·관련성·provider 설정과 API 키를 전부 `.env`
  하나에서 로드 (v3 초반엔 `config.ini` + `.env`로 나뉘어 있었으나, 결국 둘 다 사람이 직접
  입력하는 파일이라 실사용 피드백으로 `.env` 하나로 통합함)
- **Runtime**: Windows 로컬, 사용자가 터미널에서 직접 실행하는 CLI (`jobfind.py`)
- **Output**: UTF-8 txt 파일(`output/jobs_all.txt`) + 공고별 자소서 결과
  (`output/cover_letters/<공고ID>/`)

## Project Structure

```
/
├── jobfind.py                  # 얇은 진입점 — jobfind.cli.main() 호출
├── jobfind/
│   ├── cli.py                   # argparse 서브커맨드: collect / evaluate / add / select / write
│   ├── config.py                 # .env 로드 (필터/관련성/provider 설정 + API 키)
│   ├── collectors/
│   │   ├── saramin.py            # 사람인 목록 스크래핑 + 단건 상세 조회(og:description)
│   │   └── wanted.py             # 원티드 목록/상세 API 호출
│   ├── dedup.py                  # 플랫폼 간 중복 제거
│   ├── filters.py                # .env 기반 1차 필터 (키워드/지역/경력유형/연차)
│   ├── relevance.py              # HF 임베딩 기반 2차 필터 — 직무x도메인 랭킹, 상위 top_n만 유지
│   ├── verification.py           # 상세 요건 최종검수 — AI로 목록 요약 vs 실제 요건 대조
│   ├── dart.py                   # DART 기업개황 조회 (상장기업만, API 키 있을 때만)
│   ├── selection.py               # [자소서] 마커 스캔, materials/ 폴더 준비
│   ├── storage.py                # jobs_all.txt/dismissed_ids.txt 읽기·쓰기, 블록 파싱, 마커 처리
│   ├── providers/                # AI provider 추상화 (claude_cli/codex_cli/api)
│   └── pipeline/                 # 자소서 오케스트레이션 (prompts.py, orchestrator.py)
├── profile.md                    # 사용자 이력/자기소개 자유 텍스트 (.gitignore 대상)
├── profile.md.example            # profile.md 템플릿 (Git 포함)
├── requirements.txt
├── .env / .env.example           # 필터·관련성·provider 설정 + API 키 전부 여기 (.env는 Git 제외)
├── .gitignore
├── README.md
├── CLAUDE.md
├── output/                       # 실행 결과 저장 폴더 (전체 Git 제외)
│   ├── jobs_all.txt
│   ├── dismissed_ids.txt
│   ├── archived_ids.txt           # [상태] 탈락 처리된 공고 ID 영구 기록
│   ├── run_log.txt                # collect 실행 이력 누적 (소스 실패/페이지 상한 [경고])
│   └── cover_letters/<공고ID>/  # plan.md, plan_review.md, draft.md, draft_review.md, materials/
├── tests/
└── docs/                         # 기획·설계 문서 (루트는 항상 최신 상태 요약본)
    ├── PRD.md                     # 요구사항 (현재 목표/비목표/미결사항)
    ├── SPEC.md                    # 기술 스펙 (현재 동작 방식)
    ├── PLAN.md                    # 구현 전략 요약 + 미착수 Phase(5~7)
    ├── PROGRESS.md                # Phase별 완료 현황 요약
    ├── TEST_RESULT.md             # 최신 테스트 규모 요약
    └── history/                   # 과거 세션 기록 전문(全文) 아카이브 — 최신 상태 파악엔 불필요
        ├── PLAN_ARCHIVE.md         # Phase 1~15 상세 구현 로그
        ├── SPEC_ARCHIVE.md         # SPEC 변경 이력 + 실측 비교 전문
        ├── PROGRESS.md             # 세션별 상세 진행 기록
        └── TEST_RESULT.md          # Phase 1 최초 실행 로그
```

문서를 갱신할 때는 **루트 파일에는 "지금 어떤 상태인가"만 남기고, 시행착오·비교표·세션별
서술 같은 과거 기록은 `docs/history/`로 옮긴다** — 루트 문서가 길어질수록 에이전트가 오래된
맥락과 현재 상태를 혼동해 환각을 일으키기 쉬워지기 때문이다 (2026-08-15 문서 재구성 배경).

프로젝트 루트에는 실행에 직접 필요한 파일(진입점, 설정 파일, 의존성 목록, 표준 문서)만 둔다.
세션 진행 기록·테스트 결과처럼 실행에 필요 없는 문서는 `docs/`에 둔다.

## Commands

### 환경 구성 (최초 1회)

```bash
# 가상환경 생성 및 활성화 (venv 사용 — 전역 Python 환경 오염 방지)
python -m venv venv
source venv/Scripts/activate

# 의존성 설치 (sentence-transformers·torch 포함이라 최초 설치에 시간이 걸릴 수 있음)
pip install -r requirements.txt

# 설정 파일 생성 (필터·관련성·provider·API 키 전부 여기서 관리)
cp .env.example .env
```

### 실행

```bash
source venv/Scripts/activate

python jobfind.py collect     # 사람인+원티드 수집 → 1차 필터 → jobs_all.txt에 저장
python jobfind.py evaluate    # 직무·도메인 관련성 순으로 정렬해 상위 top_n건만 유지
python jobfind.py verify      # 목록 요약과 실제 상세 요건(사람인은 이미지, 원티드는 텍스트)을
                               # profile.md와 대조해 [검수] 결과를 남김 (AI 호출, 자동 삭제 안 함)
python jobfind.py add <url>   # 사람인/원티드 공고 URL을 수동으로 추가
python jobfind.py select      # jobs_all.txt에서 [자소서]로 표시한 공고에 materials/ 폴더 준비
python jobfind.py write       # [자소서] 선택된 공고(최대 4개)의 자소서 초안 작성
```

### 테스트

```bash
source venv/Scripts/activate
python -m pytest tests/ -v
```

## Code Style

이 프로젝트는 원래 "스크립트 수준 프로젝트"로 시작해 단일 파일(`fetch_jobs.py`)에 모든 로직을
두고 별도 모듈 분리를 금지했었다. v3 재설계(Phase 8, `docs/PLAN.md` 참고)에서 AI 오케스트레이션
파이프라인·provider 추상화 등 새 영역이 추가되며 단일 파일로는 관리가 불가능해져 이 원칙을
폐기하고 `jobfind/` 패키지로 전환했다. 다만 과도한 추상화를 피한다는 기본 태도는 유지한다.

- 기능 단위로 모듈 분리 (수집 / 필터 / 관련성평가 / 저장 / provider / 파이프라인)
- 클래스는 상태를 가져야 하는 경우(예: provider 구현체)에만 사용 — 나머지는 함수로 구성
- 타입 힌트 사용 (함수 시그니처 수준)
- 주석은 WHY가 명확하지 않을 때만 작성, 코드 설명성 주석 금지
- 파일 하나당 150줄 이하를 목표로 유지
- 포매터: `black`, 린터: `ruff` (설정은 기본값 사용)

## Security Rules

- API access-key는 반드시 `.env` 파일에만 저장하고, 코드에 직접 쓰지 않는다.
- `.env` 파일은 `.gitignore`에 포함해 절대 커밋하지 않는다.
- **API 키(`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`SARAMIN_ACCESS_KEY`) 값은 Claude가 채우지
  않는다.** 사용자가 직접 발급받아 입력한다. v3에서 `.env`가 필터·관련성·provider 설정까지
  통합해서 맡게 됐으므로(`config.ini` 폐기, 아래 참고), **키가 아닌 나머지 설정 값은** 사용자가
  명시적으로 요청한 마이그레이션/설정 작업의 일부로 Claude가 수정할 수 있다 — 이 구분(키 값
  vs 일반 설정 값)을 지킨다.
- `.env.example`에는 실제 키 값 없이 변수 이름과 형식만 기재한다.
- `profile.md`(사용자 이력서/자기소개)는 개인정보이므로 `.gitignore`에 포함해 커밋하지 않는다.
  실제 내용 없는 `profile.md.example` 템플릿만 커밋한다.

```
# .env.example (발췌 — 전체 항목은 실제 파일 참고)
FILTER_KEYWORDS=
RELEVANCE_ROLES=
PROVIDER_PLANNER=claude_cli
# 사람인 공식 API 승인 시: SARAMIN_ACCESS_KEY=your_access_key_here
# api:anthropic / api:openai 백엔드를 쓸 때만 필요:
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
```

## Workflow Rules

1. **구현 전 문서 확인**: `docs/PRD.md` → `docs/SPEC.md` → `docs/PLAN.md` 순서로 읽은 뒤 작업 시작
2. **단계 단위 구현**: `docs/PLAN.md`에 정의된 Phase를 한 번에 하나씩만 구현
3. **테스트 후 완료 처리**: 각 Phase 구현 후 반드시 테스트 실행, 통과 후 다음 단계 진행
4. **변경 기록**: 동작 방식·파라미터·파일 형식이 바뀌면 `docs/SPEC.md`를 해당 시점에 업데이트
5. **Phase 완료 보고**: Phase 하나가 끝나면 무엇을 구현했는지 사용자에게 요약 보고 후 다음 지시 대기
6. **필터 변경 시 실데이터 검증**: 필터링/관련성 랭킹 로직을 바꾸면 실제 사람인·원티드 데이터로
   변경 전후 결과를 수동 대조하고, 정밀도(오탐)·재현율(누락)을 확인한 뒤 완료 보고
7. **AI 파이프라인 변경 시 실제 provider로 최소 1회 검증**: prompts.py/orchestrator.py를 바꾸면
   mock provider 단위 테스트뿐 아니라 실제 provider(기본 `claude_cli`) 1회 end-to-end 실행으로
   결과물을 직접 확인한 뒤 완료 보고. 테스트에 사용한 실데이터(jobs_all.txt 마커, profile.md,
   output/cover_letters/)는 검증 후 원상복구한다.

## 다음 단계

v1(Phase 1~4, 사람인+원티드 수집)·v2(config.ini 전환 및 실데이터 검증 기반 필터 수정)·
v3 재설계(Phase 8~13: 패키지 재구조화, HF 임베딩 관련성 랭킹, 수동 추가/자소서 선택 마커,
AI provider 추상화, 자소서 오케스트레이션 파이프라인, 문서 정리) 모두 완료됐다.

기존 v3 로드맵 초안(Phase 5~7 — 실행 로그/이상 감지, 필터 고도화, 지원 상태 추적)은 구현에
착수하지 못한 채 우선순위가 밀렸다. 아이디어 자체는 여전히 유효한 개선 후보다 — 작업 재개 시
`docs/PLAN.md`의 "구현 전략" 인트로와 Phase 5~7 섹션을 먼저 확인한다.

Phase 14(실사용 피드백 반영, `docs/PLAN.md` 참고)에서 `config.ini` → `.env` 통합, 관련성 랭킹
결합식(합→곱) 수정, writer가 정보 부족해도 초안 작성을 거부하지 않도록 프롬프트 보강을
완료했다. Phase 15에서 이어서 (1) 임베딩 모델을 `jhgan/ko-sroberta-multitask` →
`snunlp/KR-SBERT-V40K-klueNLI-augSTS`로 교체(실측 비교로 도메인 판별력 개선 확인), (2) DART
기업개황 자동 조회 추가, (3) planner에 WebSearch/WebFetch 허용을 완료했다. 자소설닷컴(실제
자소서 문항 제공 사이트) 연동은 기술적으로(정적 스크래핑 불가, 이 환경에 브라우저 확장
미연결) + 정책적으로(제3자 큐레이션 콘텐츠 스크래핑 소지) 보류했다 — 사용자가 직접 보고
`materials/notes.md`에 복사해 넣는 기존 방식 유지. 재검토 시 `docs/PLAN.md` Phase 15를
먼저 확인할 것.

## Scraping & API Constraints

- **사람인 스크래핑**: 공개 검색 페이지 HTML 파싱 (`days=1` 파라미터로 오늘 공고 필터)
  - 페이지당 최대 40건, 페이지네이션으로 전체 수집
  - HTTP 오류 시 **1회** 재시도, 실패 시 해당 소스 건너뛰고 원티드 결과만 사용
  - 상세 페이지(`add`/자소서 파이프라인용)는 `og:description` 메타태그로 회사/제목/경력/
    지역/마감일만 얻을 수 있다. **본문(담당업무·자격요건 등)은 자바스크립트 렌더링이라
    정적 요청으로는 가져올 수 없음** — 자소서 파이프라인에서 이 한계로 인해 사람인 공고는
    상세 설명 보강 없이 목록 정보만으로 작성된다 (`docs/PLAN.md` Phase 12 검증 기록 참고)
- **원티드 비공식 API**: 인증 없이 JSON 응답 수신
  - 페이지당 20건, offset 기반 페이지네이션
  - HTTP 오류 시 **1회** 재시도, 실패 시 해당 소스 건너뛰고 사람인 결과만 사용
  - 상세 API(`/api/v4/jobs/<id>`)는 `detail.intro/main_tasks/requirements/preferred_points/
    benefits`를 구조화된 필드로 제공 — 자소서 파이프라인이 이걸 그대로 활용해 원티드 공고는
    실제 상세 요건을 반영한 결과가 나온다
