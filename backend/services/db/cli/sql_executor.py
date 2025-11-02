"""SQL 파일 실행 CLI"""
import sys
import argparse
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.services.db.common.db_utils import execute_sql_file, get_engine, test_connection
from sqlalchemy import text

HELP = """sql-executor <sql_file> [options]

SQL 파일을 실행하는 유틸리티

Usage:
  sql-executor <sql_file>              # SQL 파일 실행
  sql-executor <sql_file> --dry-run    # 실행 전 구문 검사만
  sql-executor --test                  # DB 연결 테스트

Examples:
  sql-executor schema/infra_spatial_views.sql
  sql-executor schema/infra_spatial_views.sql --dry-run
  sql-executor --test
"""

def execute_sql(sql_file_path: str, dry_run: bool = False):
    """SQL 파일 실행"""
    sql_path = Path(sql_file_path)
    
    if not sql_path.exists():
        print(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file_path}")
        return False
    
    if not sql_path.suffix == '.sql':
        print(f"⚠️  경고: .sql 확장자가 아닙니다: {sql_file_path}")
    
    print(f"📄 SQL 파일 읽는 중: {sql_path}")
    
    if dry_run:
        print("🔍 [DRY RUN] 구문 검사만 수행합니다...")
        engine = get_engine()
        try:
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 간단한 구문 검사 (PostgreSQL이 실제로 검증)
            with engine.connect() as conn:
                # BEGIN으로 트랜잭션 시작하고 바로 ROLLBACK
                conn.execute(text("BEGIN"))
                try:
                    conn.execute(text(sql_content))
                finally:
                    conn.rollback()
            
            print("✅ 구문 검사 통과! (실제 실행은 하지 않았습니다)")
            return True
        except Exception as e:
            print(f"❌ 구문 오류 발견: {e}")
            return False
    else:
        print("🚀 SQL 파일 실행 중...")
        try:
            execute_sql_file(str(sql_path))
            print("✅ SQL 파일 실행 완료!")
            return True
        except Exception as e:
            print(f"❌ SQL 파일 실행 실패: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='SQL 파일 실행 유틸리티',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP
    )
    
    parser.add_argument(
        'sql_file',
        nargs='?',
        help='실행할 SQL 파일 경로'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 실행 없이 구문 검사만 수행'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='DB 연결 테스트'
    )
    
    args = parser.parse_args()
    
    # 환경 변수 설정
    import os
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_DB", "rey")
    
    if args.test:
        print("🔌 데이터베이스 연결 테스트 중...")
        if test_connection():
            print("✅ 데이터베이스 연결 성공!")
            return 0
        else:
            print("❌ 데이터베이스 연결 실패!")
            return 1
    
    if not args.sql_file:
        print(HELP)
        return 1
    
    success = execute_sql(args.sql_file, args.dry_run)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

