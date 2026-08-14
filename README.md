# 채용 공고 수집 + 자소서 초안 작성 도구

사람인·원티드에서 채용 공고를 수집해 조건에 맞는 것만 필터링하고, 로컬 임베딩 모델로
관련성 순위를 매긴 뒤, 선택한 공고에 대해 AI가 자소서 초안까지 작성해주는 CLI 도구.

모든 단계는 사용자가 명령을 실행할 때만 동작한다 (Windows 작업 스케줄러 무인 실행은 v3에서
폐기됨 — 자세한 배경은 `docs/PLAN.md` Phase 8 참고).

---

## 주요 기능

- **이중 소스 수집**: 사람인 공개 검색 페이지 스크래핑 + 원티드 비공식 API 동시 조회, 교차
  중복 제거(제목 유사도 ≥ 85%)
- **조건 필터링**: 키워드·지역·경력 유형·연차를 `config.ini`에서 자유롭게 설정
- **관련성 랭킹**: 로컬 HuggingFace 임베딩 모델(비용 없음)로 "직무"와 "도메인"을 따로 비교해
  결합 점수로 정렬, 상위 `top_n`건만 유지 — 둘 다 가까운 공고가 최상위, 순위 밖 공고는
  영구 제외되지 않고 다음 수집에서 다시 상위권에 들 수 있음
- **수동 추가**: 시스템이 못 찾은 공고도 URL로 직접 추가 가능
- **자소서 초안 작성**: `[자소서]`로 최대 4개까지 선택하면, AI가 계획 → 계획평가 →
  (필요시 재작성) → 작성 → 초안평가 순으로 초안을 만들어 저장. 각 단계는 독립 호출이라
  이전 맥락을 공유하지 않는(격리된) 평가를 받는다
- **X 마커 처리**: 관심 없는 공고는 `[X]`로 표시하면 다음 실행 시 자동 제거·영구 제외

---

## 프로젝트 구조

```
/
├── jobfind.py                  # 진입점
├── jobfind/
│   ├── cli.py                   # collect / evaluate / add / select / write
│   ├── config.py
│   ├── collectors/              # saramin.py, wanted.py
│   ├── dedup.py / filters.py / relevance.py / selection.py / storage.py
│   ├── providers/               # claude_cli / codex_cli / api
│   └── pipeline/                # prompts.py, orchestrator.py
├── config.ini                   # 필터·관련성·provider 설정
├── profile.md                   # 이력/자기소개 (직접 작성, Git 제외)
├── requirements.txt
├── .env.example
├── output/
│   ├── jobs_all.txt
│   ├── dismissed_ids.txt
│   └── cover_letters/<공고ID>/  # plan.md, plan_review.md, draft.md, draft_review.md
├── tests/
└── docs/                        # 기획 문서 + 세션 진행 기록
```

---

## 설치

Python 3.11 이상 필요.

```bash
python -m venv venv
source venv/Scripts/activate

# sentence-transformers·torch가 포함돼 있어 최초 설치에 시간이 걸릴 수 있음
pip install -r requirements.txt
```

`profile.md.example`을 복사해 `profile.md`를 만들고 자신의 이력/경험을 자유 텍스트로 채워둔다
(자소서 작성 단계에서 참고, 개인정보라 Git에는 올라가지 않음).

```bash
cp profile.md.example profile.md
```

---

## 설정 (`config.ini`)

메모장 등 아무 텍스트 편집기로 열어 `=` 뒤의 값만 바꾸면 된다.

```ini
[filter]
keywords = 기획, PM              # 제목/직무 태그에 하나라도 포함되면 통과
locations = 서울, 판교           # 비워두면 전체허용
career_type = 신입·경력
exp_min =
exp_max = 5
exclude_keywords = 교육생, 무료교육, 설명회, 상시채용

[relevance]
roles = 기획, PM                 # 직무 — 비워두면 관련성 랭킹 단계를 건너뜀
domains = 커머스, 게임           # 도메인/업종 — 직무와 도메인 둘 다 가까운 공고가 1순위
top_n = 20                       # 상위 몇 건만 유지할지
model = jhgan/ko-sroberta-multitask

[providers]
planner = claude_cli             # claude_cli | codex_cli | api:anthropic | api:openai
plan_evaluator = claude_cli
writer = claude_cli
draft_evaluator = claude_cli
```

