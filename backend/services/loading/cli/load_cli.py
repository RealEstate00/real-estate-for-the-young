#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
정규화된 데이터를 DB에 적재하는 CLI 스크립트
Usage:
  data-load housing --data-dir backend/data/normalized
  data-load all     --data-dir backend/data/normalized
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from backend.services.db.common.db_utils import test_connection
from backend.services.loading.housing.housing_db_loader import HousingLoader, LoaderConfig, build_db_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def _resolve_db_url(cli_db_url: Optional[str]) -> str:
    if cli_db_url:
        return cli_db_url
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    return build_db_url()

def _load_housing_dir(housing_root: Path, db_url: str) -> bool:
    try:
        if not housing_root.exists():
            logger.error("정규화된 주택 데이터 디렉토리가 존재하지 않습니다: %s", housing_root)
            return False

        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결 실패")
            return False
        logger.info("DB 연결 성공")

        cfg = LoaderConfig(root_dir=housing_root, db_url=db_url, only_latest_date=True)
        logger.info("주택 데이터 로드 시작: %s", housing_root)

        loader = HousingLoader(cfg)  # ✅ __init__(cfg) 로 통일
        loader.run()

        logger.info("주택 데이터 로드 완료")
        return True
    except Exception as e:
        logger.exception("주택 데이터 로드 중 오류 발생: %s", e)
        return False

def load_housing_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    root = Path(normalized_data_dir).resolve()
    housing_root = root / "housing"
    dbu = _resolve_db_url(db_url)
    masked = dbu
    if "postgresql" in dbu:
        pwd = os.getenv("PG_PASSWORD", "post1234")
        masked = dbu.replace(pwd, "******")
    logger.info("주택 데이터 디렉토리: %s", housing_root)
    logger.info("DB URL: %s", masked)
    return _load_housing_dir(housing_root, dbu)

def load_rtms_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    try:
        root = Path(normalized_data_dir).resolve()
        rtms_root = root / "rtms"
        
        if not rtms_root.exists():
            logger.error("정규화된 RTMS 데이터 디렉토리가 존재하지 않습니다: %s", rtms_root)
            return False

        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결 실패")
            return False
        logger.info("DB 연결 성공")

        # RTMS 로더 import
        from backend.services.loading.rtms.load_rtms_data import RTMSDataLoader
        
        # DB 설정
        db_config = {
            'host': os.getenv('PG_HOST', 'localhost'),
            'port': os.getenv('PG_PORT', '5432'),
            'database': os.getenv('PG_DB', 'rey'),
            'user': os.getenv('PG_USER', 'postgres'),
            'password': os.getenv('PG_PASSWORD', 'post1234'),
        }
        
        logger.info("RTMS 데이터 디렉토리: %s", rtms_root)
        logger.info("DB 호스트: %s:%s", db_config['host'], db_config['port'])
        
        # RTMS 데이터 로드
        loader = RTMSDataLoader(db_config)
        loader.connect()
        loader.clear_and_load(rtms_root, batch_size=10000)
        loader.close()
        
        logger.info("RTMS 데이터 로드 완료")
        return True
        
    except Exception as e:
        logger.exception("RTMS 데이터 로드 중 오류 발생: %s", e)
        return False

def load_infra_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    try:
        root = Path(normalized_data_dir).resolve()
        infra_root = root / "infra"
        
        if not infra_root.exists():
            logger.error("정규화된 인프라 데이터 디렉토리가 존재하지 않습니다: %s", infra_root)
            return False

        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결 실패")
            return False
        logger.info("DB 연결 성공")

        # INFRA 로더 import
        from backend.services.loading.infra.infra_db_loader import JSONLDBLoader
        
        dbu = _resolve_db_url(db_url)
        masked = dbu
        if "postgresql" in dbu:
            pwd = os.getenv("PG_PASSWORD", "post1234")
            masked = dbu.replace(pwd, "******")
        
        logger.info("인프라 데이터 디렉토리: %s", infra_root)
        logger.info("DB URL: %s", masked)
        
        # JSONL 파일들을 DB에 로드
        loader = JSONLDBLoader(db_url=dbu)
        loader.load_all_jsonl_files(infra_root)
        
        logger.info("인프라 데이터 로드 완료")
        return True
        
    except Exception as e:
        logger.exception("인프라 데이터 로드 중 오류 발생: %s", e)
        return False

def load_normalized_data(normalized_data_dir: str, db_url: Optional[str] = None) -> bool:
    """모든 데이터 로드 (주택, 공공시설, 실거래)"""
    logger.info("=== 전체 데이터 로드 시작 ===")
    
    housing_ok = load_housing_data(normalized_data_dir, db_url)
    infra_ok = load_infra_data(normalized_data_dir, db_url)
    rtms_ok = load_rtms_data(normalized_data_dir, db_url)
    
    logger.info("=== 전체 데이터 로드 결과 ===")
    logger.info("주택 데이터: %s", "성공" if housing_ok else "실패")
    logger.info("공공시설 데이터: %s", "성공" if infra_ok else "실패")
    logger.info("실거래 데이터: %s", "성공" if rtms_ok else "실패")
    
    return housing_ok and infra_ok and rtms_ok

def main():
    import argparse
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_HOST", "localhost")
    os.environ.setdefault("PG_PORT", "5432")
    os.environ.setdefault("PG_DB", "rey")
    os.environ.setdefault("DATABASE_URL", "")

    parser = argparse.ArgumentParser(description="data-load: 데이터를 DB에 적재")
    parser.add_argument("--db-url", type=str, help="데이터베이스 URL (미지정시 PG_*로 조립)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")

    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    p_housing = subparsers.add_parser("housing", help="주택 데이터 로드")
    p_housing.add_argument("--data-dir", type=str, default="backend/data/normalized",
                           help="정규화된 데이터 루트 경로 (기본: backend/data/normalized)")

    p_rtms = subparsers.add_parser("rtms", help="RTMS 데이터 로드")
    p_rtms.add_argument("--data-dir", type=str, default="backend/data/normalized",
                        help="정규화된 데이터 루트 경로 (기본: backend/data/normalized)")

    p_infra = subparsers.add_parser("infra", help="공공시설 데이터 로드")
    p_infra.add_argument("--data-dir", type=str, default="backend/data/normalized",
                        help="정규화된 데이터 루트 경로 (기본: backend/data/normalized)")

    p_all = subparsers.add_parser("all", help="모든 데이터 로드")
    p_all.add_argument("--data-dir", type=str, default="backend/data/normalized",
                       help="정규화된 데이터 루트 경로 (기본: backend/data/normalized)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    db_url = _resolve_db_url(args.db_url)

    success = False
    if args.command == "housing":
        success = load_housing_data(args.data_dir, db_url)
    elif args.command == "rtms":
        success = load_rtms_data(args.data_dir, db_url)
    elif args.command == "infra":
        success = load_infra_data(args.data_dir, db_url)
    elif args.command == "all":
        success = load_normalized_data(args.data_dir, db_url)

    if success:
        logger.info("%s 데이터 적재가 성공적으로 완료되었습니다.", args.command)
        sys.exit(0)
    else:
        logger.error("%s 데이터 적재에 실패했습니다.", args.command)
        sys.exit(1)

if __name__ == "__main__":
    main()
