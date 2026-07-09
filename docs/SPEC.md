# SPEC — 사람인+원티드 채용 공고 자동 수집기

_작성일: 2026-06-30 | 최종 수정: 2026-07-09 | 기반 문서: PRD.md_

---

## 1. 모듈 구성

```
fetch_jobs.py   ← 진입점. 전체 흐름 조율. config.ini 를 load_config() 로 읽어 사용
config.ini      ← 사용자 필터 조건 정의 (INI, 코드 문법 불필요)
```

함수 단위로 역할을 분리하되, 별도 모듈 파일은 만들지 않는다 (스크립트 수준 프로젝트).
설정은 Python 모듈이 아닌 `config.ini`로 관리한다 — 표준 라이브러리 `configparser`로 파싱하며,
일반 사용자가 Python 리스트/None 문법을 몰라도 `key = value` 형태로 바로 수정할 수 있게 하기 위함이다.

---

## 2. 데이터 소스

데이터는 두 곳에서 수집한다. 각 소스에서 결과를 가져온 뒤 합산하여
동일한 필터·중복제거·저장 파이프라인에 넣는다.

### 2A. 사람인 스크래핑

#### 엔드포인트

```
GET https://www.saramin.co.kr/zf_user/search/recruit
```

#### 요청 파라미터

| 파라미터 | 예상 값 | 설명 |
|---|---|---|
| `days` | `1` | 오늘 등록된 공고만 조회 |
| `recruitPageCount` | `40` | 페이지당 최대 조회 건수 |
| `recruitPage` | `1, 2, 3, …` | 페이지 번호 |
| `sort` | `RL` | 최신순 정렬 |

> 정확한 파라미터 이름 및 페이지네이션 종료 조건은 구현 시 실제 요청으로 확인한다.

#### 파싱

`beautifulsoup4`로 HTML 파싱. 정확한 CSS 선택자는 구현 시 브라우저 개발자 도구로 확인한다.  
HTML 파서는 표준 라이브러리 `html.parser`를 사용한다 (별도 설치 불필요).

#### 필드 추출 → 내부 dict

| 내부 키 | 추출 방법 | 비고 |
|---|---|---|
| `id` | 공고 링크의 `rec_idx` 파라미터 | `"saramin_" + rec_idx` 형태 |
| `source` | — | 하드코딩 `"사람인"` |
| `company` | 회사명 요소 | |
| `title` | 공고 제목 요소 | |
| `location` | 지역 태그 | |
| `job_type` | 고용 형태 태그 | |
| `experience` | 경력 태그 | |
| `keyword` | 직무 태그 목록 | 쉼표로 join |
| `url` | 공고 상세 URL | 절대 URL로 보정 |
| `deadline` | 마감일 텍스트 | `YYYY-MM-DD`로 파싱 |

```python
def normalize_saramin(item: dict) -> dict: ...
```

### 2B. 원티드 비공식 API

#### 엔드포인트

```
GET https://www.wanted.co.kr/api/v4/jobs
```

#### 인증

없음 (인증 불필요한 공개 비공식 API).

#### 요청 파라미터

| 파라미터 | 예상 값 | 설명 |
|---|---|---|
| `job_sort` | `job.latest_order` | 최신 등록순 |
| `limit` | `20` | 페이지당 조회 건수 |
| `offset` | `0, 20, 40, …` | 페이지네이션 오프셋 |

> 오늘 공고 필터 방법 및 정확한 파라미터는 구현 시 실제 응답으로 확인한다.

#### 페이지네이션

```python
offset = 0
while True:
    response = call_wanted(offset=offset)
    jobs = response["data"]
    if not jobs:
        break
    process(jobs)
    offset += len(jobs)
```

#### 필드 추출 → 내부 dict

