#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Seoul Housing Data Crawlers
RTMS (Real Estate Transaction Management System) rent data + Land price data
"""

from __future__ import annotations
import re
import json
import csv
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import sync_playwright, Page

from crawl_platforms_raw import (
    Progress, robust_goto, safe_wait_any, get_page_html_stable,
    write_text, dump_first_table_to_csv, run_dir, append_csv,
    RAW_HEADER, sha256, KST, TODAY, make_record
)

class RTMSCrawler:
    """RTMS (Real Estate Transaction Management System) crawler for rent data"""
    
    BASE_URL = "https://land.seoul.go.kr/land/rtms/rtmsApartment.do"
    
    # Housing type tabs configuration
    TABS = {
        "apt": ("#rtmsApartment", "아파트"),
        "single": ("#rtmsSingleHouse", "단독/다가구"),
        "multi": ("#rtmsMultiHouse", "다세대/연립"),
        "offi": ("#rtmsOfficetel", "오피스텔"),
        "city": ("#rtmsCityHouse", "도시형 생활주택"),
    }
    
    def __init__(self, progress: Progress):
        self.progress = progress
    
    def switch_to_rent_mode(self, page: Page) -> None:
        """Switch to rent mode (전월세 tab)"""
        try:
            btn = page.locator("a:has-text('전월세'), a[title*='전월세']").first
            if btn.count():
                btn.click()
                self.progress.update("[RTMS] Switched to rent mode")
                page.wait_for_load_state("domcontentloaded")
                safe_wait_any(page, ["#selectJWGubun"], timeout=8000)
                return
        except Exception:
            pass
        
        # Fallback: call JavaScript function
        try:
            page.evaluate("() => { if (typeof fn_tab === 'function') fn_tab('rentApartment'); }")
            self.progress.update("[RTMS] Switched to rent mode (JS)")
            page.wait_for_load_state("domcontentloaded")
            safe_wait_any(page, ["#selectJWGubun"], timeout=8000)
        except Exception:
            self.progress.update("[RTMS] Warning: rent mode not confirmed")
    
    def select_option(self, page: Page, selector: str, value: str) -> None:
        """Select dropdown option"""
        page.wait_for_selector(f"select{selector}", timeout=15000)
        page.select_option(f"select{selector}", value=value)
        self.progress.update(f"[RTMS] Selected {selector}={value}")
        page.wait_for_timeout(200)
    
    def click_search(self, page: Page) -> None:
        """Click search button and wait for results"""
        page.click("#search")
        self.progress.update("[RTMS] Clicked search")
        safe_wait_any(page, ["table"], timeout=20000)
        page.wait_for_load_state("domcontentloaded")
    
    def get_dropdown_options(self, page: Page, selector: str) -> List[Tuple[str, str]]:
        """Get dropdown options as (value, label) pairs"""
        page.wait_for_selector(selector, timeout=15000)
        return page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (!el) return [];
                return Array.from(el.options).map(o => [
                    String(o.value || '').trim(), 
                    String(o.text || '').trim()
                ]);
            }""",
            selector,
        ) or []
    
    def get_filtered_values(self, page: Page, selector: str, filter_func=None) -> List[str]:
        """Get filtered dropdown values"""
        options = self.get_dropdown_options(page, selector)
        values = [v for v, _ in options if v]
        if filter_func:
            values = [v for v in values if filter_func(v)]
        return values
    
    def get_sigungu_codes(self, page: Page) -> List[str]:
        """Get all district codes (excluding placeholder)"""
        return self.get_filtered_values(
            page, "select#selectSigungu", 
            lambda v: v != "11000"  # Exclude placeholder
        )
    
    def get_years(self, page: Page) -> List[str]:
        """Get available years from dropdown"""
        # Try common year selectors
        candidates = ["select#selectYear", "select[name='selectYear']", "select[id*='Year']"]
        for sel in candidates:
            try:
                if page.locator(sel).count():
                    pairs = self.get_dropdown_options(page, sel)
                    years = []
                    for v, t in pairs:
                        text = f"{v} {t}".strip()
                        match = re.search(r"\b(19|20)\d{2}\b", text)
                        if match:
                            years.append(match.group(0))
                    if years:
                        return sorted(set(years))
            except Exception:
                continue
        
        # Fallback: scan all selects for years
        try:
            found = page.evaluate("""
                () => {
                    const years = new Set();
                    const sels = Array.from(document.querySelectorAll('select'));
                    for (const sel of sels) {
                        for (const opt of Array.from(sel.options || [])) {
                            const s = String((opt.value || '') + ' ' + (opt.text || '')).trim();
                            const m = s.match(/\\b(19|20)\\d{2}\\b/);
                            if (m) years.add(m[0]);
                        }
                    }
                    return Array.from(years);
                }
            """)
            if found and isinstance(found, list):
                return sorted(set(str(y) for y in found))
        except Exception:
            pass
        return []
    
    def get_quarters(self, page: Page) -> List[str]:
        """Get available quarters"""
        return self.get_filtered_values(
            page, "select#selectBoongi", 
            lambda v: v.isdigit()
        )
    
    def get_rent_types(self, page: Page) -> List[str]:
        """Get available rent types (전세/월세)"""
        return self.get_filtered_values(
            page, "select#selectJWGubun", 
            lambda v: v.isdigit()
        )
    
    def refresh_dong_codes(self, page: Page, sigungu_code: str) -> List[str]:
        """Refresh and get dong codes for selected district"""
        self.select_option(page, "#selectSigungu", sigungu_code)
        
        # Wait for options to load
        for _ in range(10):
            page.wait_for_timeout(300)
            opts = self.get_dropdown_options(page, "select#selectBjdong")
            if len(opts) > 0:
                break
        
        return [v for v, _ in self.get_dropdown_options(page, "select#selectBjdong") if v]
    
    def extract_table_data(self, page: Page, table_index: int = 2) -> List[Dict]:
        """Extract structured data from RTMS table"""
        rows_data = []
        
        try:
            # Get table by index (table 3 contains the data)
            all_tables = page.locator("table")
            if table_index >= all_tables.count():
                return rows_data
            
            table = all_tables.nth(table_index)
            rows = table.locator("tr")
            
            if rows.count() < 2:  # Need header + data
                return rows_data
            
            # Extract headers
            headers = []
            first_row = rows.first
            header_cells = first_row.locator("th, td")
            for i in range(header_cells.count()):
                header_text = header_cells.nth(i).inner_text().strip()
                headers.append(header_text)
            
            # Extract data rows
            for i in range(1, rows.count()):
                row = rows.nth(i)
                cells = row.locator("td")
                
                if cells.count() < len(headers):
                    continue
                
                # Build row data
                row_data = {}
                for j in range(min(cells.count(), len(headers))):
                    cell_text = cells.nth(j).inner_text().strip()
                    header = headers[j] if j < len(headers) else f"col_{j}"
                    row_data[header] = cell_text
                
                # Extract key fields
                extracted = self._parse_row_data(row_data)
                rows_data.append(extracted)
        
        except Exception as e:
            self.progress.update(f"[RTMS] Error extracting table: {e}")
        
        return rows_data
    
    def _parse_row_data(self, row_data: Dict) -> Dict:
        """Parse and clean row data"""
        # Extract fields (handle line breaks in headers)
        extracted = {
            "complex_name": row_data.get("단지\n[준공년도]", row_data.get("단지[준공년도]", "")),
            "address": row_data.get("지번", ""),
            "area": row_data.get("전용\n면적", row_data.get("전용면적", "")),
            "rent_price": row_data.get("전월세가", ""),
            "market_price": row_data.get("매물\n시세", row_data.get("매물시세", "")),
            "contract_date": row_data.get("계약일(계약구분)", ""),
            "deposit": row_data.get("보증금", ""),
            "floor": row_data.get("층", ""),
            "raw_data": row_data
        }
        
        # Clean data
        for key in ["complex_name", "address", "area", "rent_price", "market_price", "contract_date", "deposit", "floor"]:
            if isinstance(extracted[key], str):
                extracted[key] = extracted[key].replace("\n", " ").strip()
        
        # Parse complex name and year
        if extracted["complex_name"]:
            parts = extracted["complex_name"].split("[")
            if len(parts) > 1:
                name_part = parts[0].strip()
                year_part = "[" + parts[1] if len(parts) > 1 else ""
                
                if name_part.startswith("(") and name_part.endswith(")"):
                    # Lot number only
                    extracted["complex_name"] = name_part
                    extracted["built_year"] = year_part
                else:
                    # Complex name with year
                    extracted["complex_name"] = name_part
                    extracted["built_year"] = year_part
            else:
                extracted["built_year"] = ""
        
        return extracted
    
    def save_csv(self, data: List[Dict], out_dir: Path, base_name: str) -> Optional[Path]:
        """Save data as CSV file"""
        if not data:
            return None
        
        try:
            # Generate filename
            data_hash = sha256(str(data[:5]))[:4]
            csv_path = out_dir / "tables" / f"{base_name}_p{data_hash}.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Define headers
            headers = [
                "complex_name", "built_year", "address", "area", "rent_price", 
                "market_price", "contract_date", "deposit", "floor"
            ]
            
            # Write CSV
            with csv_path.open("w", newline="", encoding="utf-8") as fp:
                writer = csv.DictWriter(fp, fieldnames=headers)
                writer.writeheader()
                
                for record in data:
                    csv_record = {}
                    for header in headers:
                        value = record.get(header, "")
                        if isinstance(value, str):
                            value = value.replace("\n", " ").strip()
                        csv_record[header] = value
                    writer.writerow(csv_record)
            
            self.progress.update(f"[RTMS] Saved {len(data)} records to {csv_path.name}")
            return csv_path
            
        except Exception as e:
            self.progress.update(f"[RTMS] CSV save failed: {e}")
            return None
    
    def save_excel(self, page: Page, out_dir: Path, base_name: str) -> Optional[Path]:
        """Download Excel file if available"""
        downloads_dir = out_dir / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        
        if not page.locator("#excel").count():
            return None
        
        try:
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#excel")
            dl = dl_info.value
            
            # Use better filename if suggested name is empty
            if not dl.suggested_filename or dl.suggested_filename == "_":
                dest = downloads_dir / f"{base_name}.xls"
            else:
                dest = downloads_dir / dl.suggested_filename
            
            if dest.exists() and dest.stat().st_size > 0:
                dest.unlink()
            dl.save_as(str(dest))
            
            self.progress.update(f"[RTMS] Excel saved: {dest.name}")
            return dest
            
        except Exception as e:
            self.progress.update(f"[RTMS] Excel download failed: {e}")
            return None
    
    def crawl_all(self, tabs: Optional[List[str]] = None, 
                  year_from: Optional[str] = None, 
                  year_to: Optional[str] = None, 
                  throttle_ms: int = 150) -> None:
        """Crawl all RTMS rent data"""
        base_dir = run_dir("rtms_rent")
        tabs = tabs or list(self.TABS.keys())
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            
            # Initialize page
            robust_goto(page, self.BASE_URL, self.progress, "RTMS-ALL")
            self.switch_to_rent_mode(page)
            self.select_option(page, "#selectGubun", "1")  # 분기
            
            # Wait for UI to load
            safe_wait_any(page, ["select#selectBoongi", "select#selectJWGubun"], timeout=8000)
            page.wait_for_timeout(500)
            
            # Get available options
            years = self.get_years(page)
            quarters = self.get_quarters(page)
            rent_types = self.get_rent_types(page)
            
            # Fallback for years if not found
            if not years:
                if year_from or year_to:
                    yf = int(year_from) if year_from else 2006
                    yt = int(year_to) if year_to else datetime.now(KST).year
                    years = [str(y) for y in range(min(yf, yt), max(yf, yt) + 1)]
                    self.progress.update(f"[RTMS] Years from CLI: {years[0]}..{years[-1]}")
                else:
                    y0, y1 = 2006, datetime.now(KST).year
                    years = [str(y) for y in range(y0, y1 + 1)]
                    self.progress.update(f"[RTMS] Default years: {y0}..{y1}")
            
            if not (years and quarters and rent_types):
                raise RuntimeError("Required dropdowns not found")
            
            # Filter years by CLI args
            if year_from and year_from in years:
                years = [y for y in years if y >= year_from]
            if year_to and year_to in years:
                years = [y for y in years if y <= year_to]
            
            self.progress.update(f"[RTMS] Processing: {len(years)} years, {len(quarters)} quarters, {len(rent_types)} rent types")
            
            # Get all districts
            sigungu_codes = self.get_sigungu_codes(page)
            total_jobs = 0
            
            # Process each combination
            for tab in tabs:
                css, tab_name = self.TABS.get(tab, self.TABS["apt"])
                try:
                    if page.locator(css).count():
                        page.click(f"{css} a")
                        page.wait_for_load_state("domcontentloaded")
                        self.switch_to_rent_mode(page)
                        self.select_option(page, "#selectGubun", "1")
                        safe_wait_any(page, ["select"], timeout=8000)
                        page.wait_for_timeout(200)
                        self.progress.update(f"[RTMS] Tab: {tab_name}")
                except Exception as e:
                    self.progress.update(f"[RTMS] Tab {tab} failed: {e}")
                    continue
                
                for sigungu in sigungu_codes:
                    # Get dong codes for this district
                    dong_codes = self.refresh_dong_codes(page, sigungu)
                    dong_values = [""] + dong_codes  # Include "ALL"
                    
                    for dong in dong_values:
                        for year in years:
                            for quarter in quarters:
                                for rent_type in rent_types:
                                    total_jobs += 1
                                    self.progress.update(f"[JOB] {tab} {sigungu} {dong or 'ALL'} {year}Q{quarter} {rent_type}")
                                    
                                    try:
                                        # Set search parameters
                                        if sigungu:
                                            self.select_option(page, "#selectSigungu", sigungu)
                                            page.wait_for_timeout(200)
                                        
                                        if dong:
                                            self.select_option(page, "#selectBjdong", dong)
                                        else:
                                            # Reset to ALL
                                            try:
                                                page.select_option("select#selectBjdong", value="")
                                            except Exception:
                                                pass
                                        
                                        self.select_option(page, "#selectGubun", "1")
                                        self.select_option(page, "#selectYear", year)
                                        self.select_option(page, "#selectBoongi", quarter)
                                        self.select_option(page, "#selectJWGubun", rent_type)
                                        
                                        # Search and save
                                        self.click_search(page)
                                        
                                        # Save HTML snapshot
                                        record_id = sha256(f"rtms|{tab}|{sigungu}|{dong}|{year}|{quarter}|{rent_type}")
                                        html_path = base_dir / "html" / f"{record_id}.html"
                                        write_text(html_path, get_page_html_stable(page, self.progress, "rtms_all"))
                                        
                                        # Save data
                                        base_name = f"rtms_{tab}_{sigungu}_{dong or 'all'}_{year}Q{quarter}_jw{rent_type}"
                                        
                                        # Extract and save structured data
                                        data = self.extract_table_data(page)
                                        if data:
                                            # Save JSON
                                            json_path = base_dir / "tables" / f"{base_name}.json"
                                            json_path.parent.mkdir(parents=True, exist_ok=True)
                                            with json_path.open("w", encoding="utf-8") as f:
                                                json.dump(data, f, ensure_ascii=False, indent=2)
                                            
                                            # Save CSV
                                            self.save_csv(data, base_dir, base_name)
                                        
                                        # Save Excel
                                        self.save_excel(page, base_dir, base_name)
                                        
                                        # Add to manifest
                                        append_csv(
                                            base_dir / "raw.csv", RAW_HEADER,
                                            [make_record(
                                                platform="rtms_rent_all", platform_id="",
                                                list_url=self.BASE_URL, detail_url=page.url,
                                                house_name="", address="",
                                                platform_intro=f"{tab_name} rent all",
                                                html_path=str(html_path), image_paths=[],
                                                extras={"sigungu": sigungu, "bjdong": dong, "year": year, "quarter": quarter, "jw_gubun": rent_type}
                                            )]
                                        )
                                        
                                    except Exception as e:
                                        self.progress.update(f"[SKIP] Error: {e}")
                                    finally:
                                        page.wait_for_timeout(throttle_ms)
            
            browser.close()
        
        self.progress.update(f"[DONE] RTMS crawl completed: {total_jobs} jobs")

