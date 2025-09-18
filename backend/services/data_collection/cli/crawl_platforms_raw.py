#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Main entry point for housing platform crawlers

import argparse
import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from ..crawlers.base import Progress, clean_today, run_dir
from ..crawlers.so import SoHouseCrawler
from ..crawlers.co import CoHouseCrawler
from ..crawlers.youth import YouthCrawler
from ..crawlers.sh import HappyHousingCrawler, SHAnnouncementCrawler
from ..crawlers.lh import LHAnnouncementCrawler
from ..crawlers.intro_crawler import IntroCrawler

def main():
    ap = argparse.ArgumentParser(description="Crawl RAW with images and intro pages")
    ap.add_argument("--max-youth-bbs", type=int, default=0,
                    help="Max BBS details to crawl for 'youth' (0 = all).")

    sub = ap.add_subparsers(dest="cmd", required=True)

    # Add subparsers for each platform (원본과 동일한 구조)
    platforms = [
        ("sohouse", "사회주택 목록->상세 RAW"),
        ("cohouse", "공동체주택 목록->상세 RAW"),
        ("youth", "청년안심 주택찾기+모집공고 통합 RAW"),
        ("intro", "플랫폼별 소개 페이지 크롤링"),
        ("happy", "SH 공급계획 행복주택 탭 RAW"),
        ("lh-ann", "LH 공고 목록 RAW"),
        ("sh-ann", "SH 공고 (all pages) RAW"),
    ]
    
    for platform, help_text in platforms:
        parser = sub.add_parser(platform, help=help_text)
        parser.add_argument("--fresh", action="store_true", help="Delete today's dir before crawling")
        if platform == "youth":
            parser.add_argument("--max-youth-bbs", type=int, default=0, help="Max BBS details to crawl for 'youth' (0 = all).")

    args = ap.parse_args()
    progress = Progress()

    if args.cmd == "sohouse":
        if args.fresh: 
            clean_today("sohouse")
            print("[FRESH] 기존 sohouse 데이터 삭제 완료")
        out_dir = run_dir("sohouse")
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = SoHouseCrawler(progress)
                crawler.crawl()
                crawler.save_results(out_dir)
                break
            except Exception as e:
                if "EPIPE" in str(e) or "Connection closed" in str(e) or "write EPIPE" in str(e):
                    print(f"[RETRY] EPIPE 오류 발생 (시도 {retry + 1}/{max_retries}): {e}")
                    if retry < max_retries - 1:
                        import time
                        time.sleep(10)  # 10초 대기 후 재시도
                        continue
                # 다른 오류는 즉시 재발생
                raise e
        
    elif args.cmd == "cohouse":
        if args.fresh: 
            clean_today("cohouse")
            print("[FRESH] 기존 cohouse 데이터 삭제 완료")
        out_dir = run_dir("cohouse")
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = CoHouseCrawler(progress)
                crawler.crawl()
                crawler.save_results(out_dir)
                break
            except Exception as e:
                if "EPIPE" in str(e) or "Connection closed" in str(e):
                    print(f"[RETRY] EPIPE 오류 발생 (시도 {retry + 1}/{max_retries}): {e}")
                    if retry < max_retries - 1:
                        import time
                        time.sleep(5)  # 5초 대기 후 재시도
                        continue
                raise e
        
    elif args.cmd == "youth":
        if args.fresh: clean_today("youth")
        out_dir = run_dir("youth")
        crawler = YouthCrawler(progress, max_bbs=getattr(args, 'max_youth_bbs', 0))
        crawler.crawl()
        crawler.save_results(out_dir)
        
    elif args.cmd == "happy":
        if args.fresh: clean_today("sh_plan_happy")
        out_dir = run_dir("sh_plan_happy")
        crawler = HappyHousingCrawler(progress)
        crawler.crawl()
        crawler.save_results(out_dir)
        
    elif args.cmd == "sh-ann":
        if args.fresh: clean_today("sh_ann")
        out_dir = run_dir("sh_ann")
        crawler = SHAnnouncementCrawler(progress)
        crawler.crawl()
        crawler.save_results(out_dir)
        
    elif args.cmd == "intro":
        if args.fresh: clean_today("intro")
        out_dir = run_dir("intro")
        crawler = IntroCrawler()
        import asyncio
        asyncio.run(crawler.crawl_all_intros())
        
    elif args.cmd == "lh-ann":
        if args.fresh: clean_today("lh_ann")
        out_dir = run_dir("lh_ann")
        crawler = LHAnnouncementCrawler(progress)
        crawler.crawl()
        crawler.save_results(out_dir)

if __name__ == "__main__":
    main()