| 내부 키 | JSON 경로 | 비고 |
|---|---|---|
| `id` | `job["id"]` | `"wanted_" + id` 형태 |
| `source` | — | 하드코딩 `"원티드"` |
| `company` | `job["company"]["name"]` | |
| `title` | `job["position"]` | 리스팅 API는 `position` 필드가 제목 |
| `location` | `job["address"]["location"]` | 시/도 단위 (예: "서울") |
| `job_type` | — | 리스팅 API에서 미제공, 빈 문자열 |
| `experience` | `job["annual_from"]`, `job["annual_to"]` | `_wanted_experience()`로 텍스트 변환 |
| `keyword` | — | 리스팅 API에서 미제공, 빈 문자열 |
| `url` | `"https://www.wanted.co.kr/wd/" + job["id"]` | |
| `deadline` | `job["due_time"]` | 문자열(`"YYYY-MM-DD"`) 또는 `null` → `""` |

```python
def _wanted_experience(annual_from: int, annual_to: int) -> str:
    if annual_from == 0 and annual_to == 0:
        return "경력무관"
    if annual_from == 0:
        return f"신입~{annual_to}년"
    return f"경력 {annual_from}~{annual_to}년"

def normalize_wanted(item: dict) -> dict | None: ...
```

> **페이지네이션 종료**: `data` 배열이 비거나 길이가 `limit`보다 작으면 마지막 페이지.  
> **오늘 공고 필터**: Wanted 리스팅 API에 날짜 필터 없음 → 최신순 최대 100건 수집 후 ID 기반 중복 제거로 재수집 방지.

### 2C. 내부 dict 공통 포맷

두 normalize 함수가 반환하는 dict의 구조:

```python
{
    "id":         str,   # "saramin_XXXXX" 또는 "wanted_XXXXX"
    "source":     str,   # "사람인" 또는 "원티드"
    "company":    str,
    "title":      str,
    "location":   str,
    "job_type":   str,
    "experience": str,
    "keyword":    str,   # 쉼표 구분 문자열
    "url":        str,
    "deadline":   str,   # "YYYY-MM-DD" 또는 ""
}
```

### 2D. 통합 수집 함수

```python
def fetch_all() -> list[dict]:
    return deduplicate_cross_platform(fetch_saramin_all(), fetch_wanted_all())
```

### 2E. 플랫폼 간 중복 제거

같은 공고가 두 플랫폼에 올라가는 경우를 제목 유사도 + 보조 신호로 탐지한다.  
**사람인 우선** 유지 (사람인이 list 앞에 오므로 자연스럽게 유지됨).

```python
def _norm_title(title: str) -> str:
    return re.sub(r"\s+", "", title).lower()

def deduplicate_cross_platform(saramin: list[dict], wanted: list[dict]) -> list[dict]:
    result = list(saramin)
    for w in wanted:
        is_dup = any(
            SequenceMatcher(None, _norm_title(s["title"]), _norm_title(w["title"])).ratio() >= 0.85
            and (s["deadline"] == w["deadline"] or s["location"] == w["location"])
            for s in saramin
        )
        if not is_dup:
            result.append(w)
    return result
```

| 조건 | 판단 |
|---|---|
| 제목 유사도 ≥ 0.85 AND (마감일 일치 OR 지역 일치) | 중복 → Wanted 항목 제거 |
| 제목 유사도 < 0.85 | 다른 공고 → 유지 |
| 제목 비슷하나 마감일·지역 모두 다름 | 다른 공고로 간주 → 유지 |

> 나머지 케이스(표기 차이가 크거나 제목이 전혀 다를 때)는 X 마커로 수동 처리.

---

## 3. 필터 명세 (`config.ini`)

### 3-1. 설정 변수

```ini
# config.ini
[filter]

keywords = Python, 백엔드
# 공고 title 또는 keyword 필드에 하나라도 포함되면 통과 (대소문자 무시)
# 비워두면 전체 허용

locations = 서울, 판교
# location 필드에 하나라도 포함되면 통과
# 비워두면 전체 허용

career_type =
# 신입 | 경력 | 신입·경력 | 비워두면 전체 허용

exp_min = 1   # 최소 경력 연수 (비워두면 하한 없음)
exp_max = 5   # 최대 경력 연수 (비워두면 상한 없음)

exclude_keywords = 교육생, 무료교육, 설명회, 상시채용
# keywords 가 title 이 아닌 keyword(직무 태그)에만 매칭된 경우에 한해 검사.
# title 또는 job_type 에 이 목록의 단어가 포함되면 탈락 (채용 공고가 아닌 것으로 간주)
```

