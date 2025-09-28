#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Base crawler class and common utilities

from __future__ import annotations
import csv, json, re, hashlib
from pathlib import Path
import shutil
from backend.libs.utils.paths import (make_run_dir, HOUSING_DIR, today_ymd, sanitize_component)
from datetime import datetime, timezone, timedelta
from typing import Optional

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from playwright.sync_api import TimeoutError as PWTimeout

# ---------- Globals ----------
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")
ALLOWED_EXTS = {".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}

# Platform ID mapping
PLATFORM_ID_MAP = {
    "sohouse": 1, "cohouse": 2,
    "youth_home": 3, "youth_bbs": 3,
    "sh_ann": 4, "sh_plan_happy": 4, "ha_sh": 4, "ha_lh": 4,
    "lh_ann": 4, "seoul_portal_happy_intro": 4,
    "sh_happy_eligibility": 4, "sh_main_page": 4, "sh_search": 4, "sh_happy_intro": 4,
    "sohouse_intro": 1, "cohouse_intro": 2, "youth_intro": 3, "youth_finance": 3,
}

# Platform URLs
SO_BASE = "https://soco.seoul.go.kr"
SO_SOCIAL_LIST = f"{SO_BASE}/soHouse/pgm/home/sohome/list.do?menuNo=300006"
SO_COMM_LIST = f"{SO_BASE}/coHouse/pgm/home/cohome/list.do?menuNo=200043"

# -------------CSV header -------------
RAW_HEADER = [
    "notice_id", "platform", "platform_id", "house_name", "address",
    "unit_type", "building_type", "theme", "subway_station", "eligibility",
    "last_modified", "crawl_date", "list_url", "detail_url", "image_paths", "floorplan_paths", "html_path",
    "detail_text_path", "kv_json_path", "crawled_at", "unit_index"
]

# ---------- Utility Functions ----------
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def write_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def append_csv(path: Path, header: list, rows: list[dict]):
    init = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=header)
        if init:
            w.writeheader()
        for r in rows:
            w.writerow(r)

def clean_today(source: str, *, dry_run: bool = False) -> int:
    """Delete today's run directories for a given source under data/raw."""
    src = sanitize_component(source)
    date_str = today_ymd()
    base: Path = HOUSING_DIR / src
    pattern = f"{date_str}__*"

    removed = 0
    if not base.exists():
        print(f"[CLEAN] base not found: {base}")
        return removed

    for d in base.glob(pattern):
        if d.is_dir() and d.parent.resolve() == base.resolve():
            if dry_run:
                print(f"[CLEAN:DRY] would remove {d}")
            else:
                shutil.rmtree(d, ignore_errors=True)
                print(f"[CLEAN] removed {d}")
            removed += 1

    print(f"[CLEAN] {base}/{pattern} removed: {removed}{' (dry-run)' if dry_run else ''}")
    return removed

def run_dir(source: str, run_id: str | None = None, date_ymd: str | None = None) -> Path:
    """Return the canonical run directory under data/housing/<source>/<YYYY-MM-DD>__<run_id>/."""
    return make_run_dir(source, run_id=run_id, date_ymd=date_ymd)

