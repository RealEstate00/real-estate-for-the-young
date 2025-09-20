#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
정규화된 데이터를 DB에 적재하는 CLI 스크립트
data-load <command> [args] 형태로 사용
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.curated.db_loader import NormalizedDataLoader
from backend.services.data_collection.curated.infra_loader import InfraDataLoader
from backend.db.db_utils_pg import test_connection

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_housing_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    """
    주택 관련 정규화된 데이터를 DB에 적재
    
    Args:
        normalized_data_dir: 정규화된 데이터 디렉토리 경로
        db_url: 데이터베이스 URL (None이면 환경변수에서 가져옴)
        
    Returns:
        성공 여부
    """
    try:
        # DB URL 설정
        if db_url is None:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
                return False
        
        # 정규화된 데이터 디렉토리 확인
        normalized_path = Path(normalized_data_dir)
        if not normalized_path.exists():
            logger.error(f"정규화된 데이터 디렉토리가 존재하지 않습니다: {normalized_path}")
            return False
        
        # DB 연결 테스트
        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결에 실패했습니다.")
            return False
        
        logger.info("DB 연결 성공")
        
        # 정규화된 데이터 로드
        logger.info(f"주택 데이터 로드 시작: {normalized_path}")
        
        with NormalizedDataLoader(db_url) as loader:
            success = loader.load_from_directory(normalized_path)
            
            if success:
                logger.info("주택 데이터 로드 완료")
                return True
            else:
                logger.error("주택 데이터 로드 실패")
                return False
                
    except Exception as e:
        logger.error(f"주택 데이터 로드 중 오류 발생: {e}")
        return False

def load_rtms_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    """
    RTMS 관련 정규화된 데이터를 DB에 적재
    
    Args:
        normalized_data_dir: 정규화된 데이터 디렉토리 경로
        db_url: 데이터베이스 URL (None이면 환경변수에서 가져옴)
        
    Returns:
        성공 여부
    """
    # RTMS 데이터 로딩 로직 (현재는 housing과 동일하게 처리)
    return load_housing_data(normalized_data_dir, db_url)

def load_infra_data(db_url: Optional[str] = None) -> bool:
    """
    공공시설 데이터를 DB에 적재
    
    Args:
        db_url: 데이터베이스 URL (None이면 환경변수에서 가져옴)
        
    Returns:
        성공 여부
    """
    try:
        # DB URL 설정
        if db_url is None:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
                return False
        
        # DB 연결 테스트
        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결에 실패했습니다.")
            return False
        
        logger.info("DB 연결 성공")
        
        # 공공시설 데이터 로드
        logger.info("공공시설 데이터 로드 시작")
        
        loader = InfraDataLoader(db_url)
        success = loader.load_all_infra()
        
        if success:
            logger.info("공공시설 데이터 로드 완료")
            return True
        else:
            logger.error("공공시설 데이터 로드 실패")
            return False
            
    except Exception as e:
        logger.error(f"공공시설 데이터 로드 중 오류 발생: {e}")
        return False

def load_normalized_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    """
    정규화된 데이터를 DB에 적재
    
    Args:
        normalized_data_dir: 정규화된 데이터 디렉토리 경로
        db_url: 데이터베이스 URL (None이면 환경변수에서 가져옴)
        
    Returns:
        성공 여부
    """
    try:
        # DB URL 설정
        if db_url is None:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
                return False
        
        # 정규화된 데이터 디렉토리 확인
        normalized_path = Path(normalized_data_dir)
        if not normalized_path.exists():
            logger.error(f"정규화된 데이터 디렉토리가 존재하지 않습니다: {normalized_path}")
            return False
        
        # DB 연결 테스트
        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결에 실패했습니다.")
            return False
        
        logger.info("DB 연결 성공")
        
        # 정규화된 데이터 로드
        logger.info(f"정규화된 데이터 로드 시작: {normalized_path}")
        
        with NormalizedDataLoader(db_url) as loader:
            success = loader.load_from_directory(normalized_path)
            
            if success:
                logger.info("정규화된 데이터 로드 완료")
                return True
            else:
                logger.error("정규화된 데이터 로드 실패")
                return False
                
    except Exception as e:
        logger.error(f"데이터 로드 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    import argparse
    import os
    
    # 환경 변수 설정 (기본값)
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_DB", "rey")
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:post1234@localhost:5432/rey")
    
    parser = argparse.ArgumentParser(description='data-load: 데이터를 DB에 적재')
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
    
    # housing 서브커맨드
    housing_parser = subparsers.add_parser('housing', help='주택 데이터 로드')
    housing_parser.add_argument(
        '--data-dir',
        type=str,
        default='backend/data/normalized',
        help='정규화된 데이터 디렉토리 경로 (기본값: backend/data/normalized)'
    )
    
    # rtms 서브커맨드
    rtms_parser = subparsers.add_parser('rtms', help='RTMS 데이터 로드')
    rtms_parser.add_argument(
        '--data-dir',
        type=str,
        default='backend/data/normalized',
        help='정규화된 데이터 디렉토리 경로 (기본값: backend/data/normalized)'
    )
    
    # infra 서브커맨드
    infra_parser = subparsers.add_parser('infra', help='공공시설 데이터 로드')
    
    # all 서브커맨드 (기존 동작)
    all_parser = subparsers.add_parser('all', help='모든 데이터 로드')
    all_parser.add_argument(
        '--data-dir',
        type=str,
        default='backend/data/normalized',
        help='정규화된 데이터 디렉토리 경로 (기본값: backend/data/normalized)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 명령어가 없으면 도움말 출력
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    success = False
    
    if args.command == 'housing':
        data_dir = Path(args.data_dir).resolve()
        logger.info(f"주택 데이터 디렉토리: {data_dir}")
        success = load_housing_data(str(data_dir), args.db_url)
        
    elif args.command == 'rtms':
        data_dir = Path(args.data_dir).resolve()
        logger.info(f"RTMS 데이터 디렉토리: {data_dir}")
        success = load_rtms_data(str(data_dir), args.db_url)
        
    elif args.command == 'infra':
        logger.info("공공시설 데이터 로드 시작")
        success = load_infra_data(args.db_url)
        
    elif args.command == 'all':
        data_dir = Path(args.data_dir).resolve()
        logger.info(f"모든 데이터 디렉토리: {data_dir}")
        success = load_normalized_data(str(data_dir), args.db_url)
    
    if success:
        logger.info(f"{args.command} 데이터 적재가 성공적으로 완료되었습니다.")
        sys.exit(0)
    else:
        logger.error(f"{args.command} 데이터 적재에 실패했습니다.")
        sys.exit(1)

if __name__ == '__main__':
    main()