### 3-1a. `config.ini` 로드 (`load_config()`)

```python
def load_config(path: str) -> SimpleNamespace:
    """configparser 로 config.ini 를 읽어 KEYWORDS/LOCATIONS/CAREER_TYPE/
    EXP_MIN/EXP_MAX/EXCLUDE_KEYWORDS 속성을 가진 SimpleNamespace 로 변환한다."""
```

- 쉼표(`,`)로 구분된 값은 리스트로 분리 (`_parse_list`), 앞뒤 공백 제거, 빈 항목 무시
- 빈 문자열은 `None`으로 취급 (`_parse_optional_int`, `career_type`) → 전체 허용
- `config.ini` 파일이 없거나 `[filter]` 섹션이 없으면 모든 값을 빈 값으로 간주 (전체 허용, 오류 아님)
- fetch_jobs.py 모듈 로드 시점에 1회 `config = load_config(CONFIG_PATH)`로 전역 로드

### 3-2. 필터 적용 로직

```
키워드 필터:
  KEYWORDS 가 비어 있으면 → 통과
  title.lower() 에 KEYWORDS 중 하나라도 부분 포함 → 통과 (제목 매칭은 무조건 통과, EXCLUDE_KEYWORDS 검사 안 함)
  title 에는 없고, keyword 필드를 ","로 분리한 태그 중 KEYWORDS 와 완전히 일치(대소문자 무시)하는
    태그가 하나라도 있는 경우 →
    (title + " " + job_type).lower() 에 EXCLUDE_KEYWORDS 중 하나라도 포함되면 탈락, 아니면 통과
  둘 다 불일치 → 탈락

  ※ 태그는 부분 문자열이 아닌 완전 일치만 인정한다. 예: KEYWORDS=["기획"]일 때
    태그 "영업기획"·"기획MD"는 매칭되지 않고, 태그가 정확히 "기획"인 경우만 매칭된다.
    (사람인 직무 태그 체계상 "기획"이 "영업기획"·"마케팅기획"·"기획MD" 등 무관한
    직무의 접미사/접두사로 흔히 쓰여, 부분 문자열 매칭 시 오탐이 크게 늘어나기 때문)

지역 필터:
  LOCATIONS 가 비어 있으면 → 통과
  아니면 → location 에 LOCATIONS 중 하나라도 포함 → 통과

  ※ 원티드 API는 지역을 "경기"처럼 시/도 단위로만 제공하고 시/군/구 정보가 없다.
    "판교"·"성남" 등 시/군/구 단위 값만 LOCATIONS 에 넣으면 원티드 쪽 매칭이 항상 실패하므로,
    필요 시 "경기"처럼 상위 시/도 단위 값을 함께 추가해야 한다. 이 경우 사람인 쪽은 시/군/구
    단위 정보가 있으므로 "경기" 전역(수원·인천 등 포함)이 함께 통과되는 트레이드오프가 있다.

경력 유형 필터:
  CAREER_TYPE 이 None → 통과
  아니면 → CAREER_TYPE 에 대응하는 동등 표현 목록 중 하나라도 experience 필드에 포함되면 통과
    "신입"        → ["신입", "경력무관"]
    "경력"        → ["경력", "경력무관"]
    "신입·경력"   → ["신입", "경력", "경력무관"]
    (목록에 없는 값은 문자열 그대로 포함 여부만 검사)

  ※ "신입·경력"(신입/경력 무관하게 지원 가능)은 실제로는 "신입", "경력", "경력무관",
    "경력 3~8년"처럼 구체적 연차만 표기된 공고도 의미상 전부 포함하므로, 이런 표현도
    동등하게 통과시킨다. 세부 연차 제한은 별도의 경력 연차 필터(EXP_MIN/EXP_MAX)가 담당한다.

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

새로 저장되는 모든 공고 블록에는 **구분선 바로 다음 줄**에 빈 체크 마커 `[ ]`가 자동으로 포함된다.
관심 없는 공고를 제거하려면 이 줄을 `[X]`로 바꿔 쓴다.

```
════════════════════════════════════════════════
[X]
[수집일] 2024-12-10
[출처]   사람인
[회사]   카카오
[제목]   관심 없는 공고
...
════════════════════════════════════════════════
```

`[X]`는 대소문자 모두 인식(`[x]`도 허용). 앞뒤 공백 무시.  
마커가 `[ ]`(빈 상태)로 남아 있으면 아무 처리도 하지 않는다 — 블록 내 어디에 있어도 인식되므로 줄 위치를 꼭 지킬 필요는 없다.

### 처리 흐름

스크립트 실행 시 수집 전에 먼저 수행한다.

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
[ ]
[수집일] 2024-12-10
[출처]   사람인
[회사]   카카오
[제목]   백엔드 개발자 (Python)
[조건]   서울 강남구 | 정규직 | 경력 1~3년
[직무]   Python, Django, REST API
[링크]   https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=73261234
[마감]   2024-12-31
[ID]     saramin_73261234
════════════════════════════════════════════════
```

