#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Youth Housing Crawler (youth)
# - Uses BaseCrawler.process_detail_page for unified saving:
#   * stable HTML
#   * youth-tuned cleaned text (override)
#   * kv JSON
#   * CSV row (legacy-compatible)
# - Hooks:
#   * youth-specific parser for platform fields
#   * relaxed JSON filter (reuse cohouse filter)
#   * images + floor plans split

from pathlib import Path
from playwright.sync_api import sync_playwright

from .base import (
    BaseCrawler, Progress,
    robust_goto, run_dir, ensure_dirs,
)
from ..parsers.parsers import (
    extract_youth_specific_fields,
    filter_json_fields_for_cohouse as default_json_filter,
    _clean_youth_text_content,
)
from .pagination import collect_details_with_fallbacks

# Youth list (BBS/complex list) on seoul site
YOUTH_LIST = "https://soco.seoul.go.kr/youth/pgm/home/yohome/list.do?menuNo=400002"


class YouthCrawler(BaseCrawler):
    """청년주택 크롤러"""

    def __init__(self, progress: Progress, max_bbs: int = 0, platform_code: str = "youth"):
        # base_url left None; not needed
        super().__init__(progress, YOUTH_LIST, platform_code)
        self.max_bbs = max(0, int(max_bbs))

    # ---- Platform hooks --------------------------------------------
    def _extract_platform_specific_fields(self, page, detail_desc=None, detail_text_path=None, detail_text=None) -> dict:
        """Use youth parser; carry cleaned text for downstream JSON enrichment."""
        try:
            fields = extract_youth_specific_fields(page) or {}
        except Exception:
            fields = {}
        if detail_text:
            fields["text_content"] = detail_text
        return fields

    def _filter_json_fields(self, kv_pairs: dict, platform_specific_fields: dict) -> dict:
        """Youth uses relaxed filter; reuse cohouse filter to keep CSV-only fields out."""
        return default_json_filter(kv_pairs, platform_specific_fields)

    def _download_images_platform_specific(
        self, page, output_dir: Path, house_name: str, index: int
    ) -> tuple[list[str], list[str]]:
        """Youth images + floor plans (generic selectors; platform is heterogeneous)."""
        from .base import download_images_from

        (output_dir / "floor_plans").mkdir(parents=True, exist_ok=True)

        # Floor plans (by alt)
        floor_plan_paths = download_images_from(
            page, "img[alt*='평면도'], img[alt*='floor'], img[alt*='plan']",
            page.url, output_dir / "floor_plans",
            filter_floor_plan=True, house_name=house_name, index=index
        )

        # Common content images
        image_paths = []
        for sel in [
            "div.detail-box img",
            "ul.detail-list img",
            "img[src$='.jpg'], img[src$='.png'], img[src$='.gif'], img[src$='.jpeg']",
            "img[src*='upload'], img[src*='image'], img[src*='photo']",
        ]:
            image_paths += download_images_from(
                page, sel, page.url, output_dir / "images",
                filter_floor_plan=False, house_name=house_name, index=index
            )

        return image_paths, floor_plan_paths

    def _extract_csv_housing_fields(self, platform_specific_fields: dict) -> tuple[str, str, str, str]:
        """Return CSV fields (unit_type, building_type, theme, subway_station)."""
        return (
            platform_specific_fields.get("unit_type", ""),
            platform_specific_fields.get("building_type", ""),
            platform_specific_fields.get("theme", ""),
            platform_specific_fields.get("subway_station", ""),
        )

    # Youth-specific text cleaner
    def _clean_text_content(self, text: str) -> str:
        return _clean_youth_text_content(text)

    # ---- Main crawl -------------------------------------------------
    def crawl(self):
        self.progress.update(f"[START] Youth Housing Crawler (max_bbs={self.max_bbs})")

        # KST-based run dir under backend/data/
        self.output_dir = run_dir(self.platform_code)
        ensure_dirs(self.output_dir)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self.progress.update(f"[NAV] LIST {self.list_url}")
                robust_goto(page, self.list_url, self.progress, "LIST")

                details = collect_details_with_fallbacks(
                    page=page,
                    list_url=self.list_url,
                    progress=self.progress,
                )

                # optional cap
                if self.max_bbs > 0:
                    details = details[: self.max_bbs]

                self.progress.update(f"[INFO] Found {len(details)} youth housing items")

                for i, (title, detail_desc) in enumerate(details):
                    try:
                        self.progress.update(f"[DETAIL] {i+1}/{len(details)}: {title[:50]}...")
                        self.process_detail_page(page, title, detail_desc, self.output_dir, i)

                        # ★ 5건마다 중간 저장(원하면 1건마다로 바꿔도 OK)
                        if (i + 1) % 5 == 0:
                            self.save_progress(self.output_dir)

                    except Exception as e:
                        self.progress.update(f"[ERROR] 상세 페이지 처리 실패: {e}")
                        continue

                self.save_progress(self.output_dir)

                # 최종 CSV 저장(기존 로직 유지)
                if self.rows:
                    self.save_results(self.output_dir)

            except Exception as e:
                self.progress.update(f"[ERROR] 크롤링 실패: {e}")
            finally:
                browser.close()

        self.progress.update(f"[COMPLETE] youth: {len(self.rows)} records")