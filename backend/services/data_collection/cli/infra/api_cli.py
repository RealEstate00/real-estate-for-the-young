#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
API 데이터 수집, 정규화 및 DB 적재 CLI
===========================================
서울 열린데이터광장 API에서 데이터를 수집, 정규화하고 DB에 적재하는 CLI
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from backend.libs.utils.paths import RAW_DIR, INFRA_NORMALIZED_DIR

# 모듈 import
from backend.services.data_collection.infra.collector.get_open_csv import main as collect_api_data
from backend.services.data_collection.infra.normalized.infra_normalizer_NoJusoAPI import InfraNormalizer
from backend.services.loading.infra.infra_db_loader import JSONLDBLoader
from backend.services.db.common.db_utils import test_connection

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def collect_data(
    service: str = "all",
    output_dir: Optional[Path] = None,
    fresh: bool = False,
    verbose: bool = False
) -> bool:
    """API 데이터 수집"""
    setup_logging(verbose)
    
    if output_dir is None:
        output_dir = RAW_DIR / "api"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 출력 디렉토리: {output_dir}")
    logger.info(f"🔍 수집 서비스: {service}")
    logger.info(f"🔄 Fresh 모드: {fresh}")
    
    try:
        # API 데이터 수집 실행
        collect_api_data(output_dir=str(output_dir))
        
        logger.info("✅ API 데이터 수집 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터 수집 중 오류 발생: {e}")
        return False

def normalize_data(
    csv_dir: Path,
    output_dir: Optional[Path] = None,
    verbose: bool = False
) -> bool:
    """CSV 데이터를 정규화"""
    setup_logging(verbose)
    
    if not csv_dir.exists():
        logger.error(f"CSV 디렉토리가 존재하지 않습니다: {csv_dir}")
        return False
    
    if output_dir is None:
        output_dir = INFRA_NORMALIZED_DIR
    
    logger.info(f"📁 입력 CSV 디렉토리: {csv_dir}")
    logger.info(f"📁 출력 디렉토리: {output_dir}")
    
    try:
        # 정규화 실행
        normalizer = InfraNormalizer(data_dir=csv_dir)
        normalizer.normalize_openseoul_data(output_dir=output_dir, realtime_mode=True)
        
        logger.info("✅ 서울 API 데이터 정규화 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 정규화 중 오류 발생: {e}")
        return False

def load_data(
    normalized_dir: Path,
    db_url: Optional[str] = None,
    verbose: bool = False
) -> bool:
    """정규화된 데이터를 DB에 적재"""
    setup_logging(verbose)
    
    if not normalized_dir.exists():
        logger.error(f"정규화된 데이터 디렉토리가 존재하지 않습니다: {normalized_dir}")
        return False
    
    logger.info(f"📁 정규화된 데이터 디렉토리: {normalized_dir}")
    
    try:
        # DB 연결 테스트
        if not test_connection():
            logger.error("❌ 데이터베이스 연결 실패")
            return False
        
        # 데이터 로딩
        loader = JSONLDBLoader(db_url=db_url)
        loader.load_all_jsonl_files(normalized_dir)
        
        logger.info("✅ 서울 API 데이터 DB 적재 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ DB 적재 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="API 데이터 수집, 정규화 및 DB 적재 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  data-collection-infra api collect
  data-collection-infra api collect --service all
  data-collection-infra api load
  data-collection-infra api all
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # collect 명령어
    collect_parser = subparsers.add_parser('collect', help='API 데이터 수집')
    collect_parser.add_argument(
        '--service',
        default='all',
        help='수집할 서비스 (기본값: all)'
    )
    collect_parser.add_argument(
        '--output-dir',
        type=Path,
        help='출력 디렉토리 (기본값: backend/data/raw/api)'
    )
    collect_parser.add_argument(
        '--fresh',
        action='store_true',
        help='기존 데이터 삭제 후 새로 수집'
    )
    collect_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    
    # load 명령어
    load_parser = subparsers.add_parser('load', help='정규화된 데이터를 DB에 적재')
    load_parser.add_argument(
        '--normalized-dir',
        type=Path,
        default=INFRA_NORMALIZED_DIR,
        help='정규화된 데이터 디렉토리 (기본값: backend/data/normalized/infra)'
    )
    load_parser.add_argument(
        '--db-url',
        help='데이터베이스 URL (기본값: DATABASE_URL 환경변수 사용)'
    )
    load_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    # all 명령어
    all_parser = subparsers.add_parser('all', help='수집 및 DB 적재 모두 실행')
    all_parser.add_argument(
        '--service',
        default='all',
        help='수집할 서비스 (기본값: all)'
    )
    all_parser.add_argument(
        '--csv-dir',
        type=Path,
        help='CSV 데이터 디렉토리 (기본값: backend/data/raw/api)'
    )
    all_parser.add_argument(
        '--normalized-dir',
        type=Path,
        help='정규화된 데이터 디렉토리 (기본값: backend/data/normalized/infra)'
    )
    all_parser.add_argument(
        '--db-url',
        help='데이터베이스 URL (기본값: DATABASE_URL 환경변수 사용)'
    )
    all_parser.add_argument(
        '--fresh',
        action='store_true',
        help='기존 데이터 삭제 후 새로 수집'
    )
    all_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    args = parser.parse_args()
    
    if args.command == 'collect':
        success = collect_data(
            service=args.service,
            output_dir=args.output_dir,
            fresh=args.fresh,
            verbose=args.verbose
        )
        sys.exit(0 if success else 1)
        
    elif args.command == 'load':
        success = load_data(
            normalized_dir=args.normalized_dir,
            db_url=args.db_url,
            verbose=args.verbose
        )
        sys.exit(0 if success else 1)
        
    elif args.command == 'all':
        # 수집 실행
        csv_dir = args.csv_dir or RAW_DIR / "api"
        success1 = collect_data(
            service=args.service,
            output_dir=csv_dir,
            fresh=args.fresh,
            verbose=args.verbose
        )
        
        if not success1:
            logger.error("❌ 데이터 수집 실패로 인해 DB 적재를 건너뜁니다")
            sys.exit(1)
        
        # DB 적재 실행 (정규화된 데이터가 이미 있다고 가정)
        normalized_dir = args.normalized_dir or INFRA_NORMALIZED_DIR
        success2 = load_data(
            normalized_dir=normalized_dir,
            db_url=args.db_url,
            verbose=args.verbose
        )
        
        sys.exit(0 if success2 else 1)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()