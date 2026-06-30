# SPEC — 사람인 채용 공고 자동 수집기

_작성일: 2026-06-30 | 기반 문서: PRD.md_

---

## 1. 모듈 구성

```
fetch_jobs.py   ← 진입점. 전체 흐름 조율
config.py       ← 사용자 필터 조건 정의
```

함수 단위로 역할을 분리하되, 별도 모듈 파일은 만들지 않는다 (스크립트 수준 프로젝트).

---

## 2. 사람인 API 명세

### 2-1. 엔드포인트

```
GET https://oapi.saramin.co.kr/job-search
```

### 2-2. 인증

- 헤더 또는 쿼리 파라미터에 `access-key` 전달
- 키는 `.env`의 `SARAMIN_ACCESS_KEY`에서 로드

```python
headers = {"Accept": "application/json"}
params  = {"access-key": API_KEY, ...}
```

### 2-3. 요청 파라미터

| 파라미터 | 값 | 설명 |
|---|---|---|
| `access-key` | `str` | API 인증키 |
| `published` | `1` | 오늘 등록된 공고만 조회 |
| `count` | `110` | 회당 최대 조회 건수 |
| `start` | `0, 110, 220, …` | 페이지네이션 오프셋 |
| `sort` | `RL` | 최신순 정렬 |

> **OQ1 해결 — API 필터 vs 로컬 필터:**
> API 파라미터(키워드·직무코드·지역코드)는 사용하지 않는다.
> 이유: 코드 값(job_cd, loc_mcd) 매핑 테이블 관리 부담이 크고,
> 사용자가 `config.py`를 수정할 때 코드 값까지 찾아야 하는 불편이 생긴다.
> 대신 `published=1`로 오늘 공고만 가져온 뒤 전량 로컬 필터링한다.
> 하루 신규 공고 수는 수백 건 수준으로 API 호출 횟수(500회/일)에 여유가 있다.

### 2-4. 페이지네이션

```python
start = 0
while True:
    response = call_api(start=start, count=110)
    jobs = response["jobs"]["job"]
    if not jobs:
        break
    process(jobs)
    if start + 110 >= int(response["jobs"]["total"]):
        break
    start += 110
```

### 2-5. 응답 필드 매핑

API JSON → 내부 dict로 정규화.

| 내부 키 | API 경로 | 비고 |
|---|---|---|
| `id` | `job.id` | 중복 판단 기준 |
| `company` | `job.company.detail.name` | |
| `title` | `job.position.title` | |
| `location` | `job.position.location.name` | |
| `job_type` | `job.position.job-type.name` | 정규직·계약직 등 |
| `experience` | `job.position.experience-level.name` | 경력 1~3년 등 |
| `keyword` | `job.keyword` | 쉼표 구분 문자열 |
| `url` | `job.url` | |
| `deadline` | `job.expiration-timestamp` | Unix timestamp → `YYYY-MM-DD` |

```python
def normalize(job: dict) -> dict:
    exp = job.get("position", {}).get("experience-level", {})
    return {
        "id":         job["id"],
        "company":    job["company"]["detail"]["name"],
        "title":      job["position"]["title"],
        "location":   job["position"]["location"]["name"],
        "job_type":   job["position"]["job-type"]["name"],
        "experience": exp.get("name", ""),
        "keyword":    job.get("keyword", ""),
        "url":        job["url"],
        "deadline":   ts_to_date(job.get("expiration-timestamp", "")),
    }
```

---

## 3. 필터 명세 (`config.py`)

### 3-1. 설정 변수

```python
# config.py

KEYWORDS: list[str] = ["Python", "백엔드"]
# 공고 title 또는 keyword 필드에 하나라도 포함되면 통과 (대소문자 무시)
# 빈 리스트 [] → 전체 허용

LOCATIONS: list[str] = ["서울", "판교"]
# location 필드에 하나라도 포함되면 통과
# 빈 리스트 [] → 전체 허용

CAREER_TYPE: str | None = None
# "신입" | "경력" | "신입·경력" | None (전체 허용)
# job_type이 아닌 experience-level 코드로 판단 (아래 참고)

EXP_MIN: int | None = 1   # 최소 경력 연수 (None → 하한 없음)
EXP_MAX: int | None = 5   # 최대 경력 연수 (None → 상한 없음)
```

