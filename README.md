# 채용 공고 자동 수집기

사람인·원티드에서 매일 채용 공고를 수집해 로컬 txt 파일에 누적 기록하는 Windows 자동화 스크립트.

---

## 주요 기능

- **이중 소스 수집**: 사람인 공개 검색 페이지 스크래핑 + 원티드 비공식 API 동시 조회
- **교차 중복 제거**: 두 플랫폼에 동시 게재된 공고를 제목 유사도(≥ 85%)로 탐지해 하나만 저장
- **조건 필터링**: 키워드·지역·경력 유형·연차를 `config.py`에서 자유롭게 설정
- **채용 공고만 필터링**: 직무 태그만으로 우연히 걸리는 무료교육·설명회·상시채용성 공고는 `EXCLUDE_KEYWORDS`로 자동 제외
- **신규 공고만 추가**: 이미 저장된 공고(활성 ID)와 사용자가 X 처리한 공고(dismissed ID)는 건너뜀
- **X 마커 처리**: 모든 공고 블록에 체크용 빈 마커(`[ ]`)가 자동 삽입되며, `[X]`로 바꾸면 다음 실행 시 자동 제거·영구 제외
- **Windows 작업 스케줄러**: 매일 점심 무렵 자동 실행

---

## 프로젝트 구조

```
/
├── fetch_jobs.py        # 메인 실행 스크립트
├── config.py            # 필터 조건 (키워드·지역·경력)
├── requirements.txt
├── .env.example         # API 키 템플릿 (현재 필수 항목 없음)
├── output/
│   ├── jobs_all.txt     # 누적 공고 파일 (자동 생성)
│   └── dismissed_ids.txt # X 처리된 ID 목록 (자동 생성)
└── docs/
    ├── PRD.md
    ├── SPEC.md
    └── PLAN.md
```

---

## 설치

Python 3.11 이상 필요.

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/Scripts/activate

# 의존성 설치
pip install -r requirements.txt
```

---

## 필터 설정 (`config.py`)

```python
# 공고 제목·직무 키워드 중 하나라도 포함 → 통과 (빈 리스트 = 전체 허용)
KEYWORDS: list[str] = ["Python", "백엔드"]

# 근무 지역 중 하나라도 포함 → 통과 (빈 리스트 = 전체 허용)
LOCATIONS: list[str] = ["서울", "판교"]

# 경력 유형: "신입" | "경력" | "신입·경력" | None (전체 허용)
CAREER_TYPE: str | None = None

# 경력 연차 범위 (None = 제한 없음)
EXP_MIN: int | None = 1
EXP_MAX: int | None = 5

# 채용 공고가 아닌 것으로 간주해 제외할 단어
# KEYWORDS가 제목이 아닌 직무 태그에만 걸린 경우에 한해, 제목·고용형태에 이 단어가 있으면 탈락
EXCLUDE_KEYWORDS: list[str] = ["교육생", "무료교육", "설명회", "상시채용"]
```

`config.py`를 수정하고 저장한 뒤 다시 실행하면 즉시 반영된다.

---

## 실행

```bash
source venv/Scripts/activate
python fetch_jobs.py
```

콘솔 출력 예시:

```
[2026-07-09 12:00] 조회: 180건 | X 처리: 2건 | 필터 통과: 12건 | 신규 저장: 5건
```

---

## 출력 파일 형식 (`output/jobs_all.txt`)

```
════════════════════════════════════════════════
[ ]
[수집일] 2026-07-09
[출처]   사람인
[회사]   (주)예시기업
[제목]   Python 백엔드 개발자
[조건]   서울 강남구 | 정규직 | 경력 2~5년
[직무]   Python, Django, REST API
[링크]   https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345
[마감]   2026-07-31
[ID]     saramin_12345
════════════════════════════════════════════════
```

### X 마커 사용법

모든 공고 블록에는 구분선 바로 다음 줄에 빈 체크 마커 `[ ]`가 자동으로 붙어 있다.
관심 없는 공고는 이 줄을 `[X]`로 바꿔 쓰면 된다 (꼭 이 줄이 아니어도, 블록 안 어디에 `[X]` 줄을 추가해도 인식된다).

```
════════════════════════════════════════════════
[X]
[수집일] 2026-07-09
[출처]   원티드
...
[ID]     wanted_99999
════════════════════════════════════════════════
```

다음 실행 시 해당 블록이 파일에서 제거되고, ID가 `dismissed_ids.txt`에 영구 기록되어 이후 실행에서 다시 수집되지 않는다.

---

## Windows 작업 스케줄러 등록

매일 점심에 자동 실행하도록 등록하는 방법이다.

### GUI로 등록하기

1. `Win + S` → **작업 스케줄러** 검색 후 실행
2. 오른쪽 패널 **작업 만들기** 클릭
3. **일반** 탭
   - 이름: `채용공고 자동수집`
   - "사용자가 로그온되어 있는지 여부에 관계없이 실행" 선택 (선택 사항)
4. **트리거** 탭 → 새로 만들기
   - 작업 시작: **일정에 따라**
   - 매일 / 시작 시간: `12:00:00`
5. **동작** 탭 → 새로 만들기
   - 동작: **프로그램 시작**
   - 프로그램/스크립트:
     ```
     C:\Users\mypc\Desktop\new\venv\Scripts\python.exe
     ```
   - 인수 추가:
     ```
     fetch_jobs.py
     ```
   - 시작 위치(선택 사항):
     ```
     C:\Users\mypc\Desktop\new
     ```
6. **확인** → Windows 계정 비밀번호 입력

### 명령어로 등록하기 (한 번에)

bash를 **관리자 권한**으로 열고 아래 명령어를 실행한다 (`schtasks.exe`는 Windows 기본 CLI라 bash에서도 그대로 호출 가능).

```bash
schtasks /Create \
    /TN "채용공고 자동수집" \
    /TR "\"C:\Users\mypc\Desktop\new\venv\Scripts\python.exe\" fetch_jobs.py" \
    /SC DAILY \
    /ST 12:00 \
    /RL HIGHEST
```

> 시작 위치(`WorkingDirectory`)는 `schtasks`에 직접 지정하는 옵션이 없으므로, `fetch_jobs.py`가 상대 경로 대신 스크립트 자체 위치 기준으로 동작하는지 확인하거나 `/TR`에 `cmd /c "cd /d C:\Users\mypc\Desktop\new && venv\Scripts\python.exe fetch_jobs.py"` 형태로 감싸 실행 위치를 고정한다.

### 수동 실행 (등록 후 즉시 테스트)

```bash
schtasks /Run /TN "채용공고 자동수집"
```

### 등록 확인 및 삭제

```bash
# 등록된 작업 확인
schtasks /Query /TN "채용공고 자동수집"

# 삭제
schtasks /Delete /TN "채용공고 자동수집" /F
```

---

## 테스트

```bash
source venv/Scripts/activate
python -m pytest tests/ -v
```

51개 단위 테스트 전부 통과 확인됨.

---

## 기술 스택

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.11+ |
| 사람인 | 공개 검색 페이지 HTML 스크래핑 (beautifulsoup4) |
| 원티드 | 비공식 API (`/api/v4/jobs`), 인증 불필요 |
| HTTP | requests |
| 환경 변수 | python-dotenv (향후 공식 API 키 대비) |
| 런타임 | Windows 로컬 + 작업 스케줄러 |
| 출력 | UTF-8 txt 단일 누적 파일 |
