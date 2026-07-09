---
name: worldcup-result-screenshot
description: 사용자가 특정 날짜의 월드컵 경기 결과를 알고 싶어 하면, 네이버에서 해당 날짜를 찾고 화면캡처 이미지를 저장한다. 입력은 날짜 문자열이며 출력은 이미지 파일 경로다.
---

# 월드컵 경기 결과 스크린샷 수집

이 스킬은 사용자가 원하는 날짜의 월드컵 경기 결과를 네이버에서 확인하고, 그 화면을 캡처한 이미지 파일을 생성하는 작업을 담당한다.

## 목표
- 사용자의 날짜 입력을 해석한다.
- 네이버에서 해당 날짜의 경기 결과 페이지를 찾는다.
- 화면 캡처를 수행해 이미지 파일로 저장한다.
- 생성된 이미지 파일의 크기를 1MB 이하로 유지한다.

## 입력
- 날짜 문자열 예시:
  - "7일"
  - "7"
  - "6월 30일"
  - "2026-06-30"

## 날짜 해석 규칙
- 입력에 일만 있으면 현재 년월을 기준으로 해석한다.
  - 예: "7일" → 현재 연도의 같은 달의 7일
- 입력에 월과 일이 있으면 현재 년을 기준으로 해석한다.
  - 예: "6월 30일" → 현재 연도의 6월 30일
- 명확하지 않으면 최소한의 확인만 요청한다.

## 작업 절차
1. 사용자의 날짜 입력을 파싱한다.
2. Browser MCP로 네이버 페이지를 열고, 해당 날짜의 경기 결과를 찾는다.
3. 필요한 화면만 캡처한다.
4. Filesystem MCP로 이미지 파일을 저장한다.
5. 저장 경로와 결과 요약을 사용자에게 전달한다.

## 저장 규칙
- 저장 위치는 `workspace/screenshots/` 아래로 한다.
- 파일명은 `worldcup-YYYYMMDD.png` 형식으로 한다.
- 이미지 크기는 1MB 이하로 유지한다.

## 출력
- 생성된 이미지 파일 경로
- 짧은 요약 문구

## 실행 스크립트
- 실제 실행은 `collect_worldcup_result.py` 를 사용한다.
- 예시:

```bash
python3 workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py --date "7일"
python3 workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py --date "6월 30일"
python3 workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py --date "2026-06-30" --output workspace/screenshots/worldcup-20260630.png
```

## 주의사항
- 웹 페이지 로딩이 늦으면 충분히 기다린다.
- 여러 결과가 나올 경우 가장 적절한 경기 결과 화면을 선택한다.
- 실패 시 원인과 다음 시도 방향을 명확히 말한다.
- 실제 캡처 전에는 `--dry-run` 옵션으로 동작을 확인할 수 있다.
