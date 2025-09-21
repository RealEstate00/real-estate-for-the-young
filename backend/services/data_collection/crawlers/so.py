#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Social Housing Crawler (sohouse)
# - Unified saving via BaseCrawler.process_detail_page:
#   * stable HTML
#   * cleaned text -> texts/
#   * kv JSON -> kv/   (dir ensured)
#   * CSV row -> raw.csv (legacy-compatible header)
# - Platform hooks:
#   * _extract_platform_specific_fields (parser + detail_text carry-over)
#   * _filter_json_fields (legacy-compatible JSON filtering)
#   * _download_images_platform_specific (listing vs. floor plans, selectors tuned)

from pathlib import Path
from playwright.sync_api import sync_playwright

from .base import (
    BaseCrawler, Progress,
    robust_goto, run_dir, ensure_dirs,
    urljoin, sha256, write_bytes,
    SO_SOCIAL_LIST,
    safe_wait_any,                   # ← ensure imported wait helper
    get_page_html_stable,            # ← we will use stronger waits before HTML dump
)
from ..parsers.parsers import (
    extract_sohouse_specific_fields,
    filter_json_fields_for_sohouse,
)
from .pagination import collect_details_with_fallbacks


# ---- Improved downloader that supports both <img> and <a href="fileDown.do"> ----
def _download_from_nodes(page, nodes, base_url, out_dir: Path, *, is_floor: bool, house_name: str, index: int) -> list[str]:
    saved, seen = [], set()
    out_dir.mkdir(parents=True, exist_ok=True)

    n = nodes.count()
    for i in range(n):
        el = nodes.nth(i)

        # prefer href then src/data-src
        src = (
            el.get_attribute("href") or
            el.get_attribute("src") or
            el.get_attribute("data-src") or
            ""
        ).strip()

        if not src or src.startswith(("javascript:", "data:", "#")):
            continue

        abs_url = urljoin(base_url, src)
        if abs_url in seen:
            continue
        seen.add(abs_url)

        # build filename
        hn = (house_name or f"house_{index:04d}").replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(" ", "_")
        hn = hn[:20] or f"house_{index:04d}"
        ftype = "floor_plan" if is_floor else "house_image"
        name = f"detail_{index:04d}_{hn}_{ftype}_{sha256(abs_url)[:8]}.jpg"
        if len(name) > 100:
            name = f"detail_{index:04d}_{ftype}_{sha256(abs_url)[:16]}.jpg"
        out = out_dir / name

        try:
            if out.exists() and out.stat().st_size > 0:
                saved.append(str(out)); continue
        except Exception:
            pass

        try:
            resp = page.context.request.get(abs_url)
            if not resp.ok:
                continue
            # fix extension by content-type
            if out.suffix.lower() in ("", ".bin"):
                ct = (resp.headers or {}).get("content-type", "").split(";")[0].strip()
                ext_map = {
                    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                    "image/webp": ".webp", "application/pdf": ".pdf",
                }
                ext = ext_map.get(ct, out.suffix or ".bin")
                if ext != out.suffix:
                    out = out.with_suffix(ext)

            write_bytes(out, resp.body())
            saved.append(str(out))
        except Exception:
            continue

    return saved


def download_images_from(page, selector: str, base_url: str, dst_dir: Path, *, filter_floor_plan: bool, house_name: str, index: int) -> list[str]:
    """Wrapper kept for compatibility; uses the improved _download_from_nodes."""
    nodes = page.locator(selector)
    return _download_from_nodes(page, nodes, base_url, dst_dir, is_floor=filter_floor_plan, house_name=house_name, index=index)


