# SPEC — 채용 공고 수집·관련성 랭킹·자소서 초안 작성 도구

_작성일: 2026-06-30 | 최종 수정: 2026-08-14 (v3 재설계 반영) | 기반 문서: PRD.md_

---

## 1. 모듈 구성

```
jobfind.py                    ← 얇은 진입점. jobfind.cli.main() 호출
jobfind/cli.py                ← 서브커맨드 조율: collect / evaluate / add / select / write
jobfind/config.py             ← config.ini 로드 (filter/relevance/providers 섹션)
jobfind/collectors/saramin.py ← 사람인 목록 스크래핑 + 단건 상세 조회
jobfind/collectors/wanted.py  ← 원티드 목록/상세 API 호출
jobfind/dedup.py              ← 플랫폼 간 중복 제거
jobfind/filters.py            ← 1차 필터 (키워드/지역/경력유형/연차)
jobfind/relevance.py          ← 2차 필터 — HF 임베딩 기반 직무x도메인 랭킹
jobfind/selection.py          ← [자소서] 마커 스캔, materials/ 폴더 준비
jobfind/storage.py            ← jobs_all.txt/dismissed_ids.txt 입출력, 블록 파싱, 마커 처리
jobfind/providers/            ← AI provider 추상화 (claude_cli/codex_cli/api)
jobfind/pipeline/             ← 자소서 오케스트레이션 (prompts.py, orchestrator.py)
config.ini                    ← 필터·관련성·provider 설정 (INI, 코드 문법 불필요)
```

v1~v2는 "별도 모듈 파일은 만들지 않는다"는 원칙의 단일 스크립트(`fetch_jobs.py`)였다. v3
재설계(Phase 8, `docs/PLAN.md` 참고)에서 AI 오케스트레이션·provider 추상화 등이 추가되며 단일
파일 관리가 불가능해져 이 원칙을 폐기하고 `jobfind/` 패키지로 전환했다. 기능 단위로 모듈을
분리하되 과도한 추상화(불필요한 클래스 계층 등)는 여전히 피한다.

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

## 4-6. 자소서 선택 마커 명세

### 마커 형식

`[ ]` 줄을 `[자소서]`로 바꾸면 해당 공고가 자소서 작성 대상으로 선택된다. `[X]`와 같은 위치를
공유하지만 동시에 두 상태일 수는 없다 (한 블록에 마커는 하나만 유효).

```
════════════════════════════════════════════════
[자소서]
[수집일] 2026-08-14
[출처]   원티드
[회사]   주밍코리아
[제목]   소프트웨어 R&D 기술기획 IP 담당
...
════════════════════════════════════════════════
```

### 처리 흐름 (`jobfind.py select`)

```
sync_materials_folders(jobs_path):
  1. jobs_all.txt 를 블록 단위로 파싱
  2. [자소서] 마커가 있는 블록 식별 → [ID] 줄로 공고 ID 추출
  3. 각 ID마다 output/cover_letters/<ID>/materials/ 폴더 생성 (이미 있으면 유지)
  4. 선택 건수와 4개 초과 여부를 반환 (4개 초과 시 콘솔에 경고만 출력, 강제 처리는 하지 않음)
```

- `[X]`와 달리 파일에서 블록을 제거하지 않는다 — 사용자가 마커를 다시 바꾸면 선택을 취소할
  수 있어야 하기 때문이다.
- 최대 4개까지만 자소서를 작성할 수 있다. 5개 이상 선택된 상태로 `jobfind.py write`를 실행하면
  안내 메시지만 출력하고 아무 것도 작성하지 않는다 — 사용자가 마커를 정리한 뒤 다시 실행한다.
- `materials/` 폴더에는 사용자가 직접 이미지(스크린샷 등)나 `notes.md`(추가 메모)를 넣어둘 수
  있으며, 자소서 계획 단계(§13)에서 참고한다.

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

