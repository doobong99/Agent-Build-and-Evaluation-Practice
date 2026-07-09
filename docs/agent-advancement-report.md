# 월드컵 경기 결과 캡처 AI Agent 고도화 보고서

## 1. 개요

본 프로젝트는 사용자가 자연어로 특정 날짜의 월드컵 경기 결과를 요청하면, 네이버 스포츠 2026 월드컵 일정 페이지를 조회하고 해당 날짜의 경기 결과 화면을 이미지로 캡처해 응답하는 AI Agent이다.

초기 목표는 단순히 경기 결과 화면을 캡처해 파일로 저장하는 것이었지만, 실제 테스트 과정에서 실행 환경, 브라우저 자동화, 이미지 표시 방식, 날짜 보정 로직, 평가 자동화 측면에서 여러 문제가 발견되었다. 본 보고서는 고도화 과정에서 발생한 주요 문제와 해결 방식, 그리고 최종 개선 결과를 정리한다.

## 2. Agent 구성

Agent는 LangGraph Deep Agent 기반으로 구성되며, 주요 역할은 다음과 같다.

- 사용자 요청에서 날짜를 해석한다.
- `https://m.sports.naver.com/fifaworldcup2026/schedule?date=YYYY-MM-DD` 형식의 네이버 스포츠 일정 페이지를 연다.
- Playwright로 모바일 화면 기준의 경기 결과 영역을 캡처한다.
- 캡처 이미지를 `workspace/screenshots/` 아래에 저장한다.
- 응답 화면에서 이미지가 바로 보이도록 Markdown 이미지 링크를 반환한다.
- 경기가 없는 날짜는 이미지 캡처 대신 안내 문구와 전체 일정 링크를 제공한다.

관련 주요 파일은 다음과 같다.

- `langchain-deepagents.py`: Agent 런타임, 시스템 프롬프트, 스크린샷 정적 서버 구성
- `workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py`: 월드컵 결과 캡처 스크립트
- `workspace_seed/skills/worldcup-result-screenshot/SKILL.md`: 월드컵 캡처 스킬 지침
- `workspace_seed/skills/meta-harness/metaharness.py`: Agent 실행 결과를 격리 환경에서 평가하는 meta-harness
- `tests/test_worldcup_runtime_config.py`, `tests/test_meta_harness_runtime.py`: 회귀 방지 테스트

## 3. 주요 문제와 해결 과정

### 3.1 캡처 이미지를 저장만 하고 화면에 표시하지 못한 문제

초기 테스트에서는 Agent가 스크린샷 파일을 생성했지만, 사용자 응답에는 파일 경로만 표시되었다. 사용자의 요구는 "저장도 하고 화면에도 보여주는 것"이었으므로, 단순 경로 안내만으로는 목표를 충족하지 못했다.

처음에는 Markdown 이미지 링크에 `workspace/screenshots/worldcup-YYYYMMDD.png` 같은 상대 경로를 넣도록 지시했다. 그러나 LangGraph Studio 같은 브라우저 기반 UI에서는 이 경로가 실제로 접근 가능한 URL이 아니기 때문에 이미지가 깨진 아이콘으로 표시되었다.

이를 해결하기 위해 두 단계를 거쳤다.

첫 번째 해결은 이미지를 `data:image/png;base64,...` 형태로 응답에 직접 포함하는 방식이었다. 이 방식은 경로 문제를 피할 수 있어 이미지 표시에는 성공했지만, base64 문자열이 매우 길어져 응답 생성과 화면 렌더링이 느려지는 새로운 문제가 생겼다.

최종 해결은 `workspace/screenshots/` 폴더를 로컬 HTTP 정적 서버로 제공하는 방식이다. `langchain-deepagents.py`에서 Agent 실행 시 `http://127.0.0.1:8765/screenshots/...` 형태의 URL을 제공하도록 했고, 캡처 스크립트는 `SCREENSHOT_BASE_URL`이 설정되어 있으면 base64 대신 짧은 HTTP 이미지 URL을 출력하도록 개선했다.

