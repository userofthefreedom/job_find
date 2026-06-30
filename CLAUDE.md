# CLAUDE.md

## Project Overview

사람인 Open API를 사용해 매일 채용 공고를 가져오고,
사용자가 정의한 조건(직무·지역·경력 등)에 맞는 공고만 필터링해
로컬 txt 파일에 기록하는 Windows 로컬 자동화 스크립트.

- Windows 작업 스케줄러로 매일 점심 무렵 자동 실행
- 공식 API 사용(무단 크롤링 없음), 하루 500회 호출 한도 내에서 동작
- 신규 공고만 추가(append) 방식으로 누적 기록

## Tech Stack

- **Language**: Python 3.11+
- **Job data source**: 사람인 Open API (`https://oapi.saramin.co.kr/job-search`)
  - HTTP 통신: `requests`
  - 인증: API access-key (`.env`에서 로드)
- **Config / secrets**: `python-dotenv` (`.env` 파일)
- **Runtime**: Windows 로컬, Windows 작업 스케줄러(Task Scheduler)
- **Output**: UTF-8 txt 파일 (날짜별 또는 단일 누적 파일)

## Project Structure

```
/
├── fetch_jobs.py        # 메인 실행 스크립트
├── config.py            # 필터 조건 정의 (직무·지역·경력 등)
├── requirements.txt
├── .env                 # API 키 (Git 제외)
├── .env.example         # 키 템플릿 (Git 포함)
├── .gitignore
├── output/              # txt 결과 파일 저장 폴더
│   └── jobs_YYYYMMDD.txt
└── docs/
    ├── PRD.md
    ├── SPEC.md
    └── PLAN.md
```

## Commands

### 환경 구성 (최초 1회)

```powershell
# 가상환경 생성 및 활성화 (venv 사용 — 전역 Python 환경 오염 방지)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt
```

### 실행

```powershell
# 가상환경 활성화 후 실행
.\venv\Scripts\Activate.ps1
python fetch_jobs.py

# 또는 가상환경 Python 직접 지정 (Task Scheduler 등록용)
.\venv\Scripts\python.exe fetch_jobs.py
```

### 테스트

```powershell
.\venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

### Windows 작업 스케줄러 등록 (예시)

작업 스케줄러 → 새 작업 → 트리거: 매일 12:00 → 동작:

- 프로그램: `C:\Users\mypc\Desktop\test\venv\Scripts\python.exe`
- 인수: `fetch_jobs.py`
- 시작 위치: `C:\Users\mypc\Desktop\test`

## Code Style

이 프로젝트는 단일 실행 스크립트 수준이므로 과도한 추상화를 피한다.

- 함수 단위로 역할 분리 (API 호출 / 필터링 / 파일 저장)
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
# .env.example
SARAMIN_ACCESS_KEY=your_access_key_here
```

## Workflow Rules

1. **구현 전 문서 확인**: `docs/PRD.md` → `docs/SPEC.md` → `docs/PLAN.md` 순서로 읽은 뒤 작업 시작
2. **단계 단위 구현**: `docs/PLAN.md`에 정의된 Phase를 한 번에 하나씩만 구현
3. **테스트 후 완료 처리**: 각 Phase 구현 후 반드시 테스트 실행, 통과 후 다음 단계 진행
4. **변경 기록**: 동작 방식·파라미터·파일 형식이 바뀌면 `docs/SPEC.md`를 해당 시점에 업데이트
5. **Phase 완료 보고**: Phase 하나가 끝나면 무엇을 구현했는지 사용자에게 요약 보고 후 다음 지시 대기

## API Limits & Constraints

- 사람인 API 무료 플랜: **하루 최대 500회** 호출
- 단일 요청 최대 조회 건수: **110건** (`count=110`)
- `published=1` 파라미터로 오늘 등록된 공고만 조회해 호출 횟수 절약
- 호출 실패(4xx/5xx) 시 재시도는 **1회**만, 그 후 오류 로그 기록 후 종료
