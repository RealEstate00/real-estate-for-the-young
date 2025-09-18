#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Happy Housing (행복주택) Crawler

from pathlib import Path
from playwright.sync_api import sync_playwright

from .base import (
    BaseCrawler, Progress, robust_goto, get_page_html_stable, 
    open_detail, download_images_from, download_attachments_from_html,
    make_record, write_text, ensure_dirs, platform_fixed_id, sanity_check_address, run_dir
)
from ..parsers.parsers import (
    parse_house_name, parse_address_strict, parse_occupancy_type, 
    parse_eligibility, extract_platform_intro_text, filter_sh_announcement_title
)
from .pagination import collect_details_with_fallbacks

class HappyHousingCrawler(BaseCrawler):
    """행복주택 크롤러"""
    
    def __init__(self, progress: Progress):
        super().__init__(progress)
        self.list_url = "https://www.happyhouse.go.kr/happy/portal/board/list.do?boardId=notice"
        self.platform_code = "sh_happy"
    
    def crawl(self):
        """행복주택 크롤링 실행"""
        self.progress.update("[START] Happy Housing Crawler")
        
        # 오늘 날짜 폴더 생성
        self.output_dir = run_dir(self.platform_code) 
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 메인 페이지로 이동
                robust_goto(page, self.list_url, self.progress, "LIST")
                
                # 상세 페이지 링크 수집
                details = collect_details_with_fallbacks(
                    page=page,
                    list_url=self.list_url,
                    progress=self.progress
                )
                
                # SH 공고 필터링 적용
                filtered_details = []
                for title, detail_desc in details:
                    if filter_sh_announcement_title(title):
                        filtered_details.append((title, detail_desc))
                
                self.progress.update(f"[INFO] Found {len(details)} total items, {len(filtered_details)} after SH filtering")
                details = filtered_details
                
                # 각 상세 페이지 크롤링
                for i, (title, detail_desc) in enumerate(details):
                    try:
                        self.progress.update(f"[DETAIL] {i+1}/{len(details)}: {title[:50]}")
                        
                        # 상세 페이지 열기
                        open_detail(page, self.list_url, detail_desc, self.progress)
                        
                        # HTML 저장
                        html = get_page_html_stable(page, self.progress, "detail")
                        html_path = str(output_dir / "html" / f"detail_{i:04d}.html")
                        write_text(Path(html_path), html)
                        
                        # 데이터 추출
                        house_name = parse_house_name(page, title)
                        address = parse_address_strict(page)
                        building_type = parse_occupancy_type(page)
                        eligibility = parse_eligibility(page)
                        
                        # 이미지 다운로드
                        image_paths = download_images_from(
                            page, "img", self.list_url, 
                            output_dir / "images"
                        )
                        
                        # 첨부파일 다운로드
                        attachment_paths = download_attachments_from_html(
                            html, self.list_url, page.context, 
                            output_dir / "attachments"
                        )
                        
                        # 레코드 생성
                        extras = {
                            "building_type": building_type,
                            "eligibility": eligibility,
                            "attachments": attachment_paths
                        }
                        
                        record = make_record(
                            platform=self.platform_code,
                            platform_id=str(platform_fixed_id(self.platform_code) or ""),
                            list_url=self.list_url,
                            detail_url=page.url,
                            house_name=house_name,
                            address=address,
                            platform_intro="",
                            html_path=html_path,
                            image_paths=image_paths,
                            extras=extras
                        )
                        
                        sanity_check_address(record)
                        self.rows.append(record)
                        
                    except Exception as e:
                        self.progress.update(f"[ERROR] Detail {i+1}: {e}")
                        continue
                        
            finally:
                browser.close()
                # 크롤링이 중단되어도 중간에 저장된 데이터 보존
                if self.rows:
                    self.save_results(output_dir)
        
        # 최종 결과 저장 (정상 완료 시)
        if self.rows:
            self.save_results(output_dir)
        
        self.progress.update(f"[COMPLETE] Happy Housing: {len(self.rows)} records")