class SoHouseCrawler(BaseCrawler):
    """사회주택 크롤러"""

    def __init__(self, progress: Progress, platform_code: str = "sohouse"):
        super().__init__(progress, SO_SOCIAL_LIST, platform_code)

    def _extract_platform_specific_fields(self, page, detail_desc=None, detail_text_path=None, detail_text=None) -> dict:
        fields = extract_sohouse_specific_fields(page, detail_text or "") or {}
        if detail_text:
            fields["text_content"] = detail_text
        # carry over any hints parsed on list page
        if isinstance(detail_desc, dict):
            ut = detail_desc.get("unit_type")
            if ut: fields["unit_type"] = ut
            theme = detail_desc.get("theme")
            if theme: fields["theme"] = theme
            # 리스트에서 추출한 지하철역 정보 사용 (cohouse와 동일한 로직)
            subway = detail_desc.get("subway_station")
            if subway and subway.strip() and subway != "전역":
                fields["subway_station"] = subway.strip()
        
        
        return fields

    def _filter_json_fields(self, kv_pairs: dict, platform_specific_fields: dict) -> dict:
        # Let the parser filter aggressively: strip tags/normalize/price-range sanity
        return filter_json_fields_for_sohouse(kv_pairs, platform_specific_fields)

    def _download_images_platform_specific(self, page, output_dir: Path, house_name: str, index: int, unit_index: int = 0) -> tuple[list[str], list[str]]:
        """Collect normal images and floor plans from multiple containers/selectors."""
        (output_dir / "floor_plans").mkdir(parents=True, exist_ok=True)

        # Floor plans: match both <img> and <a href="fileDown.do?...평면...">
        floor_selectors = [
            # direct images with alt
            "img[alt*='평면']", "img[alt*='plan']", "img[alt*='floor']",
            # anchors that trigger downloads; many sites serve plans as files
            "a[href*='fileDown.do'][href*='평면']",
            "a[href*='fileDown.do'][href*='plan']",
            "a[href*='fileDown.do'][href*='floor']",
            # common containers
            ".viewTable a[href*='fileDown.do']",
            ".detail-box a[href*='fileDown.do']",
        ]
        floor_plan_paths = []
        for sel in floor_selectors:
            floor_plan_paths += download_images_from(
                page, sel, page.url, output_dir / "floor_plans",
                filter_floor_plan=True, house_name=house_name, index=index
            )

        # Listing images: prefer fileDown.do or semantic alt in common containers
        image_selectors = [
            "img[src*='fileDown.do']",
            ".slick-slider img[src*='fileDown.do']",
            ".detail-box img[src*='fileDown.do']",
            ".viewTable img[src*='fileDown.do']",
            "img[alt*='전경']", "img[alt*='외관']", "img[alt*='상세소개']", "img[alt*='조감도']", "img[alt*='건물']",
        ]
        image_paths = []
        for sel in image_selectors:
            image_paths += download_images_from(
                page, sel, page.url, output_dir / "images",
                filter_floor_plan=False, house_name=house_name, index=index
            )

        return image_paths, floor_plan_paths

    def _extract_csv_housing_fields(self, platform_specific_fields: dict) -> tuple[str, str, str, str]:
        return (
            platform_specific_fields.get("unit_type", ""),
            platform_specific_fields.get("building_type", ""),
            platform_specific_fields.get("theme", ""),
            platform_specific_fields.get("subway_station", ""),
        )

    def crawl(self):
        self.progress.update("[START] 사회주택 Crawler")

        self.output_dir = run_dir(self.platform_code)
        ensure_dirs(self.output_dir)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # LIST: collect_details_with_fallbacks handles navigation internally
                details = collect_details_with_fallbacks(
                    page=page,
                    list_url=self.list_url,
                    progress=self.progress,
                    max_pages=0,
                )

                if not details:
                    self.progress.update("[INFO] Found 0 social housing items")
                    return

                self.progress.update(f"[INFO] Found {len(details)} social housing items")

                for i, (title, detail_desc) in enumerate(details):
                    try:
                        self.progress.update(f"[DETAIL] {i+1}/{len(details)}: {title[:50]}...")

                        # Stronger wait before dumping HTML inside process_detail_page
                        # (process_detail_page itself will call open_detail and wait again)
                        # We keep the guard here in case detail was already open
                        safe_wait_any(page, [".viewTable", ".detail-info", ".detail-box", ".view-content"], timeout=15000)

                        self.process_detail_page(page, title, detail_desc, self.output_dir, i)

                        if (i + 1) % 5 == 0:
                            self.save_progress(self.output_dir)

                    except Exception as e:
                        self.progress.update(f"[ERROR] 상세 페이지 처리 실패: {e}")
                        continue

                self.save_progress(self.output_dir)
                if self.rows:
                    self.save_results(self.output_dir)

            except Exception as e:
                self.progress.update(f"[ERROR] 크롤링 실패: {e}")
            finally:
                browser.close()

        self.progress.update(f"[COMPLETE] sohouse: {len(self.rows)} records")