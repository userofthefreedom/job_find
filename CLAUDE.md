# CLAUDE.md

## Project Overview

사람인 공개 검색 페이지 스크래핑과 원티드 비공식 API를 사용해 매일 채용 공고를 가져오고,
사용자가 정의한 조건(직무·지역·경력 등)에 맞는 공고만 필터링해
로컬 txt 파일에 기록하는 Windows 로컬 자동화 스크립트.

- Windows 작업 스케줄러로 매일 점심 무렵 자동 실행
- 두 플랫폼(사람인·원티드)에서 공고 수집, 결과를 단일 파일에 통합
- 신규 공고만 추가(append) 방식으로 누적 기록

## Tech Stack

- **Language**: Python 3.11+
- **Job data source**:
  - 사람인 공개 검색 페이지 스크래핑 (`https://www.saramin.co.kr/zf_user/search/recruit`)
    - HTML 파싱: `beautifulsoup4`
  - 원티드 비공식 API (`https://www.wanted.co.kr/api/v4/jobs`)
  - HTTP 통신: `requests`
- **Config / secrets**: `python-dotenv` (사람인 공식 API 승인 시 키 로드용으로 유지)
- **Runtime**: Windows 로컬, Windows 작업 스케줄러(Task Scheduler)
- **Output**: UTF-8 txt 파일 (단일 누적 파일 `output/jobs_all.txt`)

## Project Structure

```
/
├── fetch_jobs.py        # 메인 실행 스크립트
├── config.ini           # 필터 조건 정의 (직무·지역·경력 등) — INI 형식, 코드 지식 없이 수정 가능
├── requirements.txt
├── .env                 # API 키 (Git 제외, 현재 선택 사항)
├── .env.example         # 키 템플릿 (Git 포함)
├── .gitignore
├── README.md
├── CLAUDE.md
├── output/              # txt 결과 파일 저장 폴더
│   └── jobs_all.txt
├── tests/
│   └── test_fetch_jobs.py
└── docs/                # 기획·설계 문서 + 세션 진행 기록
    ├── PRD.md
    ├── SPEC.md
    ├── PLAN.md
    ├── PROGRESS.md
    └── TEST_RESULT.md
```

프로젝트 루트에는 실행에 직접 필요한 파일(진입점, 설정 파일, 의존성 목록, 표준 문서)만 둔다.
세션 진행 기록·테스트 결과처럼 실행에 필요 없는 문서는 `docs/`에 둔다.

## Commands

### 환경 구성 (최초 1회)

```bash
# 가상환경 생성 및 활성화 (venv 사용 — 전역 Python 환경 오염 방지)
python -m venv venv
source venv/Scripts/activate

# 의존성 설치
pip install -r requirements.txt
```

### 실행

```bash
# 가상환경 활성화 후 실행
source venv/Scripts/activate
python fetch_jobs.py

# 또는 가상환경 Python 직접 지정 (Task Scheduler 등록용)
venv/Scripts/python.exe fetch_jobs.py
```

### 테스트

```bash
source venv/Scripts/activate
python -m pytest tests/ -v
```

### Windows 작업 스케줄러 등록 (예시)

작업 스케줄러 → 새 작업 → 트리거: 매일 12:00 → 동작:

- 프로그램: `C:\Users\mypc\Desktop\new\venv\Scripts\python.exe`
- 인수: `fetch_jobs.py`
- 시작 위치: `C:\Users\mypc\Desktop\new`

## Code Style

이 프로젝트는 단일 실행 스크립트 수준이므로 과도한 추상화를 피한다.

- 함수 단위로 역할 분리 (수집 / 필터링 / 파일 저장)
- 클래스 사용 최소화 — 단순 함수와 모듈로 구성
- 타입 힌트 사용 (함수 시그니처 수준)
- 주석은 WHY가 명확하지 않을 때만 작성, 코드 설명성 주석 금지
- 파일 하나당 150줄 이하를 목표로 유지
- 포매터: `black`, 린터: `ruff` (설정은 기본값 사용)

## Security Rules

- API access-key는 반드시 `.env` 파일에만 저장하고, 코드에 직접 쓰지 않는다.
- `.env` 파일은 `.gitignore`에 포함해 절대 커밋하지 않는다.
- **`.env` 파일은 Claude가 수정하지 않는다.** 키 값 변경은 사용자가 직접 한다.
- `.env.example`에는 실제 키 값 없이 변수 이름과 형식만 기재한다.

```
# .env.example — 현재 필수 항목 없음
# 사람인 공식 API 승인 시: SARAMIN_ACCESS_KEY=your_access_key_here
```

## Workflow Rules

1. **구현 전 문서 확인**: `docs/PRD.md` → `docs/SPEC.md` → `docs/PLAN.md` 순서로 읽은 뒤 작업 시작
2. **단계 단위 구현**: `docs/PLAN.md`에 정의된 Phase를 한 번에 하나씩만 구현
3. **테스트 후 완료 처리**: 각 Phase 구현 후 반드시 테스트 실행, 통과 후 다음 단계 진행
4. **변경 기록**: 동작 방식·파라미터·파일 형식이 바뀌면 `docs/SPEC.md`를 해당 시점에 업데이트
5. **Phase 완료 보고**: Phase 하나가 끝나면 무엇을 구현했는지 사용자에게 요약 보고 후 다음 지시 대기
6. **필터 변경 시 실데이터 검증**: 필터링 로직을 바꾸면 `fetch_saramin_all()`/`fetch_wanted_all()`로 실제 사람인·원티드 데이터를 가져와 필터 전후 결과를 수동 대조하고, 정밀도(오탐)·재현율(누락)을 확인한 뒤 완료 보고

## 다음 단계

v1(Phase 1~4)·v2(config.ini 전환 및 실데이터 검증 기반 필터 수정) 완료. v3 로드맵(Phase 5 안정성/신뢰성,
Phase 6 필터/매칭 고도화, Phase 7 지원 상태 추적)은 `docs/PLAN.md`에 계획만 수립된 상태이며 구현은
착수하지 않았다 — 작업 재개 시 `docs/PLAN.md`의 Phase 5~7을 먼저 확인할 것.

## Scraping & API Constraints

- **사람인 스크래핑**: 공개 검색 페이지 HTML 파싱 (`days=1` 파라미터로 오늘 공고 필터)
  - 페이지당 최대 40건, 페이지네이션으로 전체 수집
  - HTTP 오류 시 **1회** 재시도, 실패 시 해당 소스 건너뛰고 원티드 결과만 사용
- **원티드 비공식 API**: 인증 없이 JSON 응답 수신
  - 페이지당 20건, offset 기반 페이지네이션
  - HTTP 오류 시 **1회** 재시도, 실패 시 해당 소스 건너뛰고 사람인 결과만 사용
