#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Community Housing Crawler (cohouse)

from pathlib import Path
from playwright.sync_api import sync_playwright

from .base import (
    BaseCrawler, Progress,
    run_dir, ensure_dirs,
    urljoin, sha256, write_bytes,
    SO_COMM_LIST,
)
try:
    from ..parsers.parsers import (
        extract_cohouse_specific_fields,
        filter_json_fields_for_cohouse,
    )
except ImportError:
    # 레포에 cohouse 전용 함수가 없으면 sohouse 로직 재사용
    from ..parsers.parsers import (
        extract_sohouse_specific_fields as extract_cohouse_specific_fields,
        filter_json_fields_for_cohouse,
    )
from .pagination import collect_details_with_fallbacks

# ----------- Image downloader (filters banners/icons; separates floor plans) -----------
def download_images_from(
    page,
    selector: str,
    base_url: str,
    dst_dir: Path,
    *,
    filter_floor_plan: bool = False,
    house_name: str = "",
    index: int = 0,
) -> list[str]:
    """Download images matched by selector; skip obvious non-content images."""
    els = page.locator(selector)
    saved: list[str] = []
    seen: set[str] = set()
    dst_dir.mkdir(parents=True, exist_ok=True)

    for i in range(els.count()):
        src = (
            els.nth(i).get_attribute("src")
            or els.nth(i).get_attribute("data-src")
            or els.nth(i).get_attribute("href")
            or ""
        ).strip()
        if not src or "javascript:" in src:
            continue

        alt_text = (els.nth(i).get_attribute("alt") or "").lower()

        # Exclude obvious non-content images
        if any(k in alt_text for k in ["banner", "icon", "logo", "btn", "arrow", "nav"]):
            continue
        if any(k in src.lower() for k in ["banner", "icon", "logo", "ico", "btn", "arrow", "nav", "dot"]):
            continue

        # Floor-plan filter vs. house image filter
        if filter_floor_plan:
            if ("평면도" not in alt_text) and ("floor" not in alt_text) and ("plan" not in alt_text):
                continue
        else:
            # Prefer real listing images (site serves them through fileDown.do)
            if "fileDown.do" not in src:
                continue
            if not any(k in alt_text for k in ["전경", "상세소개", "조감도", "외관", "건물", "주택"]):
                continue

        abs_url = urljoin(base_url, src)
        if abs_url in seen:
            continue
        seen.add(abs_url)

        # Build file name
        hn = (house_name or f"house_{index:04d}")\
            .replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(" ", "_")
        hn = hn[:20] or f"house_{index:04d}"
        ftype = "floor_plan" if filter_floor_plan else "house_image"

        url_name = f"detail_{index:04d}_{hn}_{ftype}_{sha256(abs_url)[:8]}.jpg"
        if len(url_name) > 100:
            url_name = f"detail_{index:04d}_{ftype}_{sha256(abs_url)[:16]}.jpg"

        out = dst_dir / url_name

        # Skip if already present
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

            # Fix extension by content-type if needed
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
            continue

    return saved


class CoHouseCrawler(BaseCrawler):
    """공동체주택 크롤러"""

    def __init__(self, progress: Progress, platform_code: str = "cohouse"):
        super().__init__(progress, SO_COMM_LIST, platform_code)

    # ---- Platform hooks (override) ---------------------------------
    def _extract_platform_specific_fields(self, page, detail_desc=None, detail_text_path=None, detail_text=None) -> dict:
        """Use parser to keep legacy JSON shape; prefer list-page hints when present."""
        fields = extract_cohouse_specific_fields(page, detail_text) or {}

        # Prefer hints parsed on the list page (detail_desc provided by pagination)
        if isinstance(detail_desc, dict):
            ut = detail_desc.get("unit_type")
            if ut:
                fields["unit_type"] = ut
            theme = detail_desc.get("theme")
            if theme:
                fields["theme"] = theme
            # subway '전역' → empty
            subway = detail_desc.get("subway_station")
            fields["subway_station"] = subway if (subway and subway.strip() and subway != "전역") else ""

        # Carry over cleaned detail text so JSON filter can mine additional info
        if detail_text:
            fields["text_content"] = detail_text
        return fields

    def _filter_json_fields(self, kv_pairs: dict, platform_specific_fields: dict) -> dict:
        """Keep only info that is not promoted to CSV columns."""
        return filter_json_fields_for_cohouse(kv_pairs, platform_specific_fields)

    def _download_images_platform_specific(
        self, page, output_dir: Path, house_name: str, index: int, unit_index: int = 0
    ) -> tuple[list[str], list[str]]:
        """Download listing images and floor plans into separate folders."""
        (output_dir / "floor_plans").mkdir(parents=True, exist_ok=True)

        floor_plan_paths = download_images_from(
            page, "img[src*='fileDown.do'][alt*='평면도']",
            page.url, output_dir / "floor_plans",
            filter_floor_plan=True, house_name=house_name, index=index
        )

        image_paths = []
        image_paths += download_images_from(
            page, ".slick-slide img[src*='fileDown.do']",
            page.url, output_dir / "images",
            filter_floor_plan=False, house_name=house_name, index=index
        )
        image_paths += download_images_from(
            page, ".flexbox-detail img[src*='fileDown.do']",
            page.url, output_dir / "images",
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

    # ---- Main crawl -------------------------------------------------
    def crawl(self):
        self.progress.update("[START] 공동체주택 Crawler")

        # Create run dir (KST) and standard subdirs (html/images/tables/texts/kv/attachments)
        self.output_dir = run_dir(self.platform_code)
        ensure_dirs(self.output_dir)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # 1) list → collect detail descriptors (내부에서 LIST 네비 1회 수행)
                details = collect_details_with_fallbacks(
                    page=page,
                    list_url=self.list_url,
                    progress=self.progress,
                    max_pages=0,
                )

                if not details:
                    self.progress.update("[INFO] Found 0 community housing items")
                    return

                self.progress.update(f"[INFO] Found {len(details)} community housing items")

                # 2) iterate details — Base handles HTML/text/kv/CSV 저장
                for i, (title, detail_desc) in enumerate(details):
                    try:
                        self.progress.update(f"[DETAIL] {i+1}/{len(details)}: {title[:50]}...")
                        self.process_detail_page(page, title, detail_desc, self.output_dir, i)

                        # 중간 저장 (5건마다)
                        if (i + 1) % 5 == 0:
                            self.save_progress(self.output_dir)

                    except Exception as e:
                        self.progress.update(f"[ERROR] 상세 페이지 처리 실패: {e}")
                        continue

                # 마지막 버퍼 플러시
                self.save_progress(self.output_dir)

                # 남은 버퍼가 있으면 최종 저장
                if self.rows:
                    self.save_results(self.output_dir)

            except Exception as e:
                self.progress.update(f"[ERROR] 크롤링 실패: {e}")
            finally:
                browser.close()

        self.progress.update(f"[COMPLETE] cohouse: {len(self.rows)} records")