class LandPriceCrawler:
    """Land price data crawler for Seoul public data"""
    
    BASE_URL = "https://data.seoul.go.kr/dataList/OA-1180/F/1/datasetView.do"
    
    def __init__(self, progress: Progress):
        self.progress = progress
    
    def toggle_all_files(self, page: Page) -> None:
        """Open '전체 파일보기' panel"""
        selectors = [
            "span:has-text('전체 파일보기')",
            "a:has-text('전체 파일보기')",
            "button:has-text('전체 파일보기')",
            "[title*='전체 파일보기']",
            "text='전체 파일보기'"
        ]
        
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if btn.count() > 0:
                    btn.click()
                    page.wait_for_timeout(400)
                    self.progress.update(f"[LANDPRICE] Showed all files ({selector})")
                    return
            except Exception:
                continue
        
        self.progress.update("[LANDPRICE] Warning: toggle button not found")
    
    def collect_download_links(self, page: Page) -> List[Dict]:
        """Collect download file links"""
        selectors = [
            "a[onclick*='downloadFile(']",
            "a[href*='downloadFile(']",
            "a[href*='javascript:downloadFile']"
        ]
        
        links = []
        for selector in selectors:
            try:
                anchors = page.locator(selector)
                for i in range(anchors.count()):
                    anchor = anchors.nth(i)
                    title = (anchor.get_attribute("title") or anchor.inner_text() or "").strip()
                    onclick = anchor.get_attribute("onclick") or ""
                    href = anchor.get_attribute("href") or ""
                    
                    # Extract file ID
                    match = re.search(r"downloadFile\('([^']+)'\)", onclick + href)
                    if match:
                        links.append({"id": match.group(1), "title": title})
            except Exception:
                continue
        
        return links
    
    def download_file(self, page: Page, file_id: str, out_dir: Path) -> Optional[Path]:
        """Download file by ID"""
        out_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with page.expect_download(timeout=60000) as dl_info:
                page.evaluate(f"downloadFile('{file_id}')")
            dl = dl_info.value
            dest = out_dir / dl.suggested_filename
            
            if dest.exists() and dest.stat().st_size > 0:
                dest.unlink()
            dl.save_as(str(dest))
            return dest
            
        except Exception as e:
            self.progress.update(f"[LANDPRICE] Download failed for {file_id}: {e}")
            return None
    
    def extract_zips(self, base_dir: Path) -> None:
        """Extract all ZIP files and convert CSV encoding"""
        downloads_dir = base_dir / "downloads"
        extracted_dir = base_dir / "extracted_csv"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        
        # Read manifest
        manifest_path = base_dir / "raw.csv"
        if not manifest_path.exists():
            self.progress.update("[EXTRACT] No manifest file found")
            return
        
        extracted_files = []
        total_csv_files = 0
        
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    zip_path = row.get("saved_path", "")
                    if not zip_path or row.get("error"):
                        continue
                    
                    zip_file = Path(zip_path)
                    if not zip_file.exists():
                        self.progress.update(f"[EXTRACT] ZIP not found: {zip_file.name}")
                        continue
                    
                    self.progress.update(f"[EXTRACT] Processing {zip_file.name}")
                    
                    try:
                        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                            csv_files = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]
                            
                            if not csv_files:
                                self.progress.update(f"[EXTRACT] No CSV in {zip_file.name}")
                                continue
                            
                            for csv_file in csv_files:
                                try:
                                    # Extract to temp
                                    zip_ref.extract(csv_file, downloads_dir / "temp")
                                    temp_path = downloads_dir / "temp" / csv_file
                                    
                                    # Create unique filename
                                    base_name = zip_file.stem
                                    csv_name = Path(csv_file).name
                                    unique_name = f"{base_name}_{csv_name}"
                                    final_path = extracted_dir / unique_name
                                    
                                    # Convert encoding (CP949 -> UTF-8)
                                    try:
                                        with temp_path.open("r", encoding="cp949") as f:
                                            content = f.read()
                                        with final_path.open("w", encoding="utf-8") as f:
                                            f.write(content)
                                        self.progress.update(f"[EXTRACT] Converted {unique_name} (CP949->UTF-8)")
                                    except UnicodeDecodeError:
                                        # Try UTF-8
                                        try:
                                            with temp_path.open("r", encoding="utf-8") as f:
                                                content = f.read()
                                            with final_path.open("w", encoding="utf-8") as f:
                                                f.write(content)
                                            self.progress.update(f"[EXTRACT] Extracted {unique_name} (UTF-8)")
                                        except UnicodeDecodeError:
                                            # Binary copy
                                            shutil.copy2(temp_path, final_path)
                                            self.progress.update(f"[EXTRACT] Extracted {unique_name} (binary)")
                                    
                                    extracted_files.append({
                                        "zip_file": zip_file.name,
                                        "csv_file": csv_name,
                                        "extracted_path": str(final_path),
                                        "extracted_at": datetime.now(KST).isoformat()
                                    })
                                    total_csv_files += 1
                                    
                                except Exception as e:
                                    self.progress.update(f"[EXTRACT] Error extracting {csv_file}: {e}")
                    
                    except Exception as e:
                        self.progress.update(f"[EXTRACT] Error processing {zip_file.name}: {e}")
            
            # Clean up temp
            temp_dir = downloads_dir / "temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            # Save extraction manifest
            if extracted_files:
                manifest_path = base_dir / "extraction_manifest.csv"
                with manifest_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["zip_file", "csv_file", "extracted_path", "extracted_at"])
                    writer.writeheader()
                    for file_info in extracted_files:
                        writer.writerow(file_info)
                
                self.progress.update(f"[EXTRACT] Completed: {total_csv_files} CSV files extracted")
                self.progress.update(f"[EXTRACT] Manifest saved: {manifest_path}")
            else:
                self.progress.update("[EXTRACT] No CSV files extracted")
                
        except Exception as e:
            self.progress.update(f"[EXTRACT] Error: {e}")
    
    def crawl_files(self) -> None:
        """Download all land price ZIP files"""
        base_dir = run_dir("landprice")
        downloads_dir = base_dir / "downloads"
        rows = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            
            # Navigate and show all files
            robust_goto(page, self.BASE_URL, self.progress, "LANDPRICE")
            safe_wait_any(page, ["body", "#contents", "article"], timeout=15000)
            self.toggle_all_files(page)
            
            # Collect download links
            items = self.collect_download_links(page)
            
            # Download each file
            for item in items:
                try:
                    path = self.download_file(page, item["id"], downloads_dir)
                    rows.append({
                        "file_id": item["id"],
                        "title": item["title"],
                        "saved_path": str(path) if path else "",
                        "error": "",
                        "crawl_date": TODAY,
                        "crawled_at": datetime.now(KST).isoformat(),
                    })
                    self.progress.update(f"[LANDPRICE] Saved {Path(path).name if path else 'failed'}")
                except Exception as e:
                    rows.append({
                        "file_id": item["id"],
                        "title": item["title"],
                        "saved_path": "",
                        "error": str(e),
                        "crawl_date": TODAY,
                        "crawled_at": datetime.now(KST).isoformat(),
                    })
            
            # Save manifest
            if rows:
                append_csv(
                    base_dir / "raw.csv",
                    ["file_id", "title", "saved_path", "error", "crawl_date", "crawled_at"],
                    rows,
                )
            
            browser.close()
        
        self.progress.update(f"[DONE] Land price files: {len(rows)}")

# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seoul Housing Data Crawlers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # RTMS crawler
    rtms_parser = subparsers.add_parser("rtms_all", help="RTMS rent data crawler")
    rtms_parser.add_argument("--tabs", nargs="*", help="Housing types to crawl")
    rtms_parser.add_argument("--from", dest="year_from", help="Start year")
    rtms_parser.add_argument("--to", dest="year_to", help="End year")
    rtms_parser.add_argument("--throttle", type=int, default=150, help="Delay between requests (ms)")
    
    # Land price crawler
    subparsers.add_parser("landprice_files", help="Download land price ZIP files")
    subparsers.add_parser("landprice_extract", help="Extract CSV from downloaded ZIPs")
    
    args = parser.parse_args()
    progress = Progress()
    
    if args.command == "rtms_all":
        crawler = RTMSCrawler(progress)
        crawler.crawl_all(
            tabs=args.tabs,
            year_from=args.year_from,
            year_to=args.year_to,
            throttle_ms=args.throttle
        )
    elif args.command == "landprice_files":
        crawler = LandPriceCrawler(progress)
        crawler.crawl_files()
        crawler.extract_zips(run_dir("landprice"))
    elif args.command == "landprice_extract":
        crawler = LandPriceCrawler(progress)
        crawler.extract_zips(run_dir("landprice"))
