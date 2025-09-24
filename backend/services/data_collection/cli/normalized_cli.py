#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
정규화 CLI
최근 날짜의 raw 데이터를 정규화된 테이블 구조로 변환
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import json
import pandas as pd
from datetime import datetime

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.curated.normalizer import DataNormalizer
from backend.services.data_collection.curated.db_loader import NormalizedDataLoader
from backend.db.db_utils_pg import get_engine

HELP = """data-collection normalized <command> [args]

Commands:
  process              최근 날짜의 모든 raw 데이터를 정규화
  process --platform <name>  특정 플랫폼만 정규화
  process --date <date>      특정 날짜만 정규화
  process --db              정규화 후 DB에 저장

Examples:
  data-collection normalized process
  data-collection normalized process --platform sohouse
  data-collection normalized process --date 2025-09-15
  data-collection normalized process --db
"""

def find_latest_raw_data(platform: str = None, date: str = None) -> List[Path]:
    """최근 날짜의 raw 데이터 파일들을 찾기"""
    raw_dir = Path("backend/data/raw")
    if not raw_dir.exists():
        return []
    
    raw_files = []
    
    # 플랫폼별로 검색
    platforms = [platform] if platform else ['sohouse', 'cohouse', 'youth', 'sh', 'lh']
    
    for platform_name in platforms:
        platform_dir = raw_dir / platform_name
        if not platform_dir.exists():
            continue
            
        # 날짜별 디렉토리 찾기
        date_dirs = [d for d in platform_dir.iterdir() if d.is_dir()]
        if not date_dirs:
            continue
            
        # 날짜별로 정렬 (최신순)
        date_dirs.sort(key=lambda x: x.name, reverse=True)
        
        # 특정 날짜가 지정된 경우
        if date:
            target_dirs = [d for d in date_dirs if d.name.startswith(date)]
        else:
            # 최신 날짜만
            target_dirs = [date_dirs[0]]
        
        # 각 날짜 디렉토리에서 raw.csv 찾기
        for date_dir in target_dirs:
            raw_csv = date_dir / "raw.csv"
            if raw_csv.exists():
                raw_files.append(raw_csv)
    
    return raw_files

def get_normalized_output_path(raw_file: Path) -> Path:
    """정규화된 데이터 출력 경로 생성: data/normalized/크롤링날짜/플랫폼명/"""
    # raw 경로에서 날짜와 플랫폼명 추출
    # 예: data/raw/sohouse/2025-09-15__20250915T021038/raw.csv
    path_parts = raw_file.parts
    platform_name = None
    date_str = None
    
    for i, part in enumerate(path_parts):
        if part in ['sohouse', 'cohouse', 'youth', 'sh', 'lh']:
            platform_name = part
            # 다음 디렉토리가 날짜일 가능성이 높음
            if i + 1 < len(path_parts):
                date_str = path_parts[i + 1]
            break
    
    if not platform_name or not date_str:
        raise ValueError(f"플랫폼명 또는 날짜를 추출할 수 없습니다: {raw_file}")
    
    # backend/data/normalized/크롤링날짜/플랫폼명/ 구조로 생성
    output_path = Path("backend") / "data" / "normalized" / date_str / platform_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    return output_path

def normalize_data(raw_csv_path: str) -> bool:
    """raw 데이터를 정규화된 데이터로 변환"""
    raw_path = Path(raw_csv_path)
    if not raw_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {raw_csv_path}")
        return False
    
    try:
        # 출력 경로 생성
        output_path = get_normalized_output_path(raw_path)
        print(f"📁 출력 경로: {output_path}")
        
        print(f"🔄 정규화 시작: {raw_csv_path}")
        
        normalizer = DataNormalizer()
        normalized_data = normalizer.normalize_raw_data(raw_path)
        
        # 정규화된 데이터를 JSON으로 저장
        for table_name, data in normalized_data.items():
            output_file = output_path / f"{table_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"✅ {table_name}: {len(data)}개 레코드 저장 → {output_file}")
        
        # 실패한 주소 통계 출력
        if hasattr(normalizer, 'failed_addresses') and normalizer.failed_addresses:
            print(f"⚠️  주소 정규화 실패: {len(normalizer.failed_addresses)}건")
            print(f"📄 실패 데이터 저장: backend/data/normalized/failed_addresses_*.csv")
        else:
            print("✅ 주소 정규화 실패 없음")
        
        print(f"✅ 정규화 완료: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 정규화 실패: {e}")
        return False

