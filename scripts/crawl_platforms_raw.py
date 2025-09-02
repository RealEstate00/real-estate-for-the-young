#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Crawl RAW for soHouse, coHouse, youth (images + detail HTML + intro/eligibility pages).
# No emojis in comments.

from __future__ import annotations  # postpone type hints  // 타입힌트 지연
import csv, json, os, re, hashlib, argparse
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta


from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from playwright.sync_api import Error as PWError

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

# ---------- filesystem helpers ----------
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

def get_page_html_stable(page, progress: "Progress" | None = None, label: str = "content", attempts: int = 3) -> str:
    for i in range(attempts):
        # prefer networkidle if possible  // 네트워크 유휴 대기
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except PWTimeout:
            # fall back to load/domcontentloaded already done by caller  // 백업
            pass
        # try standard content()  // 기본 방식
        try:
            return page.content()
        except Exception as e:
            # fallback to outerHTML and retry once more  // outerHTML 대체 후 재시도
            try:
                return page.evaluate("document.documentElement.outerHTML")
            except Exception as e2:
                if progress:
                    progress.update(f"[RETRY content] {label} try={i+1} err={e2}")
                page.wait_for_timeout(350)  # tiny backoff
    # last resort
    return page.evaluate("document.documentElement.outerHTML")

# ---------- crawl helpers ----------
class Progress:
    def update(self, msg: str):
        print(msg, flush=True)

def robust_goto(page, url: str, progress: Progress | None = None, label: str = ""):
    if progress:
        progress.update(f"[NAV] {label} {url}")
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
    except PWTimeout:
        if progress:
            progress.update(f"[TIMEOUT domcontentloaded] {url}, retry with load")
        try:
            page.goto(url, timeout=60000, wait_until="load")
        except Exception as e:
            if progress:
                progress.update(f"[GOTO FAIL] {url} -> {e}")
            raise

def safe_wait_any(page, selectors: list[str], timeout=15000) -> str:
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout)
            return sel
        except PWTimeout:
            continue
    return ""

def download_images_from(page, selector: str, base_url: str, dst_dir: Path) -> list[str]:
    # collect images/anchors and download if missing  // 이미지/첨부 수집, 없을 때만 다운로드
    els = page.locator(selector)
    saved: list[str] = []
    seen: set[str] = set()  # per-call de-dup by url  // 호출 내 url 중복 제거
    dst_dir.mkdir(parents=True, exist_ok=True)
    n = els.count()

    for i in range(n):
        src = (
            els.nth(i).get_attribute("src")
            or els.nth(i).get_attribute("data-src")
            or els.nth(i).get_attribute("href")
            or ""
        )
        if not src:
            continue

        abs_url = urljoin(base_url, src)
        if abs_url in seen:
            continue
        seen.add(abs_url)

        # derive filename from url; fallback to hash  // 파일명 도출, 실패 시 해시
        url_name = abs_url.split("/")[-1].split("?")[0]
        if not url_name:
            url_name = f"{sha256(abs_url)[:16]}.bin"
        out = dst_dir / url_name

        # skip if file already exists and non-empty  // 기존 파일 있으면 스킵
        try:
            if out.exists() and out.stat().st_size > 0:
                saved.append(str(out))
                continue
        except Exception:
            pass

        # fetch and write  // 다운로드 및 저장
        try:
            resp = page.context.request.get(abs_url)
            if not resp.ok:
                continue

            # adjust extension if unknown and content-type hints  // 확장자 보정(선택)
            if out.suffix.lower() in ("", ".bin"):
                ct = (resp.headers or {}).get("content-type", "").split(";")[0].strip()
                ext_map = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/webp": ".webp",
                    "application/pdf": ".pdf",
                }
                ext = ext_map.get(ct, out.suffix or ".bin")
                if ext != out.suffix:
                    out = out.with_suffix(ext)

            write_bytes(out, resp.body())
            saved.append(str(out))
        except Exception:
            # log and continue if you want  // 로깅 후 계속
            continue

    return saved

