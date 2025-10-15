"""
벡터 데이터베이스 CLI - 간소화된 4파일 구조용
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .vector_client import VectorClient

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def format_similarity_color(similarity: float) -> str:
    """유사도에 따른 색상 표시"""
    if similarity >= 0.5:
        return f"\033[92m{similarity:.3f}\033[0m"  # 녹색
    elif similarity >= 0.3:
        return f"\033[93m{similarity:.3f}\033[0m"  # 노란색
    else:
        return f"\033[91m{similarity:.3f}\033[0m"  # 빨간색


def print_search_results(results, query: str):
    """검색 결과를 표 형태로 출력"""
    if not results:
        print("❌ No results found")
        return
    
    print(f"\n🔍 Search Results for: '{query}'")
    print("=" * 80)
    
    # 테이블 헤더
    print(f"{'Rank':<4} {'Housing Name':<25} {'Location':<20} {'Similarity':<12} {'Theme':<15}")
    print("-" * 80)
    
    # 결과 출력
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        housing_name = metadata.get('주택명', 'N/A')[:24]
        location = f"{metadata.get('시군구', '')} {metadata.get('동명', '')}"[:19]
        similarity = format_similarity_color(result['similarity'])
        theme = metadata.get('theme', '')[:14]
        
        print(f"{i:<4} {housing_name:<25} {location:<20} {similarity:<20} {theme:<15}")
    
    print("-" * 80)
    print(f"Total: {len(results)} results")


def print_statistics(stats):
    """통계 정보 출력"""
    print("\n📊 Vector Database Statistics")
    print("=" * 50)
    
    print(f"Total Housing Records: {stats['total_count']}")
    
    if stats.get('districts'):
        print(f"\nTop Districts:")
        print(f"{'District':<15} {'Count':<5}")
        print("-" * 20)
        for district, count in list(stats['districts'].items())[:10]:
            print(f"{district:<15} {count:<5}")
    
    if stats.get('themes'):
        print(f"\nTop Themes:")
        print(f"{'Theme':<15} {'Count':<5}")
        print("-" * 20)
        for theme, count in list(stats['themes'].items())[:10]:
            print(f"{theme:<15} {count:<5}")


def cmd_load_data(args):
    """데이터 로딩 명령"""
    client = VectorClient()
    
    if args.clear:
        print("🗑️  Clearing existing data...")
        client.clear_database()
    
    print("📥 Loading data to vector database...")
    try:
        client.load_csv_data(args.csv_path)
        print("✅ Data loaded successfully!")
        
        # 통계 출력
        stats = client.get_statistics()
        print(f"📊 Loaded {stats['total_count']} housing records")
        
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        sys.exit(1)


def cmd_search(args):
    """검색 명령"""
    client = VectorClient()
    
    try:
        results = client.search(
            query=args.query,
            n_results=args.limit,
            hybrid=args.hybrid,
            district=args.district,
            dong=args.dong,
            theme=args.theme,
            min_similarity=args.min_sim,
            smart_search=args.smart
        )
        
        print_search_results(results, args.query)
        
        if args.hybrid:
            print("\n💡 Used hybrid search (keyword + vector)")
        elif args.smart:
            print("\n🧠 Used smart search (auto keyword detection)")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        sys.exit(1)


def cmd_stats(args):
    """통계 명령"""
    client = VectorClient()
    
    try:
        stats = client.get_statistics()
        print_statistics(stats)
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")
        sys.exit(1)


def cmd_info(args):
    """정보 명령"""
    client = VectorClient()
    
    try:
        info = client.get_info()
        
        print("\n🔧 Vector Database Info")
        print("=" * 40)
        print(f"Persist Directory: {info['persist_directory']}")
        print(f"Embedding Model: {info['embedding_model']}")
        print(f"Total Collections: {info['total_collections']}")
        
        if info.get('housing_collection'):
            housing = info['housing_collection']
            print(f"\nHousing Collection:")
            print(f"  Name: {housing['name']}")
            print(f"  Records: {housing['count']}")
        
    except Exception as e:
        print(f"❌ Failed to get info: {e}")
        sys.exit(1)


def cmd_clear(args):
    """데이터베이스 초기화 명령"""
    print("⚠️  This will delete all data in the vector database!")
    confirm = input("Are you sure? (y/N): ")
    
    if confirm.lower() == 'y':
        client = VectorClient()
        client.clear_database()
        print("✅ Database cleared successfully!")
    else:
        print("❌ Operation cancelled")


def main():
    """메인 CLI 함수"""
    parser = argparse.ArgumentParser(
        description="Vector Database CLI for Housing Search (Simplified 4-file structure)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load data
  vector-db-inha load-data
  vector-db-inha load-data --clear --csv-path custom_data.csv
  
  # Search (Smart search is enabled by default)
  vector-db-inha search "강서구에 있는 주택 추천해줘"  # Auto-detects 강서구
  vector-db-inha search "홍대입구역 근처 청년주택"        # Auto-detects station + theme
  vector-db-inha search "반려동물 키울 수 있는 곳" --hybrid
  vector-db-inha search "주택" --district "강남구" --theme "청년형"
  vector-db-inha search "주택" --no-smart             # Disable smart search
  
  # Info
  vector-db-inha stats
  vector-db-inha info
  vector-db-inha clear
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # load-data 명령
    load_parser = subparsers.add_parser('load-data', help='Load housing data to vector database')
    load_parser.add_argument('--csv-path', '-c', 
                           default='backend/data/raw/for_vectorDB/housing_vector_data.csv',
                           help='Path to CSV file')
    load_parser.add_argument('--clear', action='store_true',
                           help='Clear existing data before loading')
    load_parser.set_defaults(func=cmd_load_data)
    
    # search 명령
    search_parser = subparsers.add_parser('search', help='Search housing data')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', '-n', type=int, default=10,
                             help='Number of results (default: 10)')
    search_parser.add_argument('--district', '-d', help='Filter by district')
    search_parser.add_argument('--dong', help='Filter by dong')
    search_parser.add_argument('--theme', '-t', help='Filter by theme')
    search_parser.add_argument('--hybrid', action='store_true',
                             help='Use hybrid search (keyword + vector)')
    search_parser.add_argument('--smart', action='store_true', default=True,
                             help='Use smart search with auto keyword detection (default: True)')
    search_parser.add_argument('--no-smart', dest='smart', action='store_false',
                             help='Disable smart search')
    search_parser.add_argument('--min-sim', type=float, default=0.0,
                             help='Minimum similarity threshold (0.0-1.0)')
    search_parser.set_defaults(func=cmd_search)
    
    # stats 명령
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # info 명령
    info_parser = subparsers.add_parser('info', help='Show database info')
    info_parser.set_defaults(func=cmd_info)
    
    # clear 명령
    clear_parser = subparsers.add_parser('clear', help='Clear all data (use with caution!)')
    clear_parser.set_defaults(func=cmd_clear)
    
    # 인수 파싱 및 실행
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 명령 실행
    args.func(args)


if __name__ == '__main__':
    main()
