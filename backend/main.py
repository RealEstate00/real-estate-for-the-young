#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
서울주택도시공사 주택지원 봇 - 통합 실행 스크립트
크롤링, 데이터 분석, 변환을 모두 처리
"""

import argparse
import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# Add data_collection/crawler directory to path for imports
sys.path.append(str(Path(__file__).parent / "data_collection" / "crawler"))

from services.crawlers.base import Progress
# 저장 경로 관련 함수들 import
from utils.helpers import clean_today, clean_all_platform_data, run_dir
from services.crawlers.so_co import SoHouseCrawler, CoHouseCrawler
from services.crawlers.youth import YouthCrawler
from services.crawlers.sh import HappyHousingCrawler, SHAnnouncementCrawler
from services.crawlers.lh import LHAnnouncementCrawler
from services.parsers.data_analyzer import RawDataAnalyzer


def crawl_platform(platform: str, fresh: bool = False, max_youth_bbs: int = 0):
    """플랫폼별 크롤링 실행"""
    progress = Progress()
    
    if platform == "sohouse":
        # sohouse 크롤링 시 저장 경로 설정
        if fresh: 
            clean_all_platform_data("sohouse")  # 기존 sohouse 데이터 삭제 (data/raw 폴더)
            print("[FRESH] 기존 sohouse 데이터 삭제 완료")
        out_dir = run_dir("sohouse")  # data/raw/YYYY-MM-DD/sohouse/ 디렉토리 생성
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = SoHouseCrawler(progress)
                crawler.crawl()
                break
            except BrokenPipeError as e:
                if retry < max_retries - 1:
                    print(f"[RETRY {retry + 1}] EPIPE 오류 재시도: {e}")
                    continue
                else:
                    raise e
                    
    elif platform == "cohouse":
        # cohouse 크롤링 시 저장 경로 설정
        if fresh: 
            clean_all_platform_data("cohouse")  # 기존 cohouse 데이터 삭제 (data/raw 폴더)
            print("[FRESH] 기존 cohouse 데이터 삭제 완료")
        out_dir = run_dir("cohouse")  # data/raw/YYYY-MM-DD/cohouse/ 디렉토리 생성
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = CoHouseCrawler(progress)
                crawler.crawl()
                break
            except BrokenPipeError as e:
                if retry < max_retries - 1:
                    print(f"[RETRY {retry + 1}] EPIPE 오류 재시도: {e}")
                    continue
                else:
                    raise e
                    
    elif platform == "youth":
        # youth 크롤링 시 저장 경로 설정
        if fresh: 
            clean_today("youth")  # 오늘 날짜의 youth 데이터만 삭제 (data/raw 폴더)
            print("[FRESH] 기존 youth 데이터 삭제 완료")
        out_dir = run_dir("youth")  # data/raw/YYYY-MM-DD/youth/ 디렉토리 생성
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = YouthCrawler(progress)
                crawler.crawl()
                break
            except BrokenPipeError as e:
                if retry < max_retries - 1:
                    print(f"[RETRY {retry + 1}] EPIPE 오류 재시도: {e}")
                    continue
                else:
                    raise e
                    
    elif platform == "happy":
        # happy 크롤링 시 저장 경로 설정
        if fresh: 
            clean_today("happy")  # 오늘 날짜의 happy 데이터만 삭제 (data/raw 폴더)
            print("[FRESH] 기존 happy 데이터 삭제 완료")
        out_dir = run_dir("happy")  # data/raw/YYYY-MM-DD/happy/ 디렉토리 생성
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = HappyHousingCrawler(progress)
                crawler.crawl()
                break
            except BrokenPipeError as e:
                if retry < max_retries - 1:
                    print(f"[RETRY {retry + 1}] EPIPE 오류 재시도: {e}")
                    continue
                else:
                    raise e
                    
    elif platform == "lh-ann":
        # lh-ann 크롤링 시 저장 경로 설정
        if fresh: 
            clean_today("lh-ann")  # 오늘 날짜의 lh-ann 데이터만 삭제 (data/raw 폴더)
            print("[FRESH] 기존 lh-ann 데이터 삭제 완료")
        out_dir = run_dir("lh-ann")  # data/raw/YYYY-MM-DD/lh-ann/ 디렉토리 생성
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = LHAnnouncementCrawler(progress)
                crawler.crawl()
                break
            except BrokenPipeError as e:
                if retry < max_retries - 1:
                    print(f"[RETRY {retry + 1}] EPIPE 오류 재시도: {e}")
                    continue
                else:
                    raise e
                    
    elif platform == "sh-ann":
        # sh-ann 크롤링 시 저장 경로 설정
        if fresh: 
            clean_today("sh-ann")  # 오늘 날짜의 sh-ann 데이터만 삭제 (data/raw 폴더)
            print("[FRESH] 기존 sh-ann 데이터 삭제 완료")
        out_dir = run_dir("sh-ann")  # data/raw/YYYY-MM-DD/sh-ann/ 디렉토리 생성
        
        # EPIPE 오류 재시도 로직
        max_retries = 3
        for retry in range(max_retries):
            try:
                crawler = SHAnnouncementCrawler(progress)
                crawler.crawl()
                break
            except BrokenPipeError as e:
                if retry < max_retries - 1:
                    print(f"[RETRY {retry + 1}] EPIPE 오류 재시도: {e}")
                    continue
                else:
                    raise e
    else:
        print(f"[ERROR] 지원하지 않는 플랫폼: {platform}")
        return False
    
    print(f"[SUCCESS] {platform} 크롤링 완료!")
    return True


def extract_price_range(price_str):
    """가격 문자열에서 최소/최대값 추출"""
    if not price_str or price_str.strip() == "":
        return None, None
    
    import re
    numbers = re.findall(r'[\d,]+', price_str.replace('원', ''))
    if not numbers:
        return None, None
    
    # 빈 문자열 제거하고 숫자로 변환
    clean_numbers = []
    for num in numbers:
        cleaned = num.replace(',', '').strip()
        if cleaned and cleaned.isdigit():
            clean_numbers.append(int(cleaned))
    
    if not clean_numbers:
        return None, None
    
    return min(clean_numbers), max(clean_numbers)

def count_files_from_paths(paths_str, file_type):
    """경로 문자열에서 파일 개수 계산"""
    if not paths_str or (isinstance(paths_str, str) and paths_str.strip() == ""):
        return 0
    
    # float나 다른 타입인 경우 문자열로 변환
    if not isinstance(paths_str, str):
        paths_str = str(paths_str) if paths_str else ""
    
    if not paths_str or paths_str.strip() == "":
        return 0
    
    paths = [p.strip() for p in paths_str.split(';') if p.strip()]
    return len([p for p in paths if file_type in p.lower()])

def analyze_data():
    """데이터 분석 실행"""
    print("🔍 RAW 데이터 분석 시작...")
    
    # 프로젝트 루트 기준으로 data/raw 경로 설정 (분석할 데이터 위치)
    data_root = Path(__file__).parent / "data" / "raw"
    analyzer = RawDataAnalyzer(str(data_root))
    results = analyzer.analyze_all_platforms()
    
    if results:
        analyzer.print_summary()
        analyzer.save_analysis_report()
        print("\n✅ 분석 완료!")
        print("📄 상세 보고서: data_analysis_report.json")
        return True
    else:
        print("❌ 분석할 데이터가 없습니다.")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="서울주택도시공사 주택지원 봇 - 통합 실행 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 크롤링
  python main.py crawl sohouse --fresh          # 사회주택 크롤링
  python main.py crawl all --fresh             # 모든 플랫폼 크롤링
  
  
  # 데이터 분석
  python main.py analyze                        # RAW 데이터 분석
  
  # 전체 프로세스
  python main.py all --fresh                   # 크롤링 → 분석
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령어')
    
    # 크롤링 서브커맨드
    crawl_parser = subparsers.add_parser('crawl', help='크롤링 실행')
    crawl_parser.add_argument(
        "platform", 
        choices=["sohouse", "cohouse", "youth", "happy", "lh-ann", "sh-ann", "all"],
        help="크롤링할 플랫폼 선택"
    )
    crawl_parser.add_argument(
        "--fresh", 
        action="store_true", 
        help="기존 데이터 삭제 후 크롤링"
    )
    crawl_parser.add_argument(
        "--max-youth-bbs", 
        type=int, 
        default=0,
        help="청년주택 최대 BBS 상세 크롤링 수 (0 = 전체)"
    )
    
    
    # 분석 서브커맨드
    subparsers.add_parser('analyze', help='데이터 분석')
    
    # 전체 프로세스 서브커맨드
    all_parser = subparsers.add_parser('all', help='전체 프로세스 실행')
    all_parser.add_argument(
        "--fresh", 
        action="store_true", 
        help="기존 데이터 삭제 후 크롤링"
    )
    
    args = parser.parse_args()
    
    if args.command == 'crawl':
        if args.platform == "all":
            # 모든 플랫폼 크롤링
            platforms = ["sohouse", "cohouse", "youth", "happy", "lh-ann", "sh-ann"]
            print(f"[START] 모든 플랫폼 크롤링 시작 (총 {len(platforms)}개)")
            
            success_count = 0
            for platform in platforms:
                print(f"\n{'='*50}")
                print(f"[PLATFORM] {platform} 크롤링 시작")
                print(f"{'='*50}")
                
                if crawl_platform(platform, args.fresh, args.max_youth_bbs):
                    success_count += 1
                else:
                    print(f"[ERROR] {platform} 크롤링 실패")
            
            print(f"\n{'='*50}")
            print(f"[COMPLETE] 전체 크롤링 완료: {success_count}/{len(platforms)} 성공")
            print(f"{'='*50}")
        else:
            # 단일 플랫폼 크롤링
            crawl_platform(args.platform, args.fresh, args.max_youth_bbs)
    
    
    elif args.command == 'analyze':
        analyze_data()
    
    elif args.command == 'all':
        # 전체 프로세스: 크롤링 → 분석
        print("🚀 전체 프로세스 시작: 크롤링 → 분석")
        print("="*60)
        
        # 1. 크롤링
        print("\n1️⃣ 크롤링 단계")
        platforms = ["sohouse", "cohouse", "youth", "happy", "lh-ann", "sh-ann"]
        success_count = 0
        for platform in platforms:
            if crawl_platform(platform, args.fresh, 0):
                success_count += 1
        
        if success_count > 0:
            # 2. 분석
            print("\n2️⃣ 데이터 분석 단계")
            analyze_data()
            
            print("\n🎉 전체 프로세스 완료!")
        else:
            print("\n❌ 크롤링 실패로 인해 프로세스 중단")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