def ensure_dirs(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    for d in ("html", "images", "tables", "texts", "kv", "attachments"):
        (base / d).mkdir(parents=True, exist_ok=True)

def platform_fixed_id(platform_code: str) -> int | None:
    return PLATFORM_ID_MAP.get(platform_code)

def sanity_check_address(rec):
    addr = (rec.get("address") or "").strip()
    if addr and ("입주대상" in addr or "대상" in addr):
        print(f"[WARN] address suspicious (eligibility?): record_id={rec['record_id']} addr={addr[:40]}")

# ---------- Logging ----------
class Progress:
    def update(self, msg: str):
        print(msg, flush=True)

# ---------- Web Scraping Helpers ----------
def get_page_html_stable(page, progress: Progress | None = None, label: str = "content", attempts: int = 3) -> str:
    """Return stable page HTML even during navigation/updates."""
    for i in range(attempts):
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except PWTimeout:
            pass
        try:
            return page.content()
        except Exception:
            try:
                return page.evaluate("document.documentElement.outerHTML")
            except Exception as e2:
                if progress:
                    progress.update(f"[RETRY content] {label} try={i+1} err={e2}")
                page.wait_for_timeout(350)
    return page.evaluate("document.documentElement.outerHTML")

def extract_core_content_html(page) -> str:
    """Extract only core content HTML, removing navigation, ads, and footer."""
    try:
        # Try to find main content containers
        content_selectors = [
            "#printArea",  # Main print area
            ".subpage_content",  # Subpage content
            ".detail-box",  # Detail box
            ".viewTable",  # View table
            ".detail-info",  # Detail info
            "main",  # HTML5 main element
            "#content",  # Content area
            ".content",  # Content class
        ]
        
        for selector in content_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    # Get the HTML content of the found element
                    html = element.inner_html()
                    if html and len(html.strip()) > 100:  # Ensure we have substantial content
                        return f"<div class='extracted-content'>{html}</div>"
            except Exception:
                continue
        
        # Fallback: try to extract content between header and footer
        try:
            # Remove common unwanted elements
            page.evaluate("""
                // Remove navigation, ads, footer elements
                const unwantedSelectors = [
                    'header', '.header', '#header',
                    'nav', '.nav', '.navigation', '.mainNav', '#top_nav',
                    'footer', '.footer', '#footer',
                    '.ad', '.ads', '.advertisement', '.banner',
                    '.sidebar', '.side-menu', '.gnb', '.mobileNav',
                    '.location', '.breadcrumb', '.quick',
                    'script[src*="ad"]', 'script[src*="analytics"]', 'script[src*="gtag"]',
                    '.sitemap', '.accessibilityWrap', '#seoul-common-gnb'
                ];
                
                unwantedSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => el.remove());
                });
                
                // Remove script tags (except essential ones)
                const scripts = document.querySelectorAll('script');
                scripts.forEach(script => {
                    const src = script.src || '';
                    if (src.includes('ad') || src.includes('analytics') || src.includes('gtag') || 
                        src.includes('weblog') || src.includes('dighty') || src.includes('acecounter')) {
                        script.remove();
                    }
                });
            """)
            
            # Get the cleaned content
            return page.content()
            
        except Exception:
            # Final fallback: return full content
            return page.content()
            
    except Exception:
        return page.content()

def robust_goto(page, url: str, progress: Progress | None = None, label: str = ""):
    if progress:
        progress.update(f"[NAV] {label} {url}")
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
    except PWTimeout:
        if progress:
            progress.update(f"[TIMEOUT domcontentloaded] {url}, retry with load")
        page.goto(url, timeout=60000, wait_until="load")

def safe_wait_any(page, selectors: list[str], timeout=15000) -> str:
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout)
            return sel
        except PWTimeout:
            continue
    return ""

def open_detail(page, base_for_referer: str, descriptor: dict, progress: Progress):
    if descriptor.get("kind") == "js_function":
        name = descriptor["name"]; args = descriptor.get("args", [])
        progress.update(f"[DETAIL JS] {name}({','.join(args)})")
        with page.expect_navigation(wait_until="domcontentloaded", timeout=45000):
            page.evaluate(f"{name}({','.join(args)})")
        try:
            page.wait_for_function("document.readyState === 'complete'", timeout=10000)
        except Exception:
            pass
        page.wait_for_load_state("networkidle", timeout=8000)
        try:
            page.wait_for_selector("table, .detail-info, .info-box, [class*='address'], [class*='addr'], div.detail-box", timeout=8000)
        except Exception:
            pass
    elif descriptor.get("kind") == "get":
        url = descriptor["url"]
        alt_urls = descriptor.get("alt_urls", [])
        
        # 메인 URL 시도
        try:
            robust_goto(page, url, progress, label="DETAIL")
            # 페이지가 제대로 로드되었는지 확인
            page.wait_for_load_state("networkidle", timeout=8000)
            
            # 에러 페이지인지 확인
            if "정보가 없습니다" in page.content() or "에러안내" in page.content():
                progress.update(f"[WARN] Main URL failed, trying alternatives...")
                # 대안 URL들 시도
                for i, alt_url in enumerate(alt_urls):
                    try:
                        progress.update(f"[ALT] Trying alternative URL {i+1}: {alt_url}")
                        robust_goto(page, alt_url, progress, label="DETAIL_ALT")
                        page.wait_for_load_state("networkidle", timeout=8000)
                        
                        # 성공적인 페이지인지 확인
                        if "정보가 없습니다" not in page.content() and "에러안내" not in page.content():
                            progress.update(f"[SUCCESS] Alternative URL {i+1} worked!")
                            break
                    except Exception as e:
                        progress.update(f"[ALT] Alternative URL {i+1} failed: {e}")
                        continue
        except Exception as e:
            progress.update(f"[ERROR] Main URL failed: {e}")
            # 대안 URL들 시도
            for i, alt_url in enumerate(alt_urls):
                try:
                    progress.update(f"[ALT] Trying alternative URL {i+1}: {alt_url}")
                    robust_goto(page, alt_url, progress, label="DETAIL_ALT")
                    page.wait_for_load_state("networkidle", timeout=8000)
                    
                    # 성공적인 페이지인지 확인
                    if "정보가 없습니다" not in page.content() and "에러안내" not in page.content():
                        progress.update(f"[SUCCESS] Alternative URL {i+1} worked!")
                        break
                except Exception as e:
                    progress.update(f"[ALT] Alternative URL {i+1} failed: {e}")
                    continue
    else:
        raise ValueError("Unknown detail descriptor")

