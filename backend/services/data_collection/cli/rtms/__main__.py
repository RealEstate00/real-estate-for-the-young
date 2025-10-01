"""
RTMS (실거래가) 데이터 수집 CLI 메인 모듈
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.cli.rtms.rtms_normalized_cli import RTMSNormalizedCLI


def main():
    """메인 CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="RTMS (실거래가) 데이터 수집 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # normalized 서브커맨드
    normalized_parser = subparsers.add_parser('normalized', help='데이터 정규화')
    normalized_subparsers = normalized_parser.add_subparsers(dest='normalized_action', help='정규화 작업')
    
    # normalized process 서브커맨드
    process_parser = normalized_subparsers.add_parser('process', help='RTMS 데이터 정규화 실행')
    process_parser.add_argument('--building-type', choices=['단독다가구', '아파트', '연립다세대', '오피스텔'], 
                               help='특정 주택유형만 처리 (기본값: 전체)')
    process_parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'normalized':
            if args.normalized_action == 'process':
                cli = RTMSNormalizedCLI()
                cli.process_all(
                    building_type=args.building_type,
                    verbose=args.verbose
                )
            else:
                normalized_parser.print_help()
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