- `[ ]` 줄은 구분선 바로 다음, **항상 두 번째 줄**에 자동 삽입 (관심 없는 공고 표시용, [4-5](#4-5-x-마커-처리-명세) 참고)
- `[ID]` 줄은 **항상 마지막 줄**에 고정 (블록 파싱 시 ID 추출에 사용)
- `[출처]` 줄: `"사람인"` 또는 `"원티드"` — 항상 출력
- `[조건]` 줄: `location | job_type | experience` 순, 항목이 빈 문자열이면 해당 항목 생략
- `[직무]` 줄: `keyword` 필드가 비어 있으면 줄 전체 생략
- `[마감]` 줄: deadline 변환 실패 시 줄 전체 생략
- 구분선: `═` 48개

### X 마커 사용 예시 (사용자가 직접 편집)

```
════════════════════════════════════════════════
[X]
[수집일] 2024-12-10
[출처]   원티드
[회사]   카카오
[제목]   백엔드 개발자 (Python)
[조건]   서울 강남구 | 정규직 | 경력 1~3년
[직무]   Python, Django, REST API
[링크]   https://www.wanted.co.kr/wd/12345
[마감]   2024-12-31
[ID]     wanted_12345
════════════════════════════════════════════════
```

다음 실행 시 이 블록은 파일에서 삭제되고 ID `wanted_12345`는 `dismissed_ids.txt`에 추가된다.

### 5-2. dismissed_ids 파일

경로: `output/dismissed_ids.txt`  
인코딩: UTF-8

```
saramin_73261234
wanted_12345
```

---

## 6. 오류 처리 명세

| 상황 | 처리 |
|---|---|
| 사람인 스크래핑 HTTP 오류 | 1회 재시도 후 오류 메시지 출력, 해당 소스 건너뛰고 계속 |
| 사람인 HTML 파싱 오류 (AttributeError 등) | 해당 공고 건너뜀, 경고 출력 후 계속 |
| 원티드 API HTTP 오류 | 1회 재시도 후 오류 메시지 출력, 해당 소스 건너뛰고 계속 |
| 원티드 API 응답 파싱 실패 (KeyError 등) | 해당 공고 건너뜀, 경고 출력 후 계속 |
| `output/` 디렉토리 없음 | 자동 생성 |
| 두 소스 모두 실패 | 0건 처리 후 요약 출력, 정상 종료 |

> 어느 한 소스가 실패해도 나머지 소스 결과는 정상 처리한다.

---

## 7. 실행 흐름 (fetch_jobs.py)

```
main()
 ├─ [1단계: 초기화]
 │   └─ ensure_output_dir()       → output/ 없으면 생성
 │
 ├─ [2단계: X 마커 처리] ← 수집 전에 먼저 실행
 │   └─ process_x_markers()
 │       ├─ jobs_all.txt 블록 파싱
 │       ├─ [X] 블록 식별 → ID 추출
 │       ├─ dismissed_ids.txt 에 해당 ID append
 │       └─ [X] 블록 제거 후 jobs_all.txt 덮어쓰기
 │
 ├─ [3단계: 중복 방지 기준 로드]
 │   ├─ active = load_active_ids()       → jobs_all.txt 파싱
 │   └─ dismissed = load_dismissed_ids() → dismissed_ids.txt 읽기
 │       skip_ids = active | dismissed
 │
 ├─ [4단계: 공고 수집 및 저장]
 │   ├─ jobs = fetch_all()
 │   │   ├─ fetch_saramin_all()  → HTML 스크래핑
 │   │   └─ fetch_wanted_all()   → JSON API 호출
 │   ├─ filtered = filter_jobs(jobs)     → config.ini 조건 적용
 │   ├─ new_jobs = [j for j in filtered if j["id"] not in skip_ids]
 │   └─ write_jobs(new_jobs)             → jobs_all.txt 에 append
 │
 └─ print_summary(total, filtered, dismissed_count, new)
```

---

## 8. 의존성

```
# requirements.txt
requests==2.32.3
python-dotenv==1.0.1      # 사람인 공식 API 승인 시 키 로드용으로 유지
beautifulsoup4==4.12.3    # 사람인 HTML 파싱
```

HTML 파서는 표준 라이브러리 `html.parser`를 사용한다 (별도 설치 불필요).

---

## 9. 환경 변수

현재 필수 환경 변수 없음.

```
# .env.example
# 사람인 공식 API 승인 시 아래 키를 .env 파일에 추가:
# SARAMIN_ACCESS_KEY=your_access_key_here
```

---

## 10. 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-30 | 최초 작성 |
| 2026-06-30 | seen_ids.txt 제거 → file-based dedup + dismissed_ids.txt 구조로 변경; X 마커 기능 추가; 출력 블록에 [ID] 줄 추가 |
| 2026-07-09 | 사람인 공식 API → 사람인 스크래핑 + 원티드 비공식 API 이중 소스로 전환; ID에 소스 prefix 추가(`saramin_` / `wanted_`); [출처] 출력 필드 추가; beautifulsoup4 의존성 추가; 소스 실패 시 해당 소스만 건너뛰는 오류 처리 추가 |
| 2026-07-09 | 키워드 필터를 title 매칭 우선 + EXCLUDE_KEYWORDS 검사로 개선(태그로만 매칭된 무료교육·설명회·상시채용성 노이즈 제거); 출력 블록에 체크용 빈 마커 `[ ]` 자동 삽입(구분선 바로 다음 줄) |
| 2026-07-09 | 설정 파일을 `config.py`(Python) → `config.ini`(INI)로 전환 — 일반 사용자가 코드 문법 없이 편집 가능하도록 `configparser` 기반 `load_config()` 도입; 루트 정리 — `PROGRESS.md`, `TEST_RESULT.md`를 `docs/`로 이동 |
| 2026-07-10 | 실 데이터 검증에서 발견된 필터 오탐/누락 수정: (1) 키워드 태그 매칭을 부분 문자열 → 완전 일치로 변경(짧은 키워드가 무관한 복합 태그에 우연히 걸리는 문제 해결), (2) 경력 유형 필터에 동등 표현 허용(`_CAREER_EQUIVALENTS`) 추가 — "신입·경력"이 "신입"/"경력"/"경력무관"/구체적 연차 표기도 포함하도록 개선, (3) 원티드 시/도 단위 지역 한계를 config.ini 문서화(예: "경기" 추가 안내) |