결과적으로 응답은 다음처럼 짧아졌다.

```text
IMAGE_MARKDOWN: ![worldcup-result](http://127.0.0.1:8765/screenshots/worldcup-20260707.png)
```

이 방식으로 이미지 표시 문제와 응답 지연 문제를 동시에 해결했다.

### 3.2 Python, Playwright, uv 실행 환경 문제

Windows 환경에서 `uv`, `python`, `playwright` 명령이 실행되지 않거나, Agent의 셸 환경에서 Python 런타임을 찾지 못하는 문제가 있었다. 특히 사용자가 `uv run python -m playwright install chromium`을 실행했을 때 `No module named playwright` 오류가 발생했다.

원인은 명령 실행 위치와 Python 환경이 일치하지 않은 데 있었다. 프로젝트 루트가 아닌 위치에서 `uv run`을 실행하거나, Agent 셸의 `PATH`에 현재 Python 런타임과 Scripts 디렉터리가 포함되지 않아 필요한 모듈과 콘솔 명령을 찾지 못했다.

이를 해결하기 위해 `langchain-deepagents.py`에 런타임 PATH 보정 로직을 추가했다. Agent를 실행한 Python의 디렉터리와 `Scripts` 디렉터리를 `PATH` 앞쪽에 자동으로 추가하고, `PYTHONUTF8=1`도 설정했다.

또한 시스템 프롬프트에서 월드컵 캡처 스크립트 실행 명령을 다음처럼 명확히 했다.

```bash
python skills/worldcup-result-screenshot/collect_worldcup_result.py --date YYYY-MM-DD
```

이전의 `python3 workspace/...` 경로는 Windows 및 Agent workspace 기준에서 맞지 않을 수 있었기 때문에 제거했다.

결과적으로 Agent가 자신의 workspace 안에서 안정적으로 Python 스크립트를 실행할 수 있게 되었다.

### 3.3 Playwright 브라우저 실행 실패 문제

Playwright Chromium 설치 후에도 브라우저 실행 단계에서 다음과 같은 문제가 발생했다.

```text
BrowserType.launch: spawn EPERM
```

로그에는 `chrome-headless-shell.exe` 실행 명령이 보였고, 실제 원인은 Windows 실행 권한 또는 보안 정책 때문에 Playwright의 기본 headless shell 실행 파일이 차단되는 것이었다.

처음에는 브라우저 설치 문제로 보였지만, 실행 파일을 직접 확인한 결과 일반 Chromium `chrome.exe`는 실행 가능했다. 따라서 스크립트에 fallback 로직을 추가했다.

개선된 실행 순서는 다음과 같다.

1. Playwright 기본 `chromium.launch(headless=True)` 실행 시도
2. 실패하면 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 환경변수 확인
3. 없으면 `%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win64\chrome.exe` 탐색
4. 일반 Chromium `chrome.exe`로 재시도

이 로직을 `launch_chromium()` 함수로 분리했고, 실패 내역을 모두 모아 진단 가능한 오류 메시지를 출력하도록 했다.

결과적으로 `chrome-headless-shell.exe`가 막히는 환경에서도 일반 Chromium으로 캡처를 수행할 수 있게 되었다.

### 3.4 경기가 없는 날짜에 잘못된 날짜가 캡처되는 문제

네이버 스포츠 월드컵 일정 페이지는 요청한 날짜에 경기가 없으면 `date` 파라미터를 자동으로 다음 경기일로 변경해 페이지를 보여준다. 예를 들어 사용자가 `2026-07-09`를 요청하면 실제로는 `2026-07-10` 일정 화면이 표시될 수 있다.

초기 Agent는 이 동작을 감지하지 못하고 9일 요청에 대해 10일 화면을 캡처했다. 이는 사용자의 의도와 다른 결과를 제공하는 정확성 문제였다.

해결 방식은 요청 날짜와 실제 로드된 페이지 URL의 `date` 파라미터를 비교하는 것이다.