`config.ini`를 수정하고 저장하면 다음 실행부터 즉시 반영된다.

---

## 실행

```bash
source venv/Scripts/activate

python jobfind.py collect     # 사람인+원티드 수집 → 1차 필터 → jobs_all.txt에 저장
python jobfind.py evaluate    # 직무·도메인 관련성 순 정렬, 상위 top_n건만 유지
python jobfind.py add <url>   # 공고 URL을 수동으로 추가
python jobfind.py select      # [자소서]로 표시한 공고에 materials/ 폴더 준비
python jobfind.py write       # [자소서] 선택 공고(최대 4개)의 자소서 초안 작성
```

콘솔 출력 예시:

```
[2026-08-14 12:00] 조회: 180건 | X 처리: 2건 | 필터 통과: 12건 | 신규 저장: 5건
[2026-08-14 12:01] 관련성 평가 완료 | 순위 밖 제외: 3건
```

---

## 사용 흐름

1. `jobfind.py collect` → `jobfind.py evaluate`로 관련성 높은 공고 목록을 만든다.
2. `jobs_all.txt`를 열어 훑어보며 관심 없는 공고는 `[X]`로 표시한다 (다음 실행 시 제거·영구 제외).
3. 시스템이 못 찾은 공고가 있으면 `jobfind.py add <url>`로 직접 추가한다.
4. 자소서를 쓰고 싶은 공고(최대 4개)를 `[자소서]`로 표시하고 `jobfind.py select`를 실행한다.
   생성된 `output/cover_letters/<공고ID>/materials/`에 공고 스크린샷이나 `notes.md`(추가 메모)를
   넣어두면 계획 단계에서 참고한다.
5. `jobfind.py write`를 실행하면 공고별로 `plan.md`(작성 계획) · `plan_review.md`(계획 평가) ·
   `draft.md`(자소서 초안) · `draft_review.md`(초안 평가)가 만들어진다.

---

## 출력 파일 형식 (`output/jobs_all.txt`)

```
════════════════════════════════════════════════
[ ]
[수집일] 2026-08-14
[출처]   사람인
[회사]   (주)예시기업
[제목]   Python 백엔드 개발자
[조건]   서울 강남구 | 정규직 | 경력 2~5년
[직무]   Python, Django, REST API
[링크]   https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345
[마감]   2026-08-31
[ID]     saramin_12345
════════════════════════════════════════════════
```

두 번째 줄의 마커는 세 가지 상태를 가질 수 있다.

| 마커 | 의미 | 다음 실행 시 동작 |
|---|---|---|
| `[ ]` | 아직 처리 안 함 (기본값) | 그대로 유지 |
| `[X]` | 관심 없음 | 파일에서 제거되고 `dismissed_ids.txt`에 영구 기록 (재수집 안 됨) |
| `[자소서]` | 자소서 작성 대상으로 선택 (최대 4개) | `select` 실행 시 `materials/` 폴더 생성, `write` 실행 시 초안 작성 |

---

## 테스트

```bash
source venv/Scripts/activate
python -m pytest tests/ -v
```

---

## 기술 스택

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.11+ |
| 사람인 | 공개 검색 페이지 HTML 스크래핑 (beautifulsoup4) |
| 원티드 | 비공식 API (`/api/v4/jobs`, `/api/v4/jobs/<id>`), 인증 불필요 |
| HTTP | requests |
| 관련성 평가 | sentence-transformers + jhgan/ko-sroberta-multitask (로컬, 비용 없음) |
| AI provider | claude_cli / codex_cli / api:anthropic / api:openai (역할별로 다르게 설정 가능) |
| 환경 변수 | python-dotenv |
| 런타임 | Windows 로컬, 사용자가 터미널에서 직접 실행 |
| 출력 | UTF-8 txt (`jobs_all.txt`) + 공고별 자소서 결과 (`cover_letters/<ID>/`) |