def make_record(platform: str, platform_id: str, list_url: str, detail_url: str, house_name: str, address: str,
                platform_intro: str, html_path: str, image_paths: list[str], extras: dict) -> dict:
    rid_src = "|".join([platform, platform_id or "", list_url or "", detail_url or "", house_name or ""])
    return {
        "platform": platform,
        "platform_id": platform_id,
        "crawl_date": TODAY,
        "house_name": house_name,
        "address": address,
        "platform_intro": platform_intro,
        "list_url": list_url,
        "detail_url": detail_url,
        "detail_descriptor": extras.get("_detail_descriptor", ""),
        "image_paths": ";".join(image_paths),
        "html_path": html_path,
        "extras_json": json.dumps({k: v for k, v in extras.items() if not k.startswith("_")}, ensure_ascii=False),
        "crawled_at": datetime.now(KST).isoformat(),
        "record_id": sha256(rid_src)
    }

def dump_first_table_to_csv(page, container_selector: str, out_csv_path: Path) -> bool:
    try:
        container = page.locator(container_selector)
        if not container.count():
            return False
        # 컨테이너 안 첫 번째 table 대상
        tbl = container.locator("table").first
        if not tbl.count():
            return False

        # 헤더
        ths = tbl.locator("thead th")
        headers = []
        if ths.count():
            for i in range(ths.count()):
                headers.append(ths.nth(i).inner_text().strip())
        else:
            # thead 없으면 첫 tr의 th/td를 헤더로
            first_tr = tbl.locator("tr").first
            cells = first_tr.locator("th, td")
            for i in range(cells.count()):
                headers.append(cells.nth(i).inner_text().strip())

        # 바디
        rows = []
        # 헤더 행을 스킵하기 위해 tbody 우선, 없으면 tr 전체에서 첫 행 제외
        body_trs = tbl.locator("tbody tr")
        tr_list = []
        if body_trs.count():
            for i in range(body_trs.count()):
                tr_list.append(body_trs.nth(i))
        else:
            all_trs = tbl.locator("tr")
            for i in range(max(0, all_trs.count()-1)):
                tr_list.append(all_trs.nth(i+1))

        for tr in tr_list:
            tds = tr.locator("td")
            row = []
            for i in range(tds.count()):
                row.append(tds.nth(i).inner_text().strip())
            if row:
                rows.append(row)

        out_csv_path.parent.mkdir(parents=True, exist_ok=True)
        import csv
        with out_csv_path.open("w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            if headers:
                w.writerow(headers)
            for r in rows:
                w.writerow(r)
        return True
    except Exception:
        return False

# pick today's dated output folder and init subdirs
def run_dir(kind: str) -> Path:
    base = Path("data/raw") / TODAY / kind
    (base / "html").mkdir(parents=True, exist_ok=True)
    (base / "images").mkdir(parents=True, exist_ok=True)
    (base / "tables").mkdir(parents=True, exist_ok=True)
    return base

# ensure base + common subfolders exist
def ensure_dirs(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    (base / "html").mkdir(parents=True, exist_ok=True)
    (base / "images").mkdir(parents=True, exist_ok=True)
    (base / "tables").mkdir(parents=True, exist_ok=True)

RAW_HEADER = [
    "record_id","platform","platform_id","crawl_date","house_name","address","platform_intro",
    "list_url","detail_url","detail_descriptor","image_paths","html_path","extras_json","crawled_at"
]

# ---------- platform configs ----------
# "사회주택, 공동체주택, 청년안심주택, LH&SH" url
SO_BASE = "https://soco.seoul.go.kr"
SO_SOCIAL_LIST = f"{SO_BASE}/soHouse/pgm/home/sohome/list.do?menuNo=300006"
SO_COMM_LIST   = f"{SO_BASE}/coHouse/pgm/home/cohome/list.do?menuNo=200043"
SH_PLAN = "https://www.i-sh.co.kr/main/lay2/S1T243C1043/contents.do"
LH_LIST = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026"

# intro/policy pages
SOCIAL_INTRO_URL             = f"{SO_BASE}/soHouse/main/contents.do?menuNo=300007"
SOCIAL_ELIG_URL              = f"{SO_BASE}/soHouse/main/contents.do?menuNo=300037"
CO_INTRO_URL                 = f"{SO_BASE}/coHouse/main/contents.do?menuNo=200027"
YOUTH_INTRO_URL              = f"{SO_BASE}/youth/main/contents.do?menuNo=400012"
YOUTH_FINANCE_URL            = f"{SO_BASE}/youth/main/contents.do?menuNo=400021"
SEOUL_PORTAL_HAPPY_INTRO_URL = "https://housing.seoul.go.kr/site/main/content/sh01_060503"

# ---------- extractors ----------
# Extract House name
def parse_house_name(page):
    # Try several common selectors
    sels = ["h3.pageTit", "h2.title", "div.title h2", ".detail-tit", "h1, h2, h3"]
    for s in sels:
        try:
            el = page.locator(s).first
            if el.count():
                t = el.inner_text().strip()
                if t:
                    return t
        except Exception:
            continue
    return ""

def parse_address(page):
    # Look for labels containing 주소
    try:
        label = page.locator("xpath=//*[contains(text(), '주소')]").first
        if label.count():
            # take following sibling text
            parent = label.locator("xpath=./following::*").first
            return parent.inner_text().strip()[:300]
    except Exception:
        pass
    # Fallback: any element with class containing 'addr'
    for s in ["[class*='addr']", ".address", ".loc", ".location"]:
        try:
            el = page.locator(s).first
            if el.count():
                t = el.inner_text().strip()
                if t:
                    return t
        except Exception:
            continue
    return ""

def extract_platform_intro_text(page, container_selectors: list[str]) -> str:
    for sel in container_selectors:
        try:
            if page.locator(sel).count():
                txt = page.locator(sel).inner_text().strip()
                if txt:
                    return re.sub(r"\s+\n", "\n", txt)
        except Exception:
            continue
    # Fallback to body
    return page.locator("body").inner_text().strip()[:4000]

# ---------- crawlers ----------
def crawl_list_detail_blocks(page, list_url: str, row_selector: str, link_selector: str, progress: Progress):
    robust_goto(page, list_url, progress, label="LIST")
    page.wait_for_selector(row_selector, timeout=15000)
    rows = page.locator(row_selector)
    detail_descriptors = []
    for i in range(rows.count()):
        a = rows.nth(i).locator(link_selector)
        if not a.count():
            continue
        href = a.first.get_attribute("href") or ""
        title = a.first.inner_text().strip()
        if href.startswith("javascript:"):
            # javascript:modify(20000569)
            m = re.search(r"javascript:(\w+)\(([^)]*)\)", href)
            if m:
                fname = m.group(1)
                arg = m.group(2).strip()
                descriptor = {"kind":"js_function","name":fname,"args":[arg]}
                detail_descriptors.append((title, descriptor))
        else:
            abs_url = urljoin(list_url, href)
            detail_descriptors.append((title, {"kind":"get","url":abs_url}))
    return detail_descriptors

def open_detail(page, base_for_referer: str, descriptor: dict, progress: Progress):
    if descriptor.get("kind") == "js_function":
        name = descriptor["name"]; args = descriptor.get("args", [])
        progress.update(f"[DETAIL JS] {name}({','.join(args)})")
        page.evaluate(f"{name}({','.join(args)})")
        page.wait_for_load_state("domcontentloaded")
    elif descriptor.get("kind") == "get":
        url = descriptor["url"]
        robust_goto(page, url, progress, label="DETAIL")
    else:
        raise ValueError("Unknown detail descriptor")

def crawl_sohouse_like(platform_code: str, list_url: str, out_dir: Path, progress: Progress):
    rows_out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # use site root; accept downloads
        ctx = browser.new_context(accept_downloads=True, base_url=SO_BASE)
        page = ctx.new_page()

        # collect detail descriptors from list
        details = crawl_list_detail_blocks(
            page,
            list_url=list_url,
            row_selector="table.boardTable tbody tr",
            link_selector="a.no-scr, td a[href^='javascript:modify']",
            progress=progress
        )

        for idx, (title, desc) in enumerate(details):
            progress.update(f"[{platform_code}] detail {idx+1}/{len(details)} {title[:40]}")
            # open detail
            open_detail(page, list_url, desc, progress)

            # build file paths
            house_name = parse_house_name(page) or title
            address = parse_address(page)
            rid = sha256("|".join([platform_code, title, address]))
            html_path = out_dir / "html" / f"{rid}.html"
            write_text(html_path, get_page_html_stable(page, progress, label=f"{platform_code} detail"))

            # download images from typical containers
            img_dir = out_dir / "images" / rid
            image_paths = []
            image_paths += download_images_from(page, "div.detail-box img", list_url, img_dir)
            image_paths += download_images_from(page, "ul.detail-list img", list_url, img_dir)
            image_paths += download_images_from(page, "img[src*='fileDown.do']", list_url, img_dir)

            # capture occupancy table raw html if present // 입주현황 원본 html
            occ_html = ""
            try:
                if page.locator("div.tableWrap").count():
                    occ_html = page.locator("div.tableWrap").inner_html()
            except Exception:
                pass

            # path for occupancy table csv under tables
            occ_table_csv = (out_dir / "tables" / f"{rid}_occupancy.csv")
            saved_csv = dump_first_table_to_csv(page, "div.tableWrap", occ_table_csv)

            # build extras payload for raw record
            extras = {
                "_detail_descriptor": json.dumps(desc, ensure_ascii=False),
                "occupancy_table_html": occ_html,
                "occupancy_table_csv": str(occ_table_csv) if saved_csv else ""
            }

            rec = make_record(
                platform=platform_code,
                platform_id="",
                list_url=list_url,
                detail_url=desc.get("url","") if desc.get("kind")=="get" else "",
                house_name=house_name,
                address=address,
                platform_intro="",
                html_path=str(html_path),
                image_paths=image_paths,
                extras=extras
            )
            rows_out.append(rec)

        append_csv(out_dir / "raw.csv", RAW_HEADER, rows_out)
        browser.close()
    progress.update(f"[DONE] {platform_code} rows={len(rows_out)}")

def crawl_platform_info(progress: Progress):
    base = Path(f"data/raw/{TODAY}/platform_info")
    ensure_dirs(base)
    rows = []

    pages = [
        ("sohouse_intro", SOCIAL_INTRO_URL, ["article", ".subLayout", "body"]),
        ("sohouse_eligibility", SOCIAL_ELIG_URL, ["article", ".subLayout", "body"]),
        ("cohouse_intro", CO_INTRO_URL, ["article", ".subLayout", "body"]),
        ("youth_intro", YOUTH_INTRO_URL, ["article", ".subLayout", "body"]),
        ("youth_finance", YOUTH_FINANCE_URL, ["article.subLayout.support-intro", ".subLayout", "body"]),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        for code, url, sels in pages:
            robust_goto(page, url, progress, label="INFO")
            safe_wait_any(page, ["article", ".subLayout", "#content", "body"], timeout=8000) 
            page.wait_for_load_state("domcontentloaded")
            rid = sha256(code + "|" + url)
            html_path = base / "html" / f"{rid}.html"
            write_text(html_path, get_page_html_stable(page, progress, label=f"INFO {url}"))
            text = extract_platform_intro_text(page, sels)
            # light image capture from article
            img_dir = base / "images" / code
            imgs = download_images_from(page, "article img, .subLayout img", url, img_dir)
            rows.append({
                "record_id": rid,
                "platform": code,
                "platform_id": "",
                "crawl_date": TODAY,
                "house_name": "",   # N/A for intro
                "address": "",
                "platform_intro": text[:2000],
                "list_url": url,
                "detail_url": url,
                "detail_descriptor": "",
                "image_paths": ";".join(imgs),
                "html_path": str(html_path),
                "extras_json": json.dumps({}, ensure_ascii=False),
                "crawled_at": datetime.now(KST).isoformat()
            })
        append_csv(base / "raw.csv", RAW_HEADER, rows)
        browser.close()
    progress.update(f"[DONE] platform_info rows={len(rows)}")

def crawl_seoul_portal_happy_info(progress: Progress):
    base = Path(f"data/raw/{TODAY}/seoul_portal_happy_intro")
    ensure_dirs(base)
    rows = []
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context()
        page = ctx.new_page()

        robust_goto(page, SEOUL_PORTAL_HAPPY_INTRO_URL, progress, label="INFO")
        page.wait_for_load_state("domcontentloaded")

        # 저장 경로
        rid = sha256("seoul_portal_happy_intro|" + SEOUL_PORTAL_HAPPY_INTRO_URL)
        html_path = base / "html" / f"{rid}.html"
        write_text(html_path, get_page_html_stable(page, progress, label="seoul_portal_happy_intro"))

        # 본문 텍스트 추출(컨테이너 후보 몇 가지)
        text = extract_platform_intro_text(
            page,
            container_selectors=[
                "article", "#content", ".cont_wrap", ".content", "main"
            ]
        )

        # Save Image
        img_dir = base / "images" / rid
        imgs = download_images_from(
            page,
            "article img, .content img, .cont_wrap img",
            SEOUL_PORTAL_HAPPY_INTRO_URL,
            img_dir
        )

        rec = {
            "record_id": rid,
            "platform": "seoul_portal_happy_intro",
            "platform_id": "",
            "crawl_date": TODAY,
            "house_name": "",              # Null
            "address": "",                 # Null
            "platform_intro": text[:2000], # 길면 잘라 저장
            "list_url": SEOUL_PORTAL_HAPPY_INTRO_URL,
            "detail_url": SEOUL_PORTAL_HAPPY_INTRO_URL,
            "detail_descriptor": "",
            "image_paths": ";".join(imgs),
            "html_path": str(html_path),
            "extras_json": json.dumps({}, ensure_ascii=False),
            "crawled_at": datetime.now(KST).isoformat()
        }
        rows.append(rec)
        append_csv(base / "raw.csv", RAW_HEADER, rows)
        br.close()
    progress.update(f"[DONE] seoul_portal_happy_intro rows={len(rows)}")

def crawl_youth_unified(progress: Progress):
    # Unified RAW for youth: listing + bbs announcements minimal smoke (extend later).
    base = Path(f"data/raw/{TODAY}/youth_unified")
    ensure_dirs(base)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(accept_downloads=True, base_url=SO_BASE)
        page = ctx.new_page()

        # A) 주택찾기
        list_url = f"{SO_BASE}/youth/pgm/home/yohome/list.do?menuNo=400002"
        details = crawl_list_detail_blocks(
            page, list_url,
            row_selector="table.boardTable tbody tr",
            link_selector="a[href^='javascript:modify'], td a",
            progress=progress
        )
        for title, desc in details[:10]:  # start small; lift the limit after smoke
            open_detail(page, list_url, desc, progress)
            rid = sha256("youth_home|" + title)
            html_path = base / "html" / f"{rid}.html"
            write_text(html_path, get_page_html_stable(page, progress, label="youth_home"))
            house_name = parse_house_name(page) or title
            address = parse_address(page)
            img_dir = base / "images" / rid
            imgs = download_images_from(page, ".bbsV_atchmnfl a, article img", page.url, img_dir)
            rec = make_record("youth_home","","", desc.get("url","") if desc.get("kind")=="get" else "",
                              house_name, address, "", str(html_path), imgs, {"source_type":"listing",
                              "_detail_descriptor": json.dumps(desc, ensure_ascii=False)})
            rows.append(rec)

        # B) 모집공고(BBS) 목록 → 상세
        bbs_url = f"{SO_BASE}/youth/bbs/BMSR00015/list.do?menuNo=400008"
        robust_goto(page, bbs_url, progress, "LIST")
        safe_wait_any(page, ["tbody#boardList tr", ".tbl_list tbody tr", "table tbody tr"], timeout=15000)

        # collect hrefs before navigating  // 이동 전 href 전수 수집
        link_sel = "tbody#boardList tr td.align_left a[href*='view.do?']"
        links = page.locator(link_sel)
        n = min(10, links.count())
        hrefs = []
        for i in range(n):
            try:
                h = links.nth(i).get_attribute("href")
                if h:
                    hrefs.append(urljoin(bbs_url, h))
            except Exception:
                continue

        for abs_url in hrefs:
            robust_goto(page, abs_url, progress, "DETAIL")
            safe_wait_any(page, ["h1","h2","h3","article"], timeout=10000)

            # title extract (fallbacks)  // 제목 추출
            try:
                title = page.locator("h1, h2, h3, a[title]").first.inner_text().strip()
            except Exception:
                title = abs_url.rsplit("=", 1)[-1]

            rid = sha256("youth_bbs|" + abs_url)
            html_path = base / "html" / f"{rid}.html"
            write_text(html_path, get_page_html_stable(page, progress, label="youth_bbs"))

            img_dir = base / "images" / rid
            # capture images/attachments (supports <a href>)  // 이미지/첨부 저장
            imgs = download_images_from(page, ".bbsV_atchmnfl a, article img", page.url, img_dir)

            rec = make_record(
                "youth_bbs","",bbs_url, abs_url, title, "", "",
                str(html_path), imgs, {"source_type":"announcement"}
            )
            rows.append(rec)

        append_csv(base / "raw.csv", RAW_HEADER, rows)
        browser.close()
    progress.update(f"[DONE] youth_unified rows={len(rows)}")

def crawl_sh_happy_plan(progress: Progress):
    base = run_dir("sh_plan_happy")
    rows = []
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context(base_url="https://www.i-sh.co.kr")
        page = ctx.new_page()

        # go to list  // 진입
        robust_goto(page, SH_PLAN, progress, "LIST")

        # navigate to '행복주택' tab by href first  // href 우선 이동
        link = page.locator("a:has-text('행복주택')").first
        tab_href = ""
        try:
            if link.count():
                tab_href = link.get_attribute("href") or ""
        except Exception:
            tab_href = ""

        if tab_href:
            # build absolute and navigate  // 절대경로로 이동
            robust_goto(page, urljoin(SH_PLAN, tab_href), progress, "TAB")
        else:
            # try force click as a backup  // 백업 강제클릭
            try:
                link.scroll_into_view_if_needed(timeout=3000)
                link.click(force=True, timeout=5000)
            except Exception:
                # hard fallback: known path  // 최후 수단 고정경로
                robust_goto(page, "https://www.i-sh.co.kr/main/lay2/S1T243C1045/contents.do", progress, "TAB")

        # wait for table to be present  // 표 로딩 대기
        safe_wait_any(page, ["table", ".cont_tbl table", "article table"], timeout=20000)

        # 표 전체를 행 단위로 pull
        rows_loc = page.locator("table tr")
        for i in range(1, rows_loc.count()):
            tds = rows_loc.nth(i).locator("td")
            if not tds.count():
                continue
            try:
                complex_name = tds.nth(0).inner_text().strip()
                total_units  = tds.nth(1).inner_text().strip()
                area_units   = [tds.nth(2).inner_text().strip(), tds.nth(3).inner_text().strip()]
                district     = tds.nth(5).inner_text().strip()
                month_plan   = tds.nth(6).inner_text().strip()
                plan_type    = tds.nth(7).inner_text().strip()
            except Exception:
                continue

            rid_src = f"sh_plan_happy|{complex_name}|{district}|{month_plan}"
            rid = sha256(rid_src)
            html_path = base / "html" / f"{rid}.html"
            write_text(html_path, get_page_html_stable(page, progress, label="sh_plan_happy"))

            rec = {
                "record_id": rid,
                "platform": "ha_sh",
                "platform_id": "",
                "crawl_date": TODAY,
                "house_name": complex_name,
                "address": district,
                "platform_intro": "",
                "list_url": SH_PLAN,
                "detail_url": SH_PLAN,
                "detail_descriptor": "",
                "image_paths": "",
                "html_path": str(html_path),
                "extras_json": json.dumps({
                    "housing_category": "행복주택",
                    "month_plan_raw": month_plan,
                    "plan_type": plan_type,
                    "total_units_raw": total_units,
                    "area_units_raw": area_units
                }, ensure_ascii=False),
                "crawled_at": datetime.now(KST).isoformat()
            }
            rows.append(rec)

        append_csv(base / "raw.csv", RAW_HEADER, rows)
        br.close()
    progress.update(f"[DONE] sh_plan_happy rows={len(rows)}")

def crawl_lh_announcements(progress: Progress, max_rows: int = 80):
    base = Path(f"data/raw/{TODAY}/lh_ann")
    ensure_dirs(base)
    rows = []
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context(base_url=LH_LIST)
        page = ctx.new_page()
        robust_goto(page, LH_LIST, progress, "LIST")
        page.wait_for_selector("table", timeout=20000)

        tr = page.locator("table tr")
        count = tr.count()
        for i in range(1, count):
            if len(rows) >= max_rows:
                break
            tds = tr.nth(i).locator("td")
            if not tds.count():
                continue
            try:
                type_text = tds.nth(1).inner_text().strip()
                a = tds.nth(2).locator("a.wrtancInfoBtn").first
                if not a.count():
                    continue
                title = a.inner_text().strip()
                region = tds.nth(3).inner_text().strip()
                posted = tds.nth(5).inner_text().strip()
                deadline = tds.nth(6).inner_text().strip()
                # 상세 POST 진입용 data-id*
                did = {
                    "data-id1": a.get_attribute("data-id1") or "",
                    "data-id2": a.get_attribute("data-id2") or "",
                    "data-id3": a.get_attribute("data-id3") or "",
                    "data-id4": a.get_attribute("data-id4") or "",
                }
                # external_id 대용(안정적이면 panId=data-id1 사용)
                external_id = did["data-id1"] or sha256(title + posted)
            except Exception:
                continue

            rid_src = f"ha_lh|{external_id}|{title}"
            rid = sha256(rid_src)
            html_path = base / "html" / f"{rid}.html"
            write_text(html_path, get_page_html_stable(page, progress, label="lh_ann"))

            rec = {
                "record_id": rid,
                "platform": "ha_lh",
                "platform_id": "",
                "crawl_date": TODAY,
                "house_name": title,
                "address": region,
                "platform_intro": "",
                "list_url": LH_LIST,
                "detail_url": "",  # POST 상세라 빈값
                "detail_descriptor": json.dumps({
                    "kind": "post",
                    "url": "/lhapply/apply/wt/wrtanc/selectWrtancInfo.do",
                    "form": {
                        "panId": did["data-id1"],
                        "ccrCnntSysDsCd": did["data-id2"],
                        "uppAisTpCd": did["data-id3"],
                        "aisTpCd": did["data-id4"]
                    }
                }, ensure_ascii=False),
                "image_paths": "",
                "html_path": str(html_path),
                "extras_json": json.dumps({
                    "housing_category": type_text,
                    "posting_date_raw": posted,
                    "deadline_raw": deadline,
                    "external_id_hint": external_id
                }, ensure_ascii=False),
                "crawled_at": datetime.now(KST).isoformat()
            }
            rows.append(rec)

        append_csv(base / "raw.csv", RAW_HEADER, rows)
        br.close()
    progress.update(f"[DONE] lh_ann rows={len(rows)}")


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Crawl RAW with images and intro pages")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("sohouse", help="사회주택 목록->상세 RAW")
    s2 = sub.add_parser("cohouse", help="공동체주택 목록->상세 RAW")
    s3 = sub.add_parser("platform_info", help="소개/입주자격/금융지원 RAW")
    s4 = sub.add_parser("youth", help="청년안심 주택찾기+모집공고 통합 RAW")
    s5 = sub.add_parser("sh_happy", help="SH 공급계획 행복주택 탭 RAW")
    s6 = sub.add_parser("lh_ann", help="LH 공고 목록 RAW")
    s7 = sub.add_parser("seoul_happy_intro", help="서울주거포털 행복주택 소개 RAW")

    args = ap.parse_args()
    progress = Progress()

    if args.cmd == "sohouse":
        out_dir = run_dir("sohouse")  # was: Path(f"data/raw/{TODAY}/sohouse")
        with sync_playwright() as p:
            pass
        crawl_sohouse_like("sohouse", SO_SOCIAL_LIST, out_dir, progress)
    elif args.cmd == "cohouse":
        out_dir = run_dir("cohouse")
        crawl_sohouse_like("cohouse", SO_COMM_LIST, out_dir, progress)
    elif args.cmd == "platform_info":
        crawl_platform_info(progress)
    elif args.cmd == "youth":
        crawl_youth_unified(progress)
    elif args.cmd == "sh_happy":
        crawl_sh_happy_plan(progress)
    elif args.cmd == "lh_ann":
        crawl_lh_announcements(progress)
    elif args.cmd == "seoul_happy_intro":
        crawl_seoul_portal_happy_info(progress)

if __name__ == "__main__":
    main()