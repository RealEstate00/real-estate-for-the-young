#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RTMS 전월세 CSV 대량 다운로드 자동화 (5분 타임아웃, 가독성 파일명, 15행 제거 후 UTF-8)
- 사이트: https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=
- Housing types: A(아파트), B(연립/다세대), C(단독/다가구), D(오피스텔)
- Deal type: 전월세
- Date ranges (3 runs):
  1) 2023-01-01 ~ 2024-01-01
  2) 2024-01-01 ~ 2025-01-01
  3) 2025-01-01 ~ today
- Address: 지번주소 탭 + 서울특별시만 선택
- Download: CSV (명시적 playwright wait 사용)
- Postprocess: 앞 15행 제거 후 UTF-8(무 BOM)로 재저장
"""

import argparse
import datetime as dt
from pathlib import Path
from typing import Iterable, Tuple, Dict

from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PWTimeoutError
from charset_normalizer import from_bytes

URL = "https://rt.molit.go.kr/pt/xls/xls.do?mobileAt="

# Four housing tabs we will iterate (keys align with fnThingChange codes)
HOUSING_TABS: Dict[str, str] = {
    "A": "#xlsTab1",  # 아파트
    "B": "#xlsTab2",  # 연립/다세대
    "C": "#xlsTab3",  # 단독/다가구
    "D": "#xlsTab4",  # 오피스텔
}

# Human-friendly labels/slugs for filenames
HOUSING_META: Dict[str, Tuple[str, str]] = {
    "A": ("아파트", "apartment"),
    "B": ("연립다세대", "row_multi"),
    "C": ("단독다가구", "detached_multi"),
    "D": ("오피스텔", "officetel"),
}

# Three year-like ranges as requested
DATE_WINDOWS: Tuple[Tuple[str, str], ...] = (
    ("2023-01-01", "2024-01-01"),
    ("2024-01-01", "2025-01-01"),
    # third window: 2025-01-01 ~ today
)

DOWNLOAD_TIMEOUT_MS = 300_000  # 5 minutes

def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")

def click_lease_tab(page: Page) -> None:
    """Click '전월세' tab; robust selectors with JS fallback."""
    try:
        page.get_by_role("link", name="전월세").click(timeout=2000)
        return
    except PWTimeoutError:
        pass
    try:
        page.locator("a[href*=\"fnRtToLr('2')\"]").first.click(timeout=2000)
        return
    except PWTimeoutError:
        pass
    page.evaluate("() => window.fnRtToLr && window.fnRtToLr('2')")

def switch_housing_tab(page: Page, code: str) -> None:
    """Switch to housing type tab by code A/B/C/D."""
    sel = HOUSING_TABS.get(code)
    if sel:
        try:
            page.locator(sel).click(timeout=2000)
            return
        except PWTimeoutError:
            pass
    page.evaluate("(c) => window.fnThingChange && window.fnThingChange(c)", code)

def set_date_range(page: Page, start: str, end: str) -> None:
    """Set start/end date inputs."""
    page.fill("#srhFromDt", start)
    page.fill("#srhToDt", end)

def ensure_contract_all(page: Page) -> None:
    """Ensure 계약구분 == 전체."""
    for sel in ("#srhNewRonSecd", "select[name='srhNewRonSecd']", "select[title*='계약구분']"):
        if page.locator(sel).count() > 0:
            try:
                page.select_option(sel, value="")
                return
            except Exception:
                continue

def select_jibeon_address_tab(page: Page) -> None:
    """Select '지번주소' tab."""
    try:
        page.get_by_role("tab", name="지번주소").click(timeout=1500)
        return
    except Exception:
        pass
    try:
        page.locator("button, a, li, span").filter(has_text="지번주소").first.click(timeout=1500)
        return
    except Exception:
        pass  # maybe already default

def select_seoul_only(page: Page) -> None:
    """Select '서울특별시' in top-level select; leave lower levels empty."""
    likely = [
        "select#srhSidoNm",
        "select[name='srhSidoNm']",
        "select#sido",
        "select[name='sido']",
        "select[title*='시도']",
        "div.addrSlt select",
        "div.sido select",
    ]
    for sel in likely:
        if page.locator(sel).count():
            try:
                page.select_option(sel, label="서울특별시")
                return
            except PWTimeoutError:
                return
            except Exception:
                continue
    # JS fallback
    try:
        page.evaluate(
            """
            () => {
              const sidos = Array.from(document.querySelectorAll('select'));
              for (const s of sidos) {
                const opt = Array.from(s.options || []).find(o => o.textContent.trim() === '서울특별시');
                if (opt) { s.value = opt.value; s.dispatchEvent(new Event('change', { bubbles: true })); return true; }
              }
              return false;
            }
            """
        )
    except Exception:
        pass

def _strip_first_15_and_convert_utf8(csv_path: Path) -> None:
    """
    After download: remove first 15 lines, then re-save as UTF-8 (no BOM).
    Uses charset-normalizer to detect original encoding (CP949/EUC-KR typical).
    """
    try:
        raw = csv_path.read_bytes()
        guess = from_bytes(raw).best()
        enc = (guess.encoding if guess else None) or "utf-8"
        text = raw.decode(enc, errors="replace")
        lines = text.splitlines()
        if len(lines) <= 15:
            stripped = "\n".join(lines)  # too short, keep as-is content-wise
        else:
            stripped = "\n".join(lines[15:])
        csv_path.write_text(stripped, encoding="utf-8", newline="")
        # optional: print small log
        # print(f"[ENC] {csv_path.name}: {enc} -> UTF-8, -15 lines")
    except Exception as e:
        print(f"[ENC-WARN] {csv_path.name}: re-encode failed ({e}); kept original")

def trigger_csv_download(page: Page, context: BrowserContext, save_path: Path) -> Path:
    """
    Click 'CSV 다운' and save to path.
    Wait up to DOWNLOAD_TIMEOUT_MS for download event.
    """
    with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl_info:
        clicked = False
        # by role/name
        try:
            page.get_by_role("button", name="CSV 다운").click()
            clicked = True
        except Exception:
            pass
        if not clicked:
            # by text
            try:
                page.locator("button, a").filter(has_text="CSV 다운").first.click()
                clicked = True
            except Exception:
                pass
        if not clicked:
            # onclick signature
            page.locator("button[onclick='fnCSVDown()']").first.click()

    download = dl_info.value  # type: ignore
    download.save_as(str(save_path))
    # postprocess: strip first 15 lines, convert to UTF-8
    _strip_first_15_and_convert_utf8(save_path)
    return save_path

def iter_windows() -> Iterable[Tuple[str, str]]:
    for w in DATE_WINDOWS:
        yield w
    yield ("2025-01-01", _today_str())

def main(output_dir: str, headless: bool = True) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(15_000)  # 일반 조작 timeout은 유지 (다운로드는 5분)

        page.goto(URL, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except PWTimeoutError:
            pass

        # invariant filters
        click_lease_tab(page)
        select_jibeon_address_tab(page)
        select_seoul_only(page)
        ensure_contract_all(page)

        # iterate tabs × windows
        for code in HOUSING_TABS.keys():
            switch_housing_tab(page, code)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except PWTimeoutError:
                pass

            name_ko, slug_en = HOUSING_META[code]

            for start, end in iter_windows():
                set_date_range(page, start, end)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except PWTimeoutError:
                    pass

                # readable filename
                filename = f"rtms_{code}_{name_ko}_{slug_en}_lease_{start}_to_{end}_Seoul.csv"
                filename = filename.replace(" ", "_")
                save_path = out_dir / filename

                try:
                    saved = trigger_csv_download(page, context, save_path)
                    print(f"[OK] Saved: {saved}")
                except Exception as e:
                    print(f"[WARN] Download failed for {code} {start}~{end}: {e}")

        context.close()
        browser.close()

if __name__ == "__main__":
    # 기본 저장 경로를 프로젝트 내 backend/data/rtms로 설정
    default_output_dir = Path(__file__).parent.parent.parent.parent.parent / "backend" / "data" / "rtms"
    
    parser = argparse.ArgumentParser(description="RTMS 전월세 CSV 자동 다운로드")
    parser.add_argument("-o", "--output-dir", default=str(default_output_dir), help="Directory to save CSV files (default: backend/data/rtms)")
    parser.add_argument("--no-headless", action="store_true", help="Run browser in headed mode")
    args = parser.parse_args()
    main(output_dir=args.output_dir, headless=not args.no_headless)