def load_to_db(raw_csv_path: str, db_url: str = None) -> bool:
    """정규화 후 DB에 저장"""
    raw_path = Path(raw_csv_path)
    if not raw_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {raw_csv_path}")
        return False
    
    print(f"🔄 정규화 및 DB 저장 시작: {raw_csv_path}")
    
    try:
        # 정규화
        normalizer = DataNormalizer()
        normalized_data = normalizer.normalize_raw_data(raw_path)
        
        # 실패한 주소 통계 출력
        if hasattr(normalizer, 'failed_addresses') and normalizer.failed_addresses:
            print(f"⚠️  주소 정규화 실패: {len(normalizer.failed_addresses)}건")
            print(f"📄 실패 데이터 저장: backend/data/normalized/failed_addresses_*.csv")
        else:
            print("✅ 주소 정규화 실패 없음")
        
        # DB URL 설정
        if not db_url:
            db_url = get_engine().url
        
        # DB에 저장
        with NormalizedDataLoader(db_url) as loader:
            success = loader.load_normalized_data(normalized_data)
            
            if success:
                print("✅ DB 저장 완료")
                return True
            else:
                print("❌ DB 저장 실패")
                return False
                
    except Exception as e:
        print(f"❌ 처리 실패: {e}")
        return False

def process_latest_data(platform: str = None, date: str = None, save_to_db: bool = False) -> bool:
    """최근 날짜의 모든 raw 데이터를 정규화"""
    print(f"🔍 최근 raw 데이터 검색 중...")
    
    raw_files = find_latest_raw_data(platform, date)
    if not raw_files:
        print("❌ 처리할 raw 데이터를 찾을 수 없습니다")
        return False
    
    print(f"📁 발견된 raw 파일: {len(raw_files)}개")
    for file in raw_files:
        print(f"  - {file}")
    
    success_count = 0
    
    for raw_file in raw_files:
        print(f"\n🔄 처리 중: {raw_file}")
        
        # 정규화
        if normalize_data(str(raw_file)):
            success_count += 1
            print(f"✅ 정규화 완료: {raw_file}")
            
            # DB 저장 옵션이 활성화된 경우
            if save_to_db:
                print(f"💾 DB 저장 중: {raw_file}")
                if load_to_db(str(raw_file)):
                    print(f"✅ DB 저장 완료: {raw_file}")
                else:
                    print(f"❌ DB 저장 실패: {raw_file}")
        else:
            print(f"❌ 정규화 실패: {raw_file}")
    
    print(f"\n📊 처리 결과: {success_count}/{len(raw_files)} 성공")
    return success_count > 0

def main():
    # 환경 변수 설정 (기본값)
    import os
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_DB", "rey")
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:post1234@localhost:5432/rey")
    
    parser = argparse.ArgumentParser(description="정규화 CLI")
    parser.add_argument("command", choices=["process"], 
                       help="실행할 명령어")
    parser.add_argument("--platform", help="특정 플랫폼만 처리 (sohouse, cohouse, youth, sh, lh)")
    parser.add_argument("--date", help="특정 날짜만 처리 (YYYY-MM-DD)")
    parser.add_argument("--db", action="store_true", help="정규화 후 DB에 저장")
    parser.add_argument("--db-url", help="데이터베이스 URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")
    
    args = parser.parse_args()
    
    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 명령어 실행
    if args.command == "process":
        success = process_latest_data(args.platform, args.date, args.db)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
