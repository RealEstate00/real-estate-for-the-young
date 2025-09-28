#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
서울 열린데이터광장 API 데이터 정규화 및 DB 적재 CLI
"""

import sys
import argparse
import logging
from pathlib import Path
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import importlib.util

# normalizer 모듈 로드
normalizer_path = Path(__file__).parent.parent / "public-api" / "normalizer.py"
spec = importlib.util.spec_from_file_location("normalizer", normalizer_path)
normalizer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(normalizer_module)
SeoulDataNormalizer = normalizer_module.SeoulDataNormalizer

# db_loader 모듈 로드
db_loader_path = Path(__file__).parent.parent / "public-api" / "db_loader.py"
spec = importlib.util.spec_from_file_location("db_loader", db_loader_path)
db_loader_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_loader_module)
SeoulDataLoader = db_loader_module.SeoulDataLoader

# DB 연결 테스트 함수 (간단한 버전)
def test_connection():
    """DB 연결 테스트"""
    try:
        from backend.db.db_utils_pg import test_connection as _test_connection
        return _test_connection()
    except ImportError:
        # 간단한 연결 테스트
        import psycopg2
        try:
            conn = psycopg2.connect(
                host=os.getenv('PG_HOST', 'localhost'),
                port=os.getenv('PG_PORT', '5432'),
                user=os.getenv('PG_USER', 'postgres'),
                password=os.getenv('PG_PASSWORD', 'post1234'),
                database=os.getenv('PG_DB', 'rey')
            )
            conn.close()
            return True
        except Exception as e:
            logger.error(f"DB 연결 실패: {e}")
            return False

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def normalize_data(csv_dir: str, output_dir: str) -> bool:
    """CSV 데이터를 정규화"""
    try:
        csv_path = Path(csv_dir)
        output_path = Path(output_dir)
        
        if not csv_path.exists():
            logger.error(f"CSV 디렉토리가 존재하지 않습니다: {csv_path}")
            return False
        
        logger.info(f"서울 API 데이터 정규화 시작: {csv_path}")
        
        normalizer = SeoulDataNormalizer()
        normalized_data = normalizer.normalize_all_services(csv_path)
        
        # 정규화된 데이터 저장
        normalizer.save_normalized_data(output_path)
        
        # 통계 출력
        total_records = sum(len(data) for data in normalized_data.values())
        logger.info(f"정규화 완료: {len(normalized_data)}개 서비스, 총 {total_records}개 레코드")
        
        return True
        
    except Exception as e:
        logger.error(f"정규화 실패: {e}")
        return False

def load_to_db(normalized_dir: str, db_url: str = None) -> bool:
    """정규화된 데이터를 DB에 적재"""
    try:
        normalized_path = Path(normalized_dir)
        
        if not normalized_path.exists():
            logger.error(f"정규화된 데이터 디렉토리가 존재하지 않습니다: {normalized_path}")
            return False
        
        # DB 연결 테스트
        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결에 실패했습니다.")
            return False
        
        logger.info("DB 연결 성공")
        
        # DB URL 설정
        if not db_url:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
                return False
        
        # 정규화된 데이터 로드
        logger.info(f"서울 API 데이터 로드 시작: {normalized_path}")
        
        with SeoulDataLoader(db_url) as loader:
            success = loader.load_from_directory(normalized_path)
            
            if success:
                logger.info("서울 API 데이터 로드 완료")
                return True
            else:
                logger.error("서울 API 데이터 로드 실패")
                return False
                
    except Exception as e:
        logger.error(f"DB 적재 실패: {e}")
        return False

def main():
    """메인 함수"""
    # 환경 변수 설정 (기본값)
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_DB", "rey")
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:post1234@localhost:5432/rey")
    
    parser = argparse.ArgumentParser(description='서울 API 데이터 정규화 및 DB 적재')
    parser.add_argument(
        '--db-url',
        type=str,
        help='데이터베이스 URL (기본값: DATABASE_URL 환경변수 사용)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    # 서브커맨드 추가
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # normalize 서브커맨드
    normalize_parser = subparsers.add_parser('normalize', help='CSV 데이터 정규화')
    normalize_parser.add_argument(
        '--csv-dir',
        type=str,
        default='backend/data/public-api/openseoul',
        help='CSV 데이터 디렉토리 경로 (기본값: backend/data/public-api/openseoul)'
    )
    normalize_parser.add_argument(
        '--output-dir',
        type=str,
        default='backend/data/normalized/seoul',
        help='정규화된 데이터 출력 디렉토리 (기본값: backend/data/normalized/seoul)'
    )
    
    # load 서브커맨드
    load_parser = subparsers.add_parser('load', help='정규화된 데이터를 DB에 적재')
    load_parser.add_argument(
        '--data-dir',
        type=str,
        default='backend/data/normalized/seoul',
        help='정규화된 데이터 디렉토리 경로 (기본값: backend/data/normalized/seoul)'
    )
    
    # all 서브커맨드
    all_parser = subparsers.add_parser('all', help='정규화 및 DB 적재 모두 실행')
    all_parser.add_argument(
        '--csv-dir',
        type=str,
        default='backend/data/public-api/openseoul',
        help='CSV 데이터 디렉토리 경로 (기본값: backend/data/public-api/openseoul)'
    )
    all_parser.add_argument(
        '--output-dir',
        type=str,
        default='backend/data/normalized/seoul',
        help='정규화된 데이터 출력 디렉토리 (기본값: backend/data/normalized/seoul)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 명령어가 없으면 도움말 출력
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    success = False
    
    if args.command == 'normalize':
        success = normalize_data(args.csv_dir, args.output_dir)
        
    elif args.command == 'load':
        success = load_to_db(args.data_dir, args.db_url)
        
    elif args.command == 'all':
        # 정규화 먼저 실행
        if normalize_data(args.csv_dir, args.output_dir):
            # 정규화 성공 시 DB 적재
            success = load_to_db(args.output_dir, args.db_url)
        else:
            success = False
    
    if success:
        logger.info(f"{args.command} 명령이 성공적으로 완료되었습니다.")
        sys.exit(0)
    else:
        logger.error(f"{args.command} 명령이 실패했습니다.")
        sys.exit(1)


if __name__ == '__main__':
    main()
