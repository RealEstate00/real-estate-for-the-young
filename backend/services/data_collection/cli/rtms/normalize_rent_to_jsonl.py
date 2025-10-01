"""
RTMS 전월세 데이터 정규화 CLI

CSV 파일을 읽어서 스키마에 맞게 정규화한 후 JSONL 형식으로 저장합니다.

사용법:
    python backend/services/data_collection/cli/rtms/normalize_rent_to_jsonl.py
    python backend/services/data_collection/cli/rtms/normalize_rent_to_jsonl.py --batch-size 5000
    python backend/services/data_collection/cli/rtms/normalize_rent_to_jsonl.py --raw-dir ./data/raw/rtms
"""

import argparse
from pathlib import Path
import sys

# 정규화 모듈 임포트
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from backend.services.data_collection.rtms.normalized.rent_normalizer import RentDataNormalizer


def main():
    parser = argparse.ArgumentParser(
        description='RTMS 전월세 데이터 정규화 (CSV → JSONL)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행
  python %(prog)s
  
  # 배치 크기 지정
  python %(prog)s --batch-size 5000
  
  # 사용자 지정 경로
  python %(prog)s --raw-dir /path/to/raw --output-dir /path/to/output
"""
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='배치 크기 (기본: 10000)'
    )
    parser.add_argument(
        '--raw-dir',
        type=str,
        help='원본 CSV 파일 디렉토리 (기본: backend/data/raw/rtms)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='출력 JSONL 파일 디렉토리 (기본: backend/data/normalized/rtms)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        default=True,
        help='중단된 작업 재개 (기본: True)'
    )
    
    args = parser.parse_args()
    
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent.parent
    raw_data_dir = Path(args.raw_dir) if args.raw_dir else base_dir / 'data' / 'raw' / 'rtms'
    normalized_dir = Path(args.output_dir) if args.output_dir else base_dir / 'data' / 'normalized' / 'rtms'
    bjdong_code_file = raw_data_dir / '법정동코드 전체자료.txt'
    
    # 디렉토리 존재 확인
    if not raw_data_dir.exists():
        print(f"❌ 오류: 원본 데이터 디렉토리를 찾을 수 없습니다: {raw_data_dir}")
        sys.exit(1)
    
    if not bjdong_code_file.exists():
        print(f"❌ 오류: 법정동 코드 파일을 찾을 수 없습니다: {bjdong_code_file}")
        sys.exit(1)
    
    # 정규화 실행
    try:
        print("\n" + "="*80)
        print("🏠 RTMS 전월세 데이터 정규화")
        print("="*80)
        print(f"📁 입력 디렉토리: {raw_data_dir}")
        print(f"📁 출력 디렉토리: {normalized_dir}")
        print(f"📦 배치 크기: {args.batch_size:,}")
        print(f"🔄 재개 모드: {'ON' if args.resume else 'OFF'}")
        print("="*80 + "\n")
        
        normalizer = RentDataNormalizer(raw_data_dir, normalized_dir, bjdong_code_file)
        normalizer.process_all_files(batch_size=args.batch_size)
        
        print("\n" + "="*80)
        print("✅ 정규화 완료!")
        print(f"📁 출력 디렉토리: {normalized_dir}")
        print("="*80 + "\n")
        
        print("📋 다음 단계:")
        print("  1. 정규화된 JSONL 파일 확인")
        print(f"     ls {normalized_dir}")
        print("  2. DB에 로드")
        print("     python backend/services/loading/rtms/load_rtms_data.py")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        print("💡 다시 실행하면 중단된 지점부터 재개됩니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

