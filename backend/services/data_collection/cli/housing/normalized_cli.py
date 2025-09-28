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

from backend.services.data_collection.normalized.housing.normalizer import DataNormalizer
from backend.services.data_collection.normalized.housing.db_loader import NormalizedDataLoader
from backend.db.db_utils_pg import get_engine

HELP = """data-ingest normalized <command> [args]

Commands:
  process              최근 날짜의 모든 raw 데이터를 정규화
  process --platform <name>  특정 플랫폼만 정규화
  process --date <date>      특정 날짜만 정규화
  process --db              정규화 후 DB에 저장
  process --fresh           기존 정규화 데이터를 삭제하고 새로 생성

Examples:
  data-ingest normalized process
  data-ingest normalized process --platform sohouse
  data-ingest normalized process --date 2025-09-15
  data-ingest normalized process --db
  data-ingest normalized process --fresh
  data-ingest normalized process --platform cohouse --fresh
"""

def find_latest_raw_data(platform: str = None, date: str = None) -> List[Path]:
    """최근 날짜의 housing 데이터 파일들을 찾기"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    housing_dir = backend_dir / "data" / "housing"
    
    if not housing_dir.exists():
        logging.warning(f"[ERROR] Housing directory not found: {housing_dir}")
        return []
    
    raw_files = []
    
    # 플랫폼별로 검색
    platforms = [platform] if platform else ['sohouse', 'cohouse', 'youth', 'sh', 'lh']
    logging.debug(f"[DEBUG] Searching platforms: {platforms}")
    
    for platform_name in platforms:
        platform_dir = housing_dir / platform_name
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
    """정규화된 데이터 출력 경로 생성: data/normalized/작업진행날짜/플랫폼명/"""
    # housing 경로에서 플랫폼명만 추출
    # 예: data/housing/sohouse/2025-09-15/raw.csv
    path_parts = raw_file.parts
    platform_name = None
    
    for part in path_parts:
        if part in ['sohouse', 'cohouse', 'youth', 'sh', 'lh']:
            platform_name = part
            break
    
    if not platform_name:
        raise ValueError(f"플랫폼명을 추출할 수 없습니다: {raw_file}")
    
    # 오늘 날짜 사용 (정규화 실행 날짜)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    # backend/data/normalized/작업진행날짜/플랫폼명/ 구조로 생성
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    output_path = backend_dir / "data" / "normalized" / today / platform_name
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
        
        # 실시간 저장을 위한 콜백 함수
        def save_progress(table_name: str, data: list):
            output_file = output_path / f"{table_name}.json"
            
            # NaN 값을 null로 변환하는 함수
            def convert_nan_to_null(obj):
                if isinstance(obj, dict):
                    return {k: convert_nan_to_null(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_nan_to_null(item) for item in obj]
                elif pd.isna(obj):
                    return None
                elif hasattr(obj, 'isoformat'):  # datetime, Timestamp 등
                    return obj.isoformat()
                else:
                    return obj
            
            # 데이터 변환
            converted_data = convert_nan_to_null(data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2)
            print(f"✅ {table_name}: {len(data)}개 레코드 저장 → {output_file}")
        
        # 정규화 실행 (실시간 저장)
        normalized_data = normalizer.normalize_raw_data(raw_path, save_callback=save_progress)
        
        # codes.json 복사 (공통 파일)
        codes_file = Path("backend/data/normalized/2025-09-28/codes.json")
        if codes_file.exists():
            import shutil
            shutil.copy(codes_file, output_path / "codes.json")
            print(f"✅ codes.json 복사 완료")
        
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
        
        # DB URL 설정
        if not db_url:
            db_url = get_engine().url
        
        # DB에 저장
        loader = NormalizedDataLoader(db_url)
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

def clean_normalized_data(platform: str = None, date: str = None) -> None:
    """기존 정규화된 데이터 삭제"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    normalized_dir = backend_dir / "backend" / "data" / "normalized"
    
    if not normalized_dir.exists():
        logging.info("[INFO] Normalized data directory not found")
        return
    
    # 날짜별로 검색 (실제 구조: normalized/날짜/플랫폼)
    date_dirs = [d for d in normalized_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        logging.info("[INFO] No normalized data found")
        return
        
    # 날짜별로 정렬 (최신순)
    date_dirs.sort(key=lambda x: x.name, reverse=True)
    
    # 특정 날짜가 지정된 경우
    if date:
        target_date_dirs = [d for d in date_dirs if d.name.startswith(date)]
    else:
        # 최신 날짜만
        target_date_dirs = [date_dirs[0]]
    
    # 플랫폼별로 검색
    platforms = [platform] if platform else ['sohouse', 'cohouse', 'youth', 'sh', 'lh']
    
    for date_dir in target_date_dirs:
        print(f"🗑️  날짜 디렉토리 검사: {date_dir}")
        
        for platform_name in platforms:
            platform_dir = date_dir / platform_name
            if platform_dir.exists():
                print(f"🗑️  기존 정규화 데이터 삭제: {platform_dir}")
                import shutil
                shutil.rmtree(platform_dir, ignore_errors=True)
        
        # 날짜 디렉토리가 비어있으면 삭제
        if not any(date_dir.iterdir()):
            print(f"🗑️  빈 날짜 디렉토리 삭제: {date_dir}")
            import shutil
            shutil.rmtree(date_dir, ignore_errors=True)

def process_latest_data(platform: str = None, date: str = None, save_to_db: bool = False, fresh: bool = False) -> bool:
    """최근 날짜의 모든 raw 데이터를 정규화"""
    if fresh:
        print(f"🧹 Fresh 모드: 기존 정규화 데이터 삭제 중...")
        clean_normalized_data(platform, date)
    
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
    parser.add_argument("--fresh", action="store_true", help="기존 정규화 데이터를 삭제하고 새로 생성")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")
    
    args = parser.parse_args()
    
    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 명령어 실행
    if args.command == "process":
        success = process_latest_data(args.platform, args.date, args.db, args.fresh)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