```python
def loaded_schedule_date(page_url: str) -> str | None:
    values = parse_qs(urlparse(page_url).query).get("date")
    return values[0] if values else None
```

캡처 직전에 `page.url`을 확인하고, 요청 날짜와 실제 로드 날짜가 다르면 `NoMatchesForDate` 예외를 발생시킨다. 이 경우 이미지를 캡처하지 않고 다음 정보를 출력한다.

```text
NO_MATCHES: 경기가 없는 날짜 입니다. 다른 날짜를 조회해 주세요
LOADED_DATE: 2026-07-10
SCHEDULE_URL: https://m.sports.naver.com/fifaworldcup2026/schedule
```

Agent 시스템 프롬프트도 `NO_MATCHES:`가 출력되면 이미지를 표시하지 않고 안내 문구와 전체 일정 링크를 답하도록 보강했다.

결과적으로 경기가 없는 날짜에 잘못된 다음 경기일 이미지를 보여주는 문제가 해결되었다.

### 3.5 OpenRouter Key limit 및 LangSmith tracing 확인 문제

LangSmith tracing을 적용하는 과정에서 tracing 화면에 기록이 보이지 않거나, Agent가 진행 중 상태로 머무는 문제가 있었다. 이후 OpenRouter에서 다음 오류가 확인되었다.

```text
PermissionDeniedError: Key limit exceeded (total limit)
```

이는 LangSmith 문제가 아니라 모델 호출에 사용하는 OpenRouter API key 한도 문제였다. 모델 호출이 실패하면 LangSmith trace가 기대한 방식으로 남지 않거나 최종 답변이 생성되지 않을 수 있다.

해결 방향은 문제의 층위를 분리하는 것이었다.

- LangSmith 설정은 `.env`와 서버 로그에서 확인
- `LANGSMITH_TRACING=false`로 비교 실행해 tracing 유무와 Agent 실행 문제를 분리
- OpenRouter 403 오류는 API key 한도 또는 크레딧 문제로 판단

이 과정을 통해 tracing 자체의 문제와 모델 provider quota 문제를 분리해서 볼 수 있게 되었다.

### 3.6 meta-harness 적용 중 Windows 호환성 문제

Agent 고도화 후 meta-harness 스킬을 적용해 self-evaluation 흐름을 실험했다. `doctor`는 정상 통과했지만, baseline 실행과 기록 조회 과정에서 Windows 인코딩 문제가 발생했다.

대표 증상은 다음과 같다.

- `show transcript` 실행 시 `UnicodeEncodeError`
- 자식 프로세스 로그 수집 중 `UnicodeDecodeError`
- Windows 기본 콘솔 인코딩 `cp949`와 UTF-8 로그가 충돌

이를 해결하기 위해 `metaharness.py`에 다음 개선을 적용했다.

- `sys.stdout`, `sys.stderr`를 UTF-8로 재설정
- 자식 프로세스 환경에 `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` 강제
- `subprocess.run()`에서 `encoding="utf-8"`, `errors="replace"` 지정

이후 짧은 smoke 질의로 meta-harness 실행을 검증했다.

```text
query: 안녕. 한 문장으로만 답해.
duration: 26.8s
messages: 2
tool_calls: 0
error: null
```

또한 `show --what answer`, `show --what transcript`가 정상 동작하는 것을 확인했다.

## 4. 검증 및 테스트

고도화 과정에서 단순 수동 확인에 그치지 않고, 회귀 방지 테스트를 추가했다.

### 4.1 월드컵 캡처 관련 테스트

`tests/test_worldcup_runtime_config.py`에 다음 항목을 검증했다.

- Agent 프롬프트가 Windows 기준 실행 명령을 사용한다.
- 상대 경로 이미지 링크를 만들지 않는다.
- HTTP 이미지 URL을 우선 사용하고, 필요 시 base64 fallback을 사용한다.
- Playwright 기본 headless shell 실패 시 일반 Chromium 실행 파일로 재시도한다.
- 네이버가 요청 날짜를 다른 날짜로 바꾸면 경기 없음으로 처리한다.