class SHAnnouncementCrawler(BaseCrawler):
    """SH 공고 크롤러"""
    
    def __init__(self, progress: Progress):
        super().__init__(progress)
        self.list_url = "https://www.sh.co.kr/portal/board/list.do?boardId=notice"
        self.platform_code = "sh_ann"
    
    def crawl(self):
        """SH 공고 크롤링 실행"""
        self.progress.update("[START] SH Announcement Crawler")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 메인 페이지로 이동
                robust_goto(page, self.list_url, self.progress, "LIST")
                
                # 상세 페이지 링크 수집
                details = collect_details_with_fallbacks(
                    page=page,
                    list_url=self.list_url,
                    progress=self.progress
                )
                
                # SH 공고 필터링 적용
                filtered_details = []
                for title, detail_desc in details:
                    if filter_sh_announcement_title(title):
                        filtered_details.append((title, detail_desc))
                
                self.progress.update(f"[INFO] Found {len(details)} total items, {len(filtered_details)} after SH filtering")
                details = filtered_details
                
                # 각 상세 페이지 크롤링
                for i, (title, detail_desc) in enumerate(details):
                    try:
                        self.progress.update(f"[DETAIL] {i+1}/{len(details)}: {title[:50]}")
                        
                        # 상세 페이지 열기
                        open_detail(page, self.list_url, detail_desc, self.progress)
                        
                        # HTML 저장
                        html = get_page_html_stable(page, self.progress, "detail")
                        html_path = str(output_dir / "html" / f"detail_{i:04d}.html")
                        write_text(Path(html_path), html)
                        
                        # 데이터 추출
                        house_name = parse_house_name(page, title)
                        address = parse_address_strict(page)
                        building_type = parse_occupancy_type(page)
                        eligibility = parse_eligibility(page)
                        
                        # 이미지 다운로드
                        image_paths = download_images_from(
                            page, "img", self.list_url, 
                            output_dir / "images"
                        )
                        
                        # 첨부파일 다운로드
                        attachment_paths = download_attachments_from_html(
                            html, self.list_url, page.context, 
                            output_dir / "attachments"
                        )
                        
                        # 레코드 생성
                        extras = {
                            "building_type": building_type,
                            "eligibility": eligibility,
                            "attachments": attachment_paths
                        }
                        
                        record = make_record(
                            platform=self.platform_code,
                            platform_id=str(platform_fixed_id(self.platform_code) or ""),
                            list_url=self.list_url,
                            detail_url=page.url,
                            house_name=house_name,
                            address=address,
                            platform_intro="",
                            html_path=html_path,
                            image_paths=image_paths,
                            extras=extras
                        )
                        
                        sanity_check_address(record)
                        self.rows.append(record)
                        
                    except Exception as e:
                        self.progress.update(f"[ERROR] Detail {i+1}: {e}")
                        continue
                        
            finally:
                browser.close()
                # 크롤링이 중단되어도 중간에 저장된 데이터 보존
                if self.rows:
                    self.save_results(output_dir)
        
        # 최종 결과 저장 (정상 완료 시)
        if self.rows:
            self.save_results(output_dir)
        
        self.progress.update(f"[COMPLETE] SH Announcement: {len(self.rows)} records")
    
    def _download_images_platform_specific(self, page, output_dir: Path, house_name: str, index: int) -> tuple[list[str], list[str]]:
        """행복주택 이미지 다운로드 로직 (기본 로직 + 평면도 분리)"""
        image_paths = []
        floor_plan_paths = []
        
        # 기존 로직과 완전히 동일한 이미지 다운로드
        image_paths += self._download_images_from(page, "div.detail-box img", page.url, output_dir / "images")
        image_paths += self._download_images_from(page, "ul.detail-list img", page.url, output_dir / "images")
        image_paths += self._download_images_from(page, "img[src$='.jpg'], img[src$='.png'], img[src$='.gif'], img[src$='.jpeg']", page.url, output_dir / "images")
        image_paths += self._download_images_from(page, "img[src*='upload'], img[src*='image'], img[src*='photo']", page.url, output_dir / "images")
        
        # 추가: 평면도 분리 (새로운 기능)
        from .base import download_images_from
        floor_plans = download_images_from(page, "img[alt*='평면도']", page.url, output_dir / "floor_plans", 
                                         filter_floor_plan=True, house_name=house_name, index=index)
        floor_plan_paths.extend(floor_plans)
        
        # floor_plans 디렉토리 생성
        (output_dir / "floor_plans").mkdir(parents=True, exist_ok=True)
        
        return image_paths, floor_plan_paths