### 3-2. 필터 적용 로직

```
키워드 필터:
  KEYWORDS 가 비어 있으면 → 통과
  아니면 → title.lower() 또는 keyword.lower() 에 KEYWORDS 중 하나라도 포함 → 통과

지역 필터:
  LOCATIONS 가 비어 있으면 → 통과
  아니면 → location 에 LOCATIONS 중 하나라도 포함 → 통과

경력 유형 필터:
  CAREER_TYPE 이 None → 통과
  아니면 → experience 필드에 CAREER_TYPE 문자열 포함 → 통과

경력 연차 필터:
  EXP_MIN, EXP_MAX 모두 None → 통과
  아니면 → experience 필드에서 숫자 추출 후 범위 비교
  추출 불가(예: "경력무관") → 통과 (관대하게 처리)
```

모든 필터를 AND 조건으로 통과해야 최종 저장된다.

---

## 4. 중복 방지 및 X 마커 명세

### 4-1. ID 관리 파일 구조

| 파일 | 역할 |
|---|---|
| `output/jobs_all.txt` | 현재 보관 중인 공고 목록. 파싱해서 활성 ID 추출 |
| `output/dismissed_ids.txt` | 사용자가 X 마커로 제거한 공고 ID. 영구 제외 목록 |

`seen_ids.txt`는 사용하지 않는다.  
**`jobs_all.txt` 자체가 "현재 남아 있는 공고"의 소스 오브 트루스**이므로,
런타임에 파일을 파싱해서 활성 ID를 추출하는 방식으로 중복을 방지한다.

### 4-2. 활성 ID 추출

```python
def load_active_ids(jobs_path: str) -> set[str]:
    """jobs_all.txt 에서 [ID] 줄을 파싱해 현재 파일에 있는 ID 집합 반환."""
    if not os.path.exists(jobs_path):
        return set()
    ids = set()
    with open(jobs_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("[ID]"):
                ids.add(line.split(None, 1)[1].strip())
    return ids
```

### 4-3. dismissed_ids 관리

```python
def load_dismissed_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def append_dismissed_ids(path: str, ids: list[str]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for id_ in ids:
            f.write(id_ + "\n")
```

### 4-4. 제외 기준

새 공고를 저장할 때 다음 중 하나라도 해당하면 건너뜀:

```
active_ids    ← jobs_all.txt 에 현재 존재하는 공고
dismissed_ids ← 사용자가 X 마커로 영구 제외한 공고

skip_ids = active_ids | dismissed_ids
```

---

## 4-5. X 마커 처리 명세

### 마커 형식

사용자가 `jobs_all.txt`를 열어 관심 없는 공고 블록의 **구분선 바로 다음 줄**에 `[X]`를 입력한다.

```
════════════════════════════════════════════════
[X]
[수집일] 2024-12-10
[회사]   카카오
[제목]   관심 없는 공고
...
════════════════════════════════════════════════
```

`[X]`는 대소문자 모두 인식(`[x]`도 허용). 앞뒤 공백 무시.

### 처리 흐름

스크립트 실행 시 API 호출 전에 먼저 수행한다.

```
process_x_markers(jobs_path, dismissed_path):
  1. jobs_all.txt 를 블록 단위로 파싱
  2. [X] 마커가 있는 블록 식별
  3. 해당 블록에서 [ID] 줄로 공고 ID 추출
  4. 추출한 ID → dismissed_ids.txt 에 append
  5. [X] 마커 블록을 제거한 나머지로 jobs_all.txt 덮어쓰기
  6. 처리된 공고 수 콘솔 출력
```

### 블록 파싱 기준

- 블록 시작: `═` 문자로만 이루어진 줄 (48자)
- 블록 종료: 다음 `═` 줄 직전까지
- `[ID]`가 없는 블록(손상된 항목)은 X 마커 여부와 무관하게 보존

---

## 5. 출력 파일 명세

### 5-1. 결과 파일

경로: `output/jobs_all.txt`  
인코딩: UTF-8  
모드: append (`a`)

공고 1건 형식:

