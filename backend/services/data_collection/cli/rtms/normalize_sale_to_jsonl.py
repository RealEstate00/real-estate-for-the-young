"""
RTMS 매매 데이터 정규화 CLI (향후 구현)

CSV 파일을 읽어서 스키마에 맞게 정규화한 후 JSONL 형식으로 저장합니다.

사용법:
    python backend/services/data_collection/cli/rtms/normalize_sale_to_jsonl.py
"""

import argparse
from pathlib import Path
import sys

# 정규화 모듈 임포트
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from backend.services.data_collection.rtms.normalized.sale_normalizer import SaleDataNormalizer


def main():
    parser = argparse.ArgumentParser(
        description='RTMS 매매 데이터 정규화 (CSV → JSONL) - 향후 구현',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
주의:
  현재 이 기능은 구현되지 않았습니다.
  매매 데이터 수집 후 구현 예정입니다.
"""
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='배치 크기 (기본: 10000)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🏢 RTMS 매매 데이터 정규화")
    print("="*80)
    print("\n⚠️  이 기능은 아직 구현되지 않았습니다.\n")
    print("📋 구현을 위해 필요한 작업:")
    print("  1. 매매 데이터 CSV 파일 수집")
    print("  2. 매매 전용 스키마 설계 (transactions_sale 테이블)")
    print("  3. 컬럼 매핑 정의")
    print("  4. 정규화 로직 구현")
    print("\n" + "="*80 + "\n")
    
    sys.exit(0)


if __name__ == '__main__':
    main()