### 4.2 meta-harness 관련 테스트

`tests/test_meta_harness_runtime.py`에 다음 항목을 검증했다.

- meta-harness 자식 프로세스 실행 시 UTF-8 출력 디코딩을 사용한다.
- `WORKSPACE_DIR`은 제거하고, `PYTHONUTF8`, `PYTHONIOENCODING`을 강제한다.

### 4.3 최종 검증 결과

최종 커밋 전 다음 검증을 수행했다.

```bash
python -m unittest tests.test_meta_harness_runtime tests.test_worldcup_runtime_config
python -m py_compile langchain-deepagents.py workspace_seed/skills/meta-harness/metaharness.py workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py
```

결과는 총 10개 테스트 통과 및 문법 검사 통과였다.

## 5. 고도화 결과

고도화 후 Agent는 다음 수준으로 개선되었다.

- 사용자가 날짜만 입력해도 월드컵 경기 결과 조회 의도를 자동 인식한다.
- Windows 환경에서 Python 및 Playwright 실행 안정성이 높아졌다.
- Playwright headless shell 실행 실패 시 일반 Chromium으로 자동 fallback한다.
- 캡처 이미지를 저장하고, 브라우저 UI에서 바로 볼 수 있는 HTTP 이미지 URL을 응답한다.
- 경기가 없는 날짜는 잘못된 다음 경기일 캡처를 하지 않고 안내 문구를 제공한다.
- 전체 일정 링크를 함께 제공해 사용자가 다른 날짜를 선택할 수 있게 했다.
- meta-harness로 Agent 실행 결과를 격리 환경에서 기록하고 확인할 수 있는 기반을 마련했다.
- 핵심 동작에 대한 자동 테스트가 추가되어 회귀 가능성이 줄었다.

## 6. 향후 개선 과제

현재 Agent는 기능적으로 안정화되었지만, 다음 개선 여지가 있다.

1. 경기 없음 안내 화면 개선
   - 단순 문구 외에 전체 일정 페이지 캡처 또는 주요 일정 목록을 함께 제공할 수 있다.

2. meta-harness 평가 시나리오 확장
   - 현재는 smoke 테스트까지 확인했다. 앞으로는 "경기 있는 날짜", "경기 없는 날짜", "월/일 입력", "잘못된 날짜 형식" 같은 대표 질의를 정해 baseline과 variant를 비교할 수 있다.

3. 모델 호출 비용 및 속도 최적화
   - 월드컵 조회처럼 정형화된 작업은 LLM 추론 단계를 줄이고, 스크립트 실행과 결과 포맷팅을 더 결정적으로 만들 수 있다.

4. 이미지 서버 운영 방식 정리
   - 현재는 로컬 HTTP 서버를 사용한다. 배포 환경에서는 파일 제공 URL, 인증, 만료 정책을 명확히 정의할 필요가 있다.

5. LangSmith 관측성 고도화
   - 정상 실행, OpenRouter quota 오류, Playwright 실행 오류, 경기 없음 케이스를 trace에서 구분할 수 있도록 태그와 메타데이터를 보강할 수 있다.

## 7. 결론

이번 고도화의 핵심은 단순히 "이미지를 캡처한다"에서 끝나지 않고, 실제 사용 환경에서 Agent가 안정적으로 동작하도록 문제를 하나씩 분리해 해결한 데 있다.

초기에는 실행 환경 문제, 브라우저 실행 실패, 이미지 표시 실패, 긴 base64 응답, 네이버 날짜 자동 보정, tracing 혼선, meta-harness Windows 호환성 문제가 연달아 발생했다. 각 문제는 원인을 분리한 뒤 코드와 프롬프트, 실행 환경, 테스트를 함께 보완하는 방식으로 해결했다.

그 결과 현재 Agent는 월드컵 경기 결과 캡처라는 핵심 업무를 더 정확하고 빠르게 수행하며, 실패 상황에서도 사용자에게 올바른 안내를 제공할 수 있는 형태로 개선되었다.