```
════════════════════════════════════════════════
[수집일] 2024-12-10
[회사]   카카오
[제목]   백엔드 개발자 (Python)
[조건]   서울 강남구 | 정규직 | 경력 1~3년
[직무]   Python, Django, REST API
[링크]   https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=73261234
[마감]   2024-12-31
[ID]     73261234
════════════════════════════════════════════════
```

- `[ID]` 줄은 **항상 마지막 줄**에 고정 (블록 파싱 시 ID 추출에 사용)
- `[조건]` 줄: `location | job_type | experience` 순, 항목이 빈 문자열이면 해당 항목 생략
- `[직무]` 줄: `keyword` 필드가 비어 있으면 줄 전체 생략
- `[마감]` 줄: deadline 변환 실패 시 줄 전체 생략
- 구분선: `═` 48개

### X 마커 사용 예시 (사용자가 직접 편집)

```
════════════════════════════════════════════════
[X]
[수집일] 2024-12-10
[회사]   카카오
[제목]   백엔드 개발자 (Python)
[조건]   서울 강남구 | 정규직 | 경력 1~3년
[직무]   Python, Django, REST API
[링크]   https://www.saramin.co.kr/...
[마감]   2024-12-31
[ID]     73261234
════════════════════════════════════════════════
```

다음 실행 시 이 블록은 파일에서 삭제되고 ID `73261234`는 `dismissed_ids.txt`에 추가된다.

### 5-2. dismissed_ids 파일

경로: `output/dismissed_ids.txt`  
인코딩: UTF-8

```
73261234
73261235
```

---

## 6. 오류 처리 명세

| 상황 | 처리 |
|---|---|
| API 호출 실패 (네트워크 오류) | 1회 재시도 후 오류 메시지 출력 및 종료 |
| API 응답 4xx / 5xx | 재시도 없이 상태 코드와 메시지 출력 후 종료 |
| API 응답 파싱 실패 (KeyError 등) | 해당 공고 건너뜀, 경고 메시지 출력 후 계속 |
| `output/` 디렉토리 없음 | 자동 생성 |
| `.env` 파일 없음 / 키 누락 | 즉시 종료, 안내 메시지 출력 |

---

## 7. 실행 흐름 (fetch_jobs.py)

```
main()
 ├─ [1단계: 초기화]
 │   ├─ load_config()           → .env 로드, API 키 확인
 │   └─ ensure_output_dir()     → output/ 없으면 생성
 │
 ├─ [2단계: X 마커 처리] ← API 호출 전에 먼저 실행
 │   └─ process_x_markers()
 │       ├─ jobs_all.txt 블록 파싱
 │       ├─ [X] 블록 식별 → ID 추출
 │       ├─ dismissed_ids.txt 에 해당 ID append
 │       └─ [X] 블록 제거 후 jobs_all.txt 덮어쓰기
 │
 ├─ [3단계: 중복 방지 기준 로드]
 │   ├─ active = load_active_ids()     → jobs_all.txt 파싱
 │   └─ dismissed = load_dismissed_ids() → dismissed_ids.txt 읽기
 │       skip_ids = active | dismissed
 │
 ├─ [4단계: 공고 수집 및 저장]
 │   ├─ jobs = fetch_all()              → 페이지네이션 전체 조회
 │   ├─ filtered = filter_jobs(jobs)    → config.py 조건 적용
 │   ├─ new_jobs = [j for j in filtered if j["id"] not in skip_ids]
 │   └─ write_jobs(new_jobs)            → jobs_all.txt 에 append
 │
 └─ print_summary(total, filtered, dismissed_count, new)
```

---

## 8. 의존성

```
# requirements.txt
requests==2.32.3
python-dotenv==1.0.1
```

표준 라이브러리 외 추가 패키지는 위 두 개만 사용한다.

---

## 9. 환경 변수 (`.env.example`)

```
SARAMIN_ACCESS_KEY=your_access_key_here
```

---

## 10. 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-30 | 최초 작성 |
| 2026-06-30 | seen_ids.txt 제거 → file-based dedup + dismissed_ids.txt 구조로 변경; X 마커 기능 추가; 출력 블록에 [ID] 줄 추가 |
