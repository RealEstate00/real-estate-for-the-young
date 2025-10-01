#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Intro Crawler - 플랫폼별 소개 페이지 크롤링
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
from datetime import datetime
from bs4 import BeautifulSoup
import re

class IntroCrawler:
    """플랫폼별 소개 페이지 크롤러"""
    
    def __init__(self):
        self.platforms = {
            "sohouse": {
                "url": "https://soco.seoul.go.kr/soHouse/main/contents.do?menuNo=300007",
                "title": "사회주택이란?",
                "platform": "sohouse"
            },
            "cohouse": {
                "url": "https://soco.seoul.go.kr/coHouse/main/contents.do?menuNo=200011",
                "title": "공동체주택 소개",
                "platform": "cohouse"
            },
            "youth": {
                "url": "https://soco.seoul.go.kr/youth/main/contents.do?menuNo=400012",
                "title": "청년안심주택 소개",
                "platform": "youth"
            }
        }
        
        self.financial_support_url = "https://soco.seoul.go.kr/youth/main/contents.do?menuNo=400021"
    
    async def crawl_all_intros(self):
        """모든 플랫폼 소개 페이지 크롤링"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            results = {}
            
            for platform, config in self.platforms.items():
                print(f"[INTRO] {platform} 소개 페이지 크롤링 시작...")
                try:
                    page = await context.new_page()
                    await page.goto(config["url"], wait_until="networkidle")
                    
                    # 페이지 내용 추출
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # 소개 내용 추출
                    intro_data = self._extract_intro_content(soup, platform)
                    results[platform] = intro_data
                    
                    await page.close()
                    print(f"[INTRO] {platform} 크롤링 완료")
                    
                except Exception as e:
                    print(f"[ERROR] {platform} 크롤링 실패: {e}")
                    results[platform] = {"error": str(e)}
            
            # 금융지원 안내 크롤링
            print(f"[INTRO] 금융지원 안내 크롤링 시작...")
            try:
                page = await context.new_page()
                await page.goto(self.financial_support_url, wait_until="networkidle")
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                financial_data = self._extract_financial_support(soup)
                results["financial_support"] = financial_data
                
                await page.close()
                print(f"[INTRO] 금융지원 안내 크롤링 완료")
                
            except Exception as e:
                print(f"[ERROR] 금융지원 안내 크롤링 실패: {e}")
                results["financial_support"] = {"error": str(e)}
            
            await browser.close()
            return results
    
    def _extract_intro_content(self, soup: BeautifulSoup, platform: str) -> dict:
        """소개 페이지 내용 추출"""
        intro_data = {
            "platform": platform,
            "title": "",
            "content": "",
            "url": self.platforms[platform]["url"],
            "crawled_at": datetime.now().isoformat()
        }
        
        try:
            # 제목 추출
            title_selectors = ["h1", "h2", ".subcont_tit", ".title"]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    intro_data["title"] = title_elem.get_text().strip()
                    break
            
            # 내용 추출
            content_selectors = [".subcont", ".content", ".main_content", "article"]
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 불필요한 태그 제거
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer']):
                        tag.decompose()
                    
                    content_text = content_elem.get_text(separator='\n', strip=True)
                    if content_text and len(content_text) > 100:  # 의미있는 내용만
                        intro_data["content"] = content_text
                        break
            
            # 공동체주택의 경우 유형 정보도 추출
            if platform == "cohouse":
                intro_data["types"] = self._extract_cohouse_types(soup)
                
        except Exception as e:
            print(f"[ERROR] {platform} 내용 추출 실패: {e}")
            intro_data["error"] = str(e)
        
        return intro_data
    
    def _extract_cohouse_types(self, soup: BeautifulSoup) -> list:
        """공동체주택 유형 정보 추출"""
        types = []
        
        try:
            # 유형 정보가 있는 컨테이너 찾기
            type_containers = soup.select(".box-gray a, .case a")
            
            for container in type_containers:
                type_info = {}
                
                # 이미지 정보
                img_elem = container.select_one("img")
                if img_elem:
                    type_info["image_url"] = img_elem.get("src", "")
                    type_info["image_alt"] = img_elem.get("alt", "")
                
                # 유형명
                name_elem = container.select_one(".img_name, span")
                if name_elem:
                    type_info["type_name"] = name_elem.get_text().strip()
                
                # 상세 URL
                type_info["detail_url"] = container.get("href", "")
                
                if type_info.get("type_name"):
                    types.append(type_info)
                    
        except Exception as e:
            print(f"[ERROR] 공동체주택 유형 추출 실패: {e}")
        
        return types
    
    def _extract_financial_support(self, soup: BeautifulSoup) -> dict:
        """금융지원 안내 정보 추출"""
        support_data = {
            "platform": "youth",
            "title": "금융지원 안내",
            "url": self.financial_support_url,
            "crawled_at": datetime.now().isoformat(),
            "support_programs": []
        }
        
        try:
            # 지원 프로그램 정보 추출
            # 실제 페이지 구조에 따라 수정 필요
            content_elem = soup.select_one(".subcont, .content, .main_content")
            if content_elem:
                support_data["content"] = content_elem.get_text(separator='\n', strip=True)
                
        except Exception as e:
            print(f"[ERROR] 금융지원 안내 추출 실패: {e}")
            support_data["error"] = str(e)
        
        return support_data
    
    def save_intro_data(self, results: dict, output_dir: Path):
        """소개 데이터 저장"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON 파일로 저장
        with open(output_dir / "platform_intros.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"[INTRO] 소개 데이터 저장 완료: {output_dir / 'platform_intros.json'}")

async def main():
    """메인 실행 함수"""
    crawler = IntroCrawler()
    results = await crawler.crawl_all_intros()
    
    # 결과 저장
    backend_dir = Path(__file__).parent.parent.parent.parent
    output_dir = backend_dir / "data" / "raw" / datetime.now().strftime("%Y-%m-%d")
    crawler.save_intro_data(results, output_dir)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())


