#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
인프라 데이터 정규화 CLI
===========================================
서울 열린데이터광장 API 데이터를 정규화하는 CLI
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from backend.libs.utils.paths import make_normalized_dir, INFRA_NORMALIZED_DIR

# 정규화 모듈 import
from backend.services.data_collection.infra.normalized.infra_normalizer_NoJusoAPI import InfraNormalizer

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def get_normalized_output_path(data_dir: Path) -> Path:
    """정규화된 데이터 출력 경로 생성"""
    return make_normalized_dir("infra")

def process_normalization(
    data_dir: Path,
    output_dir: Optional[Path] = None,
    verbose: bool = False
) -> None:
    """인프라 데이터 정규화 처리"""
    setup_logging(verbose)
    
    if not data_dir.exists():
        logger.error(f"데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return
    
    if output_dir is None:
        output_dir = get_normalized_output_path(data_dir)
    
    logger.info(f"📁 입력 데이터 디렉토리: {data_dir}")
    logger.info(f"📁 출력 디렉토리: {output_dir}")
    
    try:
        # 정규화 실행
        normalizer = InfraNormalizer(data_dir=data_dir)
        normalizer.normalize_openseoul_data(output_dir=output_dir, realtime_mode=True)
        
        logger.info("✅ 인프라 데이터 정규화 완료!")
        
    except Exception as e:
        logger.error(f"❌ 정규화 중 오류 발생: {e}")
        raise

def clean_normalized_data(date: str = None) -> None:
    """정규화된 데이터 정리"""
    normalized_dir = INFRA_NORMALIZED_DIR
    if date:
        normalized_dir = normalized_dir / date
    
    if normalized_dir.exists():
        import shutil
        shutil.rmtree(normalized_dir)
        print(f"🗑️  정규화된 데이터 삭제: {normalized_dir}")
    else:
        print(f"ℹ️  삭제할 데이터가 없습니다: {normalized_dir}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="인프라 데이터 정규화 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  data-collection-infra normalized process --data-dir backend/data/raw/api
  data-collection-infra normalized process --data-dir backend/data/raw/api --output-dir backend/data/normalized/infra
  data-collection-infra normalized clean
  data-collection-infra normalized clean --date 2024-01-01
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # process 명령어
    process_parser = subparsers.add_parser('process', help='인프라 데이터 정규화 실행')
    process_parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('backend/data/raw/api'),
        help='입력 데이터 디렉토리 경로 (기본값: backend/data/raw/api)'
    )
    process_parser.add_argument(
        '--output-dir',
        type=Path,
        help='정규화된 데이터 출력 디렉토리 (기본값: backend/data/normalized/infra)'
    )
    process_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    # clean 명령어
    clean_parser = subparsers.add_parser('clean', help='정규화된 데이터 정리')
    clean_parser.add_argument(
        '--date',
        help='삭제할 특정 날짜 (YYYY-MM-DD)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'process':
        process_normalization(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            verbose=args.verbose
        )
    elif args.command == 'clean':
        clean_normalized_data(date=args.date)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