# ---------- File Download Helpers ----------
def _ext_of_url(u: str) -> str:
    try:
        path = urlparse(u).path
        name = path.rsplit("/", 1)[-1]
        if "." in name:
            return "." + name.split(".")[-1].lower()
    except Exception:
        pass
    return ""

def download_attachments_from_html(html: str, base_url: str, ctx, dst_dir: Path) -> list[str]:
    """Parse <a href> from html and download allowed file types."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[str] = []
    seen: set[str] = set()

    soup = BeautifulSoup(html, "html.parser")
    # '첨부/다운로드' 성격의 링크만 수집
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        lower = href.lower()
        if not any(k in lower for k in ("download", "attach", "file", ".hwp", ".pdf", ".doc", ".xls", ".ppt")):
            continue

        abs_url = urljoin(base_url, href)
        if abs_url in seen:
            continue
        seen.add(abs_url)

        ext = _ext_of_url(abs_url)
        if ext and ext not in ALLOWED_EXTS:
            continue

        fname = abs_url.split("/")[-1].split("?")[0] or f"{sha256(abs_url)[:16]}{ext or '.bin'}"
        out = dst_dir / fname
        try:
            if out.exists() and out.stat().st_size > 0:
                out_paths.append(str(out))
                continue
        except Exception:
            pass

        try:
            resp = ctx.request.get(abs_url)
            if not resp.ok:
                continue
            write_bytes(out, resp.body())
            out_paths.append(str(out))
        except Exception:
            continue

    return out_paths

def download_images_from(page, selector: str, base_url: str, dst_dir: Path, filter_floor_plan: bool = False, house_name: str = "", index: int = 0) -> list[str]:
    """Download images/links matched by selector; skip if file already exists."""
    els = page.locator(selector)
    saved: list[str] = []
    seen: set[str] = set()
    dst_dir.mkdir(parents=True, exist_ok=True)
    n = els.count()

    for i in range(n):
        src = (
            els.nth(i).get_attribute("src")
            or els.nth(i).get_attribute("data-src")
            or els.nth(i).get_attribute("href")
            or ""
        )
        if not src or "javascript:" in src:
            continue

        alt_text = (els.nth(i).get_attribute("alt") or "").lower()

        # 평면도 필터
        if filter_floor_plan:
            if ("평면도" not in alt_text) and ("floor" not in alt_text) and ("plan" not in alt_text):
                continue
        else:
            # 집 이미지 위주
            if "fileDown.do" not in src:
                continue
            if any(k in alt_text for k in ("평면도", "floor", "plan")):
                continue

        abs_url = urljoin(base_url, src)
        if abs_url in seen:
            continue
        seen.add(abs_url)

        # 파일명
        hn = (house_name or f"house_{index:04d}").replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(" ", "_")[:20]
        ftype = "floor_plan" if filter_floor_plan else "house_image"
        url_name = f"detail_{index:04d}_{hn}_{ftype}_{sha256(abs_url)[:8]}.jpg"
        out = dst_dir / url_name

        try:
            if out.exists() and out.stat().st_size > 0:
                saved.append(str(out))
                continue
        except Exception:
            pass

        try:
            resp = page.context.request.get(abs_url)
            if not resp.ok:
                continue

            if out.suffix.lower() in ("", ".bin"):
                ct = (resp.headers or {}).get("content-type", "").split(";")[0].strip()
                ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp", "application/pdf": ".pdf"}
                ext = ext_map.get(ct, out.suffix or ".bin")
                if ext != out.suffix:
                    out = out.with_suffix(ext)

            write_bytes(out, resp.body())
            saved.append(str(out))
        except Exception:
            continue

    return saved

# ---------- Data Processing Helpers ----------
def make_relative_path(absolute_path: str, base_dir: str) -> str:
    """상대경로 저장"""
    if not absolute_path:
        return ""
    abs_path = Path(absolute_path)
    base_path = Path(base_dir)
    try:
        return str(abs_path.relative_to(base_path))
    except ValueError:
        return absolute_path

def generate_crawler_id(platform: str, platform_key: str, object_type: str = "notice", object_index: int = 0) -> str:
    """
    단순화된 크롤러 ID 생성
    형식: {platform}_{object_type}_{hash}_{index}
    """
    from hashlib import sha256
    
    # 안정적인 크롤러 ID 생성
    id_source = f"{platform}|{platform_key}|{object_type}"
    hash_part = sha256(id_source.encode('utf-8')).hexdigest()[:8]
    
    base_id = f"{platform}_{object_type}_{hash_part}"
    
    # object_index가 0보다 크면 추가
    if object_index > 0:
        return f"{base_id}_{object_index}"
    
    return base_id

def generate_stable_notice_id(platform: str, platform_key: str, list_url: str, detail_url: str, house_name: str, unit_index: int = 0) -> str:
    """
    안정적인 notice_id 생성 (공고 레벨)
    platform + platform_key + URLs + house_name 기반 (unit_index 무시)
    """
    from hashlib import sha256
    from urllib.parse import urlparse
    
    # URL에서 안정적인 부분만 추출
    stable_list_url = ""
    if list_url:
        parsed = urlparse(list_url)
        stable_list_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    stable_detail_url = ""
    if detail_url:
        parsed = urlparse(detail_url)
        # 쿼리 파라미터 제거하고 안정적인 부분만 사용
        stable_detail_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    # ID 생성용 문자열 구성 (unit_index 제외 - 공고 레벨 ID)
    id_components = [
        platform,
        platform_key,
        stable_list_url,
        stable_detail_url,
        house_name or ""
    ]
    
    id_string = "|".join([comp for comp in id_components if comp])
    hash_part = sha256(id_string.encode('utf-8')).hexdigest()[:12]
    
    return f"{platform}_notice_{hash_part}"

def make_record(platform: str, platform_id: str, list_url: str, detail_url: str, house_name: str, address: str,
                html_path: str, image_paths: list[str], floorplan_paths: list[str] = None,
                detail_text_path: str = "", kv_json_path: str = "", 
                unit_type: str = "", building_type: str = "", theme: str = "", subway_station: str = "", eligibility: str = "", last_modified: str = "",
                base_dir: str = "", unit_index: int = 0) -> dict:
    # 안정적인 record_id 생성 (플랫폼별 구분)
    notice_id = generate_stable_notice_id(platform, platform_id, list_url, detail_url, house_name, unit_index)

    # 상대경로 변환
    if base_dir:
        html_path = make_relative_path(html_path, base_dir)
        detail_text_path = make_relative_path(detail_text_path, base_dir)
        kv_json_path = make_relative_path(kv_json_path, base_dir)
        image_paths = [make_relative_path(p, base_dir) for p in image_paths]
        floorplan_paths = [make_relative_path(p, base_dir) for p in floorplan_paths]


    return {
        "notice_id": notice_id,  # 공고별 고유 ID (FK용)
        "platform": platform,
        "platform_id": platform_id,
        "house_name": house_name,
        "address": address,
        "unit_type": unit_type,
        "building_type": building_type,
        "theme": theme,
        "subway_station": subway_station,
        "eligibility": eligibility,
        "last_modified": last_modified,
        "crawl_date": TODAY,
        "list_url": list_url,
        "detail_url": detail_url,
        "image_paths": ";".join(image_paths),
        "floorplan_paths": ";".join(floorplan_paths),
        "html_path": html_path,
        "detail_text_path": detail_text_path,
        "kv_json_path": kv_json_path,
        "crawled_at": datetime.now(KST).isoformat(),
        "unit_index": unit_index,  # units 인덱스 추가
    }

def generate_space_id(address: str, floor: str, room_number: str, building_name: str = "") -> str:
    """
    물리적 공간 ID 생성 (주소+층+호수+건물명 기반)
    크롤링할 때마다 동일한 값이 나와야 함
    """
    import hashlib
    
    # 주소 정규화 (도로명주소 우선, 지번주소는 괄호 제거)
    normalized_address = address.strip()
    if "(" in normalized_address and ")" in normalized_address:
        # 지번주소가 괄호 안에 있는 경우 제거
        normalized_address = normalized_address.split("(")[0].strip()
    
    # 층과 호수 정규화
    normalized_floor = str(floor).strip() if floor else ""
    normalized_room = str(room_number).strip() if room_number else ""
    normalized_building = str(building_name).strip() if building_name else ""
    
    # ID 생성용 문자열 조합
    id_components = [
        normalized_address,
        normalized_floor,
        normalized_room,
        normalized_building
    ]
    
    # 빈 값 제거하고 조합
    id_string = "|".join([comp for comp in id_components if comp])
    
    # SHA256 해시로 안정적인 ID 생성
    hash_part = hashlib.sha256(id_string.encode('utf-8')).hexdigest()[:12]
    return f"space_{hash_part}"

def generate_notice_id(platform: str, platform_id: str, house_name: str, address: str) -> str:
    """
    공고별 notice_id 생성 (원 공고 detail000 연결용)
    단순화된 크롤러 ID 사용
    """
    # 단순화된 크롤러 ID 사용 (notice 타입, unit_index=0)
    return generate_crawler_id(platform, platform_id, "notice", 0)

def dump_improved_occupancy_csv(page, container_selector: str, out_csv_path: Path, source_notice_id: str | None = None, 
                                unit_type: str = "", building_type: str = "", target_occupancy: str = "", 
                                theme: str = "", subway_station: str = "", house_name: str = "", address: str = "", 
                                platform: str = None) -> bool:
    """개선된 컬럼 구조로 CSV 생성 (입주타입 제거, 새로운 컬럼 추가)"""
    try:
        container = page.locator(container_selector)
        if not container.count():
            return False

        tbl = container.locator("table").first
        if not tbl.count():
            return False

        rows = []
        body_trs = tbl.locator("tbody tr")
        tr_list = []
        if body_trs.count():
            for i in range(body_trs.count()):
                tr_list.append(body_trs.nth(i))
        else:
            all_trs = tbl.locator("tr")
            for i in range(all_trs.count()):
                tr_list.append(all_trs.nth(i))

        for tr in tr_list:
            cells = tr.locator("td")
            if cells.count() == 0:
                continue

            row_data = []
            for i in range(cells.count()):
                cell_text = cells.nth(i).inner_text().strip()

                # 마지막 컬럼: 입주가능 (이미지/텍스트를 1/0으로 매핑)
                if i == cells.count() - 1:
                    imgs = cells.nth(i).locator("img")
                    if imgs.count():
                        alt = (imgs.first.get_attribute("alt") or "").strip()
                        if "불가능" in alt or "마감" in alt:
                            cell_text = "0"
                        elif "가능" in alt:
                            cell_text = "1"
                        else:
                            cell_text = "0"
                    else:
                        if "가능" in cell_text:
                            cell_text = "1"
                        elif any(k in cell_text for k in ("불가능", "마감")):
                            cell_text = "0"
                        else:
                            cell_text = "0"

                cell_text = "" if (not cell_text or cell_text.isspace()) else cell_text
                row_data.append(cell_text)

            if row_data and len(row_data) >= 3 and any(c.strip() for c in row_data):
                rows.append(row_data)

        if not rows:
            return False

        # 헤더 - 단순화된 ID 구조 (notice_id 사용)
        headers = ["notice_id", "space_id", "방이름", "면적", "보증금", "월임대료", "관리비", "층", "호", "인원", "입주가능일", "입주가능"]

        # 공고별 크롤러 ID 생성 (unit_index=0으로 고정)
        notice_crawler_id = source_notice_id or ""

        out_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with out_csv_path.open("w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for idx, row in enumerate(rows):
                # 기존 구조 기준: [방이름, 입주타입, 면적, 보증금, 월임대료, 관리비, 층, 호, 인원, 입주가능일, 입주가능]
                if len(row) >= 11:
                    # 유닛별 크롤러 ID 생성
                    unit_crawler_id = generate_crawler_id(platform, source_notice_id or "", "unit", idx)
                    
                    # space_id 생성 (물리적 공간 식별자)
                    room_name = row[0] if len(row) > 0 else ""
                    floor = row[6] if len(row) > 6 else ""
                    room_number = row[7] if len(row) > 7 else ""
                    space_id = generate_space_id(address, floor, room_number, house_name)
                    
                    csv_row = [
                        notice_crawler_id,  # 공고 ID (FK용)
                        space_id,  # 물리적 공간 ID
                        row[0] if len(row) > 0 else "",  # 방이름
                        row[2] if len(row) > 2 else "",  # 면적
                        row[3] if len(row) > 3 else "",  # 보증금
                        row[4] if len(row) > 4 else "",  # 월임대료
                        row[5] if len(row) > 5 else "",  # 관리비
                        row[6] if len(row) > 6 else "",  # 층
                        row[7] if len(row) > 7 else "",  # 호
                        row[8] if len(row) > 8 else "",  # 인원
                        row[9] if len(row) > 9 else "",  # 입주가능일
                        row[10] if len(row) > 10 else "",  # 입주가능
                    ]
                    f.write(",".join(f'"{c}"' for c in csv_row) + "\n")
        return True
    except Exception as e:
        print(f"Error in dump_improved_occupancy_csv: {e}")
        return False

# ---------- Base Crawler Class ----------
class BaseCrawler:
    """Base class for all crawlers"""
    def __init__(self, progress: Progress, list_url: str, platform_code: str, base_url: str = None, save_to_db: bool = False):
        self.progress = progress
        self.list_url = list_url
        self.platform_code = platform_code
        self.base_url = base_url or list_url
        self.rows: list[dict] = []
        self.save_to_db = save_to_db
        self.db_service = None
        if save_to_db:
            try:
                from ..storage.database import DatabaseService
                self.db_service = DatabaseService()
                self.progress.update("[INFO] Database storage enabled")
            except Exception as e:
                self.progress.update(f"[WARN] Database storage disabled: {e}")
                self.save_to_db = False

    def crawl(self):
        raise NotImplementedError

    def save_results(self, output_dir: Path):
        append_csv(output_dir / "raw.csv", RAW_HEADER, self.rows)
        self.progress.update(f"[DONE] {len(self.rows)} rows saved")

    def save_progress(self, output_dir: Path) -> int:
        """현재 메모리 버퍼(self.rows)를 raw.csv에 플러시하고 버퍼를 비운다."""
        if not self.rows:
            return 0
        rows_to_write = self.rows
        self.rows = []  # 중복 방지
        append_csv(output_dir / "raw.csv", RAW_HEADER, rows_to_write)
        self.progress.update(f"[PROGRESS] +{len(rows_to_write)} rows → raw.csv")
        return len(rows_to_write)

    # ---- hooks (override in platform crawlers) ----
    def _extract_platform_specific_fields(self, page, detail_desc=None, detail_text_path=None, detail_text=None) -> dict:
        return {}

    def _filter_json_fields(self, kv_pairs: dict, platform_specific_fields: dict) -> dict:
        return kv_pairs

    def _download_images_platform_specific(self, page, output_dir: Path, house_name: str, index: int, unit_index: int = 0) -> tuple[list[str], list[str]]:
        image_paths = []
        floor_plan_paths = []
        try:
            els = page.locator("img")
            dst_dir = output_dir / "images"
            dst_dir.mkdir(parents=True, exist_ok=True)
            for i in range(min(els.count(), 10)):
                src = els.nth(i).get_attribute("src") or ""
                if not src or "javascript:" in src:
                    continue
                abs_url = urljoin(page.url, src)
                url_name = abs_url.split("/")[-1].split("?")[0] or f"image_{i}.jpg"
                if len(url_name) > 50:
                    url_name = f"image_{i}_{sha256(abs_url)[:8]}.jpg"
                # unit_index를 파일명에 포함
                if unit_index > 0:
                    name_parts = url_name.rsplit('.', 1)
                    if len(name_parts) == 2:
                        url_name = f"{name_parts[0]}_unit_{unit_index:02d}.{name_parts[1]}"
                    else:
                        url_name = f"{url_name}_unit_{unit_index:02d}"
                out = dst_dir / url_name
                if out.exists():
                    image_paths.append(str(out))
                    continue
                resp = page.context.request.get(abs_url)
                if resp.ok:
                    write_bytes(out, resp.body())
                    image_paths.append(str(out))
        except Exception:
            pass
        return image_paths, floor_plan_paths

    def _extract_csv_housing_fields(self, platform_specific_fields: dict) -> tuple[str, str, str, str]:
        return "", "", "", ""

    # ------------ text 저장 ------------
    def _clean_text_content(self, text: str) -> str:
        """텍스트에서 불필요한 네비게이션/푸터 제거 (공통)"""
        lines = text.split("\n")
        cleaned = []
        skip_keywords = [
            "바로가기 메뉴","본문 바로가기","주메뉴 바로가기","서울특별시","서울소식","주요메뉴","응답소","정보공개",
            "사회주택플랫폼","로그인","메뉴","HOME","공지사항","FAQ","이용안내","사이트맵","개인정보처리방침",
            "저작권정책","인쇄하기","공유하기","검색","페이지 상단","페이지 하단","맨 위로","맨 아래로","이전","다음",
            "목록","리스트","새창","팝업","닫기","확인","취소","저장","삭제","수정","등록","더보기","펼치기","접기",
            "전체보기","관련사이트","바로가기","자주묻는질문","도움말","설정","언어","로그아웃","회원가입","아이디","비밀번호"
        ]
        content_start = ["※","▷","소재지","주소","위치","입주","모집","공고","사회주택","공동체주택","청년주택","임대","보증금","월임대료","관리비","면적","세대","호실","동","입주자격","입주조건","선정기준","신청","접수","문의","연락처","전화","이메일"]
        started = False
        for line in lines:
            t = line.strip()
            if not t:
                continue
            if not started and any(k in t for k in content_start):
                started = True
            if not started:
                continue
            if any(k in t for k in skip_keywords):
                continue
            if len(t) < 3:
                continue
            if re.match(r"^[-=_*#\s]+$", t):
                continue
            if re.match(r"^(https?://|www\.)", t):
                continue
            if re.match(r"^\d+$", t):
                continue
            cleaned.append(t)
        return "\n".join(cleaned)

    # ---------- Unified detail processing ----------
    def process_detail_page(self, page, title: str, detail_desc: dict, output_dir: Path, index: int):
        """Process a single detail page - common logic for all crawlers"""
        try:
            from ..parsers.parsers import (
                parse_house_name, parse_address_strict, parse_building_type,
                parse_eligibility, _clean_title, extract_detail_text, extract_key_value_pairs,
                parse_subway_station, extract_units_from_notice,
            )

            # 상세 페이지 열기
            open_detail(page, self.list_url, detail_desc, self.progress)
            safe_wait_any(page, ["div.detail-box", ".bbsV_wrap", "article", ".viewTable", "#content"], timeout=10000)

            # HTML 저장
            html = get_page_html_stable(page, self.progress, "detail")

            # 기본 파싱
            house_name = parse_house_name(page, title) or _clean_title(title)
            address = parse_address_strict(page)
            building_type = parse_building_type(page)
            detail_text = extract_detail_text(page)
            
            # eligibility 추출 (텍스트 파일에서 우선)
            eligibility = ""
            if detail_text:
                # 텍스트에서 직접 eligibility 추출
                from ..parsers.parsers import parse_eligibility_from_text
                eligibility = parse_eligibility_from_text(detail_text)
            if not eligibility:
                # HTML에서도 시도
                eligibility = parse_eligibility(page)
            
            # 최종수정일 추출
            from ..parsers.parsers import parse_last_modified_date
            last_modified = parse_last_modified_date(page)
            
            # 편의시설 정보 추출
            from ..parsers.parsers import extract_facility_info
            facility_info = extract_facility_info(page)
            
            # 관련 주택 정보 추출
            from ..parsers.parsers import extract_related_housing_info
            related_housing_info = extract_related_housing_info(page)
            
            kv_pairs = extract_key_value_pairs(page)

            # 플랫폼 특화 필드
            ps_fields = self._extract_platform_specific_fields(page, detail_desc, None, detail_text) or {}
            
            # facility_info와 related_housing_info를 kv_pairs에 추가
            if facility_info:
                kv_pairs["facility_info"] = facility_info
            if related_housing_info:
                kv_pairs["related_housing_info"] = related_housing_info
            if detail_text:
                ps_fields["text_content"] = detail_text

            # 플랫폼이 제공한 eligibility가 있으면 우선
            if ps_fields.get("eligibility"):
                eligibility = ps_fields["eligibility"]

            json_fields = self._filter_json_fields(kv_pairs, ps_fields)

            # 주소 sanity
            if address:
                self.progress.update(f"[{self.platform_code}] Found address: {address[:50]}...")
                if not any(p in address for p in ("구","동","로","길","시","군","읍","면")):
                    self.progress.update(f"[{self.platform_code}] WARNING: address may be incomplete: {address[:50]}...")
                    address = ""
            else:
                self.progress.update(f"[{self.platform_code}] No address found")

            # 지하철역 보조 추출
            subway_station = parse_subway_station(page) or ps_fields.get("subway_station", "")
            if subway_station:
                ps_fields["subway_station"] = subway_station

            # CSV 분류 필드
            csv_unit_type, csv_building_type, csv_theme, csv_subway_station = self._extract_csv_housing_fields(ps_fields)

            # Units 추출 (occupancy 테이블 우선, JSON 데이터 활용)
            occupancy_table_path = str(output_dir / "tables" / f"detail_{index:04d}_occupancy.csv")
            units = extract_units_from_notice(page, detail_text, json_fields, occupancy_table_path)
            
            # 공고별 통합 파일 생성 (unit별 분할 제거)
            # 공고 레벨 파일들
            html_path = output_dir / "html" / f"detail_{index:04d}.html"
            detail_text_path = output_dir / "texts" / f"detail_{index:04d}.txt"
            kv_json_path = output_dir / "kv" / f"detail_{index:04d}.json"
            
            # HTML 저장
            write_text(html_path, html)
            
            # 텍스트 저장 (노이즈 제거)
            if detail_text:
                cleaned_text = self._clean_text_content(detail_text)
                write_text(detail_text_path, cleaned_text)

            # 이미지/평면도 (공고별로 다운로드)
            image_paths, floor_plan_paths = self._download_images_platform_specific(
                page, output_dir, house_name, index, 0  # unit_index=0으로 통일
            )

            # 첨부파일
            attach_paths = download_attachments_from_html(html, page.url, page.context, output_dir / "attachments")

            # 테이블 CSV (occupancy) - 공고별 통합 생성
            occ_csv = output_dir / "tables" / f"detail_{index:04d}_occupancy.csv"
            saved_occ = False
            # 안정적인 record_id 생성 (플랫폼별 구분)
            stable_notice_id = generate_stable_notice_id(
                self.platform_code, 
                str(PLATFORM_ID_MAP.get(self.platform_code, 1)),  # platform_id 사용
                self.list_url, 
                page.url, 
                house_name, 
                0
            )
            # occupancy 테이블 생성 (공고별 통합)
            for sel in ("div.tableWrap", "table", ".table", ".tbl_list"):
                if dump_improved_occupancy_csv(page, sel, occ_csv,
                                               source_notice_id=stable_notice_id,
                                               unit_type=csv_unit_type,
                                               building_type=csv_building_type,
                                               target_occupancy=ps_fields.get("target_occupancy", ""),
                                               theme=csv_theme,
                                               subway_station=csv_subway_station,
                                               house_name=house_name,
                                               address=address,
                                               platform=self.platform_code):
                    saved_occ = True
                    break

            # 공고별 통합 레코드 생성
            # 첫 번째 unit의 정보를 기본으로 사용 (공고 레벨 정보)
            primary_unit = units[0] if units else {}
            
            # 레코드 생성용 데이터 준비
            record_data = {
                "list_title": title,
                "house_name_source": "detail" if house_name and house_name != title else "list_fallback",
                "occupancy_table_csv": str(occ_csv) if saved_occ else "",
                "attachments_paths": attach_paths,
                "floor_plan_paths": floor_plan_paths if self.platform_code in ("sohouse","cohouse") else [],
                "eligibility_raw": eligibility,
                "building_type": primary_unit.get("building_type", building_type),
                "occupancy_type_detailed": {
                    "raw_value": primary_unit.get("building_type", building_type),
                    "is_detailed": "(" in (primary_unit.get("building_type", building_type) or ""),
                    "base_type": (primary_unit.get("building_type", building_type) or "").split("(")[0].strip() if primary_unit.get("building_type", building_type) and "(" in (primary_unit.get("building_type", building_type) or "") else primary_unit.get("building_type", building_type),
                    "sub_type": ((primary_unit.get("building_type", building_type) or "").split("(")[1].split(")")[0].strip()
                                 if primary_unit.get("building_type", building_type) and "(" in (primary_unit.get("building_type", building_type) or "") and ")" in (primary_unit.get("building_type", building_type) or "") else "")
                } if primary_unit.get("building_type", building_type) else {},
                "platform_specific_fields": ps_fields,
                "units": units  # 모든 unit 정보 포함
            }
            
            # record_data에서 필요한 정보만 json_fields에 추가 (중복 제거)
            filtered_record_data = {
                "eligibility_raw": record_data.get("eligibility_raw", "")
            }
            unit_json_fields = json_fields.copy()
            unit_json_fields.update(filtered_record_data)
            
            # platform_specific_fields를 세부 테이블로 분리
            ps_fields_copy = record_data.get("platform_specific_fields", {})
            
            # facilities 정보 분리 (기존 facilities와 병합)
            if "facility_info" in ps_fields_copy:
                if "facilities" in unit_json_fields:
                    unit_json_fields["facilities"].update(ps_fields_copy["facility_info"])
                else:
                    unit_json_fields["facilities"] = ps_fields_copy["facility_info"]
            
            # company_info 분리
            company_info = {}
            for key in ["company_name", "representative", "contact_phone", "homepage"]:
                if key in ps_fields_copy:
                    company_info[key] = ps_fields_copy[key]
            if company_info:
                unit_json_fields["company_info"] = company_info
            
            # housing_specific 분리
            housing_specific = {}
            for key in ["deposit", "monthly_rent", "target_occupancy"]:
                if key in ps_fields_copy:
                    if key == "deposit":
                        housing_specific["deposit_range"] = ps_fields_copy[key]
                    elif key == "monthly_rent":
                        housing_specific["monthly_rent_range"] = ps_fields_copy[key]
                    elif key == "target_occupancy":
                        housing_specific["target_occupancy_detail"] = ps_fields_copy[key]
            if housing_specific:
                unit_json_fields["housing_specific"] = housing_specific
            
            # building_details 분리
            building_details = {}
            for key in ["district_type", "building_scale", "building_structure", "site_area", 
                       "total_floor_area", "approval_date", "parking", "total_people"]:
                if key in ps_fields_copy:
                    building_details[key] = ps_fields_copy[key]
            if building_details:
                unit_json_fields["building_details"] = building_details
            
            # sohouse_text_extracted_info 분리 (기존 구조 유지)
            if "sohouse_text_extracted_info" in ps_fields_copy:
                unit_json_fields["sohouse_text_extracted_info"] = ps_fields_copy["sohouse_text_extracted_info"]
            
            # JSON 저장 (공고별 통합)
            if unit_json_fields:
                write_text(kv_json_path, json.dumps(unit_json_fields, ensure_ascii=False, indent=2))

            # CSV 레코드 생성 (공고별 통합)
            record = make_record(
                platform=self.platform_code,
                platform_id=str(PLATFORM_ID_MAP.get(self.platform_code, 1)),  # 플랫폼 번호 사용
                list_url=self.list_url,
                detail_url=page.url,
                house_name=house_name,
                address=address,
                html_path=str(html_path),
                image_paths=image_paths,
                floorplan_paths=floor_plan_paths,
                detail_text_path=str(detail_text_path) if detail_text else "",
                kv_json_path=str(kv_json_path) if unit_json_fields else "",
                unit_type=csv_unit_type,
                building_type=csv_building_type,
                theme=csv_theme,
                subway_station=csv_subway_station,
                eligibility=eligibility,
                last_modified=last_modified,
                base_dir=str(output_dir),
                unit_index=0  # 공고별 통합이므로 unit_index=0
            )

            sanity_check_address(record)
            self.rows.append(record)
            self.progress.update(f"[{self.platform_code}] Processed notice {index}: {house_name[:30]}... (units: {len(units)})")

            return True

        except Exception as e:
            self.progress.update(f"[ERROR] Detail {index+1}: {e}")
            return False
