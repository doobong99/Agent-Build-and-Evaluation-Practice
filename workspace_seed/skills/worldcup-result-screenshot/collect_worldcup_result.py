#!/usr/bin/env python3
"""월드컵 경기 결과 스크린샷 수집용 스크립트.

사용 예:
  python3 workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py --date "7일"
  python3 workspace_seed/skills/worldcup-result-screenshot/collect_worldcup_result.py --date "6월 30일" --output workspace/screenshots/worldcup-20260630.png --dry-run
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


def resolve_date(raw: str, today: datetime | None = None) -> datetime:
    """사용자 입력을 규칙에 맞춰 날짜로 해석한다.

    - "7일" 또는 "7" -> 현재 년/월 기준의 해당 일
    - "6월 30일" 또는 "6/30" -> 현재 년 기준의 해당 월/일
    - "2026-06-30" -> 명시적 날짜
    """
    if today is None:
        today = datetime.now()
    text = raw.strip()

    if not text:
        raise ValueError("날짜가 비어 있습니다.")

    if re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", text):
        return datetime.strptime(text, "%Y-%m-%d")

    if re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", text):
        return datetime.strptime(text, "%Y-%m-%d")

    if re.fullmatch(r"\d{1,2}", text):
        return today.replace(day=int(text))

    if re.fullmatch(r"\d{1,2}일", text):
        return today.replace(day=int(text[:-1]))

    month_day_match = re.fullmatch(r"(\d{1,2})\s*(월|/|-)?\s*(\d{1,2})\s*(일)?", text)
    if month_day_match:
        month = int(month_day_match.group(1))
        day = int(month_day_match.group(3))
        return today.replace(month=month, day=day)

    raise ValueError(f"지원하지 않는 날짜 형식입니다: {raw}")


def build_query(resolved: datetime) -> str:
    return f"{resolved.year}년 {resolved.month}월 {resolved.day}일 월드컵 경기 결과"


def build_output_path(raw: str, output: str | None, resolved: datetime) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    default_dir = Path("workspace/screenshots")
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir / f"worldcup-{resolved.strftime('%Y%m%d')}.png"


def capture_screenshot(target_url: str, output_path: Path, dry_run: bool = False) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        output_path.write_text(f"dry-run: {target_url}\n", encoding="utf-8")
        return output_path

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright가 설치되지 않았습니다. `pip install playwright` 및 `playwright install chromium` 을 먼저 실행하세요."
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 900})
        page.goto(target_url, wait_until="networkidle")

        try:
            page.wait_for_selector('div[class*="PanelDate_group"]', timeout=15000)
            schedule_container = page.locator('div[class*="PanelDate_group"]').first
            schedule_container.screenshot(path=str(output_path))
        except Exception:
            page.screenshot(path=str(output_path), full_page=True)
        finally:
            browser.close()

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="월드컵 경기 결과 스크린샷을 저장합니다.")
    parser.add_argument("--date", required=True, help="예: 7일, 6월 30일, 2026-06-30")
    parser.add_argument("--output", help="저장할 이미지 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 캡처 대신 안내 파일을 생성합니다")
    args = parser.parse_args()

    resolved = resolve_date(args.date)
    page_url = f"https://m.sports.naver.com/fifaworldcup2026/schedule?date={resolved.strftime('%Y-%m-%d')}"
    query = build_query(resolved)
    output_path = build_output_path(args.date, args.output, resolved)

    try:
        saved_path = capture_screenshot(page_url, output_path, dry_run=args.dry_run)
    except Exception as exc:
        raise SystemExit(f"실패: {exc}") from exc

    print(f"날짜: {resolved.strftime('%Y-%m-%d')}")
    print(f"페이지 URL: {page_url}")
    print(f"검색어: {query}")
    print(f"저장 경로: {saved_path}")


if __name__ == "__main__":
    main()