- `[ ]` 줄은 구분선 바로 다음, **항상 두 번째 줄**에 자동 삽입. 세 가지 상태를 가진다:
  `[ ]`(미처리, 기본값) / `[X]`(관심 없음 — [4-5](#4-5-x-마커-처리-명세) 참고) /
  `[자소서]`(자소서 작성 대상으로 선택 — [4-6](#4-6-자소서-선택-마커-명세) 참고)
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

## 7. 실행 흐름 (jobfind.py)

v3부터는 단일 `main()`이 아니라 서브커맨드별로 흐름이 나뉜다 (`jobfind/cli.py`).

```
jobfind.py collect
 ├─ ensure_output_dir()            → output/ 없으면 생성
 ├─ process_x_markers()            → [X] 블록 제거 + dismissed_ids.txt 기록 (§4-5)
 ├─ skip_ids = active | dismissed
 ├─ jobs = fetch_all()             → fetch_saramin_all() + fetch_wanted_all() + dedup
 ├─ filtered = filter_jobs(jobs)   → config.ini [filter] 조건 적용 (§3)
 ├─ new_jobs = filtered - skip_ids
 ├─ write_jobs(new_jobs)           → jobs_all.txt 에 append
 └─ print_summary(...)

jobfind.py evaluate
 └─ evaluate_relevance()           → HF 임베딩으로 직무x도메인 랭킹, 상위 top_n건만 유지 (§11)

jobfind.py add <url>
 ├─ URL에서 소스/ID 판별 (사람인 rec_idx / 원티드 wd/<id>)
 ├─ 단건 상세 조회·정규화
 ├─ 이미 목록에 있으면 건너뜀 (ID 기준)
 └─ write_jobs([job])              → jobs_all.txt 에 append

jobfind.py select
 └─ sync_materials_folders()       → [자소서] 마커 스캔, materials/ 폴더 준비 (§4-6)

jobfind.py write
 └─ 선택된 공고(최대 4개)마다 run_for_job() 실행 → 자소서 파이프라인 (§13)
```

---

## 8. 의존성

```
# requirements.txt
requests==2.32.3
python-dotenv==1.0.1               # 사람인 공식 API 승인 시 키 로드용 + api:* provider 키 로드
beautifulsoup4==4.12.3              # 사람인 HTML 파싱
sentence-transformers==5.7.0        # 관련성 평가용 한국어 임베딩 모델 실행 (§11)
```

HTML 파서는 표준 라이브러리 `html.parser`를 사용한다 (별도 설치 불필요).
`sentence-transformers`는 `torch`를 전이 의존성으로 함께 설치하며, 최초 실행 시 모델
가중치(`jhgan/ko-sroberta-multitask`, 수백 MB)를 자동 다운로드한다.

---

## 9. 환경 변수

`config.ini [providers]`에서 `api:anthropic` / `api:openai` 백엔드를 쓸 때만 필요하다.
`claude_cli` / `codex_cli`만 쓰면 `.env`가 없어도 동작한다.

```
# .env.example
# 사람인 공식 API 승인 시 아래 키를 .env 파일에 추가:
# SARAMIN_ACCESS_KEY=your_access_key_here

# config.ini [providers]에서 api:anthropic / api:openai 백엔드를 쓸 때만 필요:
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
```

---

## 11. 관련성 평가 명세 (`jobfind/relevance.py`)

### 11-1. 목적

`config.ini [filter] keywords`는 문자열 완전/부분 일치 기반이라 "기획"으로 설정하면 의미상
가까운 "프로덕트 오너"·"그로스 매니저" 같은 공고를 못 잡는다. 관련성 평가는 로컬 임베딩
모델로 의미 기반 유사도를 계산해 이 한계를 보완한다. LLM 호출이 아니므로 비용이 들지 않는다.

### 11-2. 설정 (`config.ini [relevance]`)

```ini
[relevance]
roles = 기획, PM        # 직무 — 비워두면 이 축은 0점 처리
domains = 커머스, 게임  # 도메인/업종 — 비워두면 이 축은 0점 처리
top_n = 20               # 상위 몇 건만 jobs_all.txt에 남길지
model = jhgan/ko-sroberta-multitask
```

`roles`와 `domains`가 둘 다 비어 있으면 관련성 평가 단계 전체를 건너뛴다.

### 11-3. 점수 계산

```python
def score_axis(query: str, job_texts: list[str]) -> list[float]:
    # query와 각 job_texts의 코사인 유사도(0~1). query가 비어 있으면 전부 0.
    ...

def rank_jobs(job_texts: list[str]) -> list[float]:
    # role_scores + domain_scores 를 더한 결합 점수.
    ...
```

- `job_texts`는 각 공고의 `title + " " + keyword`.
- 직무·도메인 둘 다 가까운 공고가 최상위, 하나만 가까운 공고는 그 다음 순위가 되도록
  단순 합산한다 (가중치 없음).
- 임베딩 모델은 `functools.lru_cache`로 프로세스당 1회만 로드한다.

### 11-4. 적용 (`evaluate_relevance()`)

```
evaluate_relevance(jobs_path):
  1. jobs_all.txt 를 블록 단위로 파싱, [X] 블록은 그대로 보존
  2. 활성 블록마다 결합 점수 계산
  3. 점수 내림차순 정렬
  4. 상위 top_n건만 남기고, 순위 순서대로 jobs_all.txt 재작성
  5. 순위 밖 공고 수를 콘솔에 출력
```

- 순위 밖으로 밀린 공고는 `[X]`와 달리 `dismissed_ids.txt`에 기록되지 않는다 — 다음 수집에서
  경쟁 구도가 바뀌면 다시 상위 `top_n`에 들 수 있어야 하기 때문이다 (영구 제외가 아니라
  "이번엔 순위 밖"이라는 의미).
- 아무 것도 잘리지 않아도(전체 공고 수 ≤ top_n) 순위 순서를 파일에 반영하기 위해 항상
  다시 쓴다.

### 11-5. 파인튜닝에 대해

사전학습 모델(`jhgan/ko-sroberta-multitask`)만 그대로 사용한다. 파인튜닝은 라벨 데이터가
없어 범위 밖이다 — `[X]` 마커로 걸러낸 이력이 쌓이면 이후 파인튜닝 데이터로 활용할 수 있다는
점만 기록해둔다 (착수 시점 미정).

---

## 12. AI Provider 프로토콜 (`jobfind/providers/`)

### 12-1. 인터페이스

```python
class Provider(Protocol):
    def run(self, system_prompt: str, user_prompt: str,
            images: list[Path] | None = None) -> str: ...


def get_provider(spec: str) -> Provider:
    # spec: "claude_cli" | "codex_cli" | "api:anthropic" | "api:openai"
    ...
```

호출마다 독립된 subprocess/API 요청이라 이전 호출과 대화 맥락을 공유하지 않는다 — 자소서
파이프라인(§13)의 "격리된 평가"를 이 특성으로 보장한다.

### 12-2. `claude_cli`

```
subprocess.run(["claude", "-p", user_prompt,
                "--append-system-prompt", system_prompt,
                "--output-format", "json",
                "--allowedTools", "" 또는 "Read"],
               cwd=<materials 폴더 또는 임시 폴더>)
```

- `images`가 있으면 `cwd`를 그 이미지들이 있는 `materials/` 폴더로 잡고 `--allowedTools Read`를
  줘서 그 폴더의 파일만 읽게 한다 (repo 전체 접근은 차단 — 격리 유지). 프롬프트에 이미지
  파일명을 안내해 Read 툴로 읽도록 지시한다.
- `images`가 없으면 `cwd`를 임시 폴더로 잡고 `--allowedTools ""`로 모든 툴을 차단한다 —
  이 프로젝트의 CLAUDE.md 등 무관한 컨텍스트가 우연히 섞이는 것도 방지한다.
- 응답은 `--output-format json`의 `result` 필드에서 추출한다. `is_error: true`거나
  `returncode != 0`이면 `RuntimeError`를 발생시킨다.
- 실제 `claude -p` 호출로 텍스트 전용/이미지 포함 양쪽 다 검증 완료 (Phase 11 기록 참고).

### 12-3. `codex_cli`

공개된 `codex exec <prompt>` 비대화형 실행 방식을 기준으로 작성했으나, 개발 환경에 Codex
CLI가 설치되어 있지 않아 실제 플래그를 검증하지 못했다. 실사용 전 `codex --help`로 재확인이
필요하다 (미결 사항 OQ4, `docs/PRD.md` 참고).

### 12-4. `api:anthropic` / `api:openai`

`requests`로 각 Messages/Chat Completions API를 직접 호출한다. 키는 `.env`의
`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`에서 읽으며, 없으면 명확한 오류를 낸다. 이미지는
base64로 인코딩해 API의 image content block(Anthropic) / image_url(OpenAI)로 첨부한다.
호출당 별도 과금이 발생한다.

---

## 13. 자소서 오케스트레이션 파이프라인 (`jobfind/pipeline/`)

### 13-1. 흐름 (`run_for_job(job_id, job_text)`)

```
posting_text = fetch_posting_text(공고 링크)   → §13-3
job_text += "[공고 상세 설명]\n" + posting_text  (있을 때만)

plan = planner.run(planner_prompt(job_text, profile, materials_dir), images=자소서 이미지)
plan_review = plan_evaluator.run(plan_evaluator_prompt(job_text, plan))

if plan_review 가 "NEEDS_REVISION"으로 시작:
    plan = planner.run(planner_revision_prompt(..., plan, plan_review), images=자소서 이미지)

draft = writer.run(writer_prompt(job_text, profile, plan))
draft_review = draft_evaluator.run(draft_evaluator_prompt(job_text, draft))

저장: output/cover_letters/<job_id>/{plan,plan_review,draft,draft_review}.md
```

- `job_text`는 `jobs_all.txt`의 원본 블록 텍스트를 그대로 쓴다 (별도 구조화 파싱 없음).
- `plan_evaluator`/`draft_evaluator`는 `profile.md`나 이미지를 받지 않는다 — 평가 대상
  산출물과 공고 정보만으로 판단하게 해 "필요한 것만 최소 주입"한다.
- 초안 평가 이후 자동 재작성 루프는 없다. 평가 의견은 `draft_review.md`로 그대로 남기고,
  재작성이 필요하면 사용자가 다시 `write`를 실행하도록 한다 (설계 원칙, `docs/PLAN.md`
  Phase 12 참고).

### 13-2. `profile.md`

사용자가 자유 텍스트로 이력·경험·강점을 적어두는 파일. `.gitignore` 대상이며, 실제 내용 없는
`profile.md.example` 템플릿만 Git에 포함한다. 없으면 빈 문자열로 취급해 파이프라인은 계속
진행한다 (개인화 없이 일반적인 초안이 나옴).

### 13-3. 공고 상세 설명 보강 (`fetch_posting_text()`)

목록 페이지에서 긁은 요약(제목·조건·태그)만으로는 planner/writer가 진부하고 회사 특정성
없는 결과를 내는 문제가 Phase 12 실데이터 검증에서 확인됐다. 이를 보완하기 위해 provider
호출 전에 서버 측(Python)에서 한 번 상세 설명을 가져와 `job_text`에 얹는다 — provider
종류(claude_cli/codex_cli/api)와 무관하게 동일하게 동작한다.

| 소스 | 방법 | 결과 |
|---|---|---|
| 원티드 | 상세 API의 `detail.intro/main_tasks/requirements/preferred_points/benefits` 필드를 그대로 가져와 라벨을 붙여 합침 (`fetch_wanted_description()`) | 실제 담당업무·자격요건이 반영됨 (검증 완료) |
| 사람인 | (검토됨, 미채택) 정적 페이지 요청 + `BeautifulSoup.get_text()` | 본문이 자바스크립트로 렌더링돼 헤더/내비게이션 텍스트만 잡힘 — 노이즈만 추가하므로 **빈 문자열 반환으로 되돌림** (알려진 한계, PRD OQ5) |

### 13-4. materials/ 이미지

`output/cover_letters/<job_id>/materials/`의 이미지 파일(`.png/.jpg/.jpeg/.webp/.gif`)은
`planner`(및 계획 재작성) 호출에만 전달한다 — 계획 산출물이 이미지에서 뽑아낸 정보를 텍스트로
흡수하므로 이후 단계(평가/작성)는 원본 이미지가 다시 필요하지 않다. 같은 폴더의 `notes.md`가
있으면 텍스트로 프롬프트에 포함한다.

---

## 14. 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-30 | 최초 작성 |
| 2026-06-30 | seen_ids.txt 제거 → file-based dedup + dismissed_ids.txt 구조로 변경; X 마커 기능 추가; 출력 블록에 [ID] 줄 추가 |
| 2026-07-09 | 사람인 공식 API → 사람인 스크래핑 + 원티드 비공식 API 이중 소스로 전환; ID에 소스 prefix 추가(`saramin_` / `wanted_`); [출처] 출력 필드 추가; beautifulsoup4 의존성 추가; 소스 실패 시 해당 소스만 건너뛰는 오류 처리 추가 |
| 2026-07-09 | 키워드 필터를 title 매칭 우선 + EXCLUDE_KEYWORDS 검사로 개선(태그로만 매칭된 무료교육·설명회·상시채용성 노이즈 제거); 출력 블록에 체크용 빈 마커 `[ ]` 자동 삽입(구분선 바로 다음 줄) |
| 2026-07-09 | 설정 파일을 `config.py`(Python) → `config.ini`(INI)로 전환 — 일반 사용자가 코드 문법 없이 편집 가능하도록 `configparser` 기반 `load_config()` 도입; 루트 정리 — `PROGRESS.md`, `TEST_RESULT.md`를 `docs/`로 이동 |
| 2026-07-10 | 실 데이터 검증에서 발견된 필터 오탐/누락 수정: (1) 키워드 태그 매칭을 부분 문자열 → 완전 일치로 변경(짧은 키워드가 무관한 복합 태그에 우연히 걸리는 문제 해결), (2) 경력 유형 필터에 동등 표현 허용(`_CAREER_EQUIVALENTS`) 추가 — "신입·경력"이 "신입"/"경력"/"경력무관"/구체적 연차 표기도 포함하도록 개선, (3) 원티드 시/도 단위 지역 한계를 config.ini 문서화(예: "경기" 추가 안내) |
| 2026-08-14 | v3 재설계(Phase 8~13): `fetch_jobs.py` 단일 스크립트 → `jobfind/` 패키지 전환; 관련성 평가를 role_description+threshold 이진 필터에서 roles/domains 결합 랭킹(top_n)으로 재설계; `jobfind.py add`(수동 추가)·`select`(`[자소서]` 마커, materials/)·`write`(자소서 파이프라인) 커맨드 추가; AI provider 추상화(`claude_cli`/`codex_cli`/`api:anthropic`/`api:openai`) 추가; 자소서 계획→계획평가→(재작성)→작성→초안평가 파이프라인 추가; 원티드 상세 API 기반 공고 설명 보강 추가(사람인은 JS 렌더링 한계로 미적용) |
