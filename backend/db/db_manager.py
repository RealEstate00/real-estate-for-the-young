# Entry point for "sha-db ..." and "python -m backend.db.db_manager"
# Database management commands

import sys, os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from db.db_utils_pg import get_engine, test_connection
from db.db_setup_pg import setup_schema
from sqlalchemy import text

HELP = f"""sha-db <command> [args]

Commands:
  create              Create database tables
  drop                Drop all tables (WARNING!)
  reset               Reset database (drop + create)
  list                List all tables
  structure <table>   Show table structure
  test                Test database connection
  migrate-pg          Migrate data to PostgreSQL
  migrate-db          Generic migration script
  load-csv-mysql      Load CSV into MySQL
  load-mysql          Load into MySQL
  db-create-load      Create DB and load

Examples:
  sha-db create
  sha-db list
  sha-db structure bus_stops
  sha-db test
  sha-db migrate-pg
  sha-db load-mysql
"""

def create_tables():
    """테이블 생성"""
    print("🏗️  데이터베이스 테이블 생성 중...")
    try:
        setup_schema()
        print("✅ 테이블 생성 완료!")
        return True
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return False

def drop_tables():
    """모든 테이블 삭제 (주의!)"""
    print("⚠️  모든 테이블을 삭제합니다. 계속하시겠습니까? (y/N)")
    confirm = input().lower()
    if confirm != 'y':
        print("❌ 취소되었습니다.")
        return False
    
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # 외래키 제약조건 비활성화
            conn.execute(text("SET session_replication_role = replica;"))
            
            # 모든 테이블 삭제
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'pg_%'
            """))
            
            tables = [row[0] for row in result]
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"🗑️  {table} 테이블 삭제")
            
            # 외래키 제약조건 재활성화
            conn.execute(text("SET session_replication_role = DEFAULT;"))
            conn.commit()
            
        print("✅ 모든 테이블 삭제 완료!")
        return True
    except Exception as e:
        print(f"❌ 테이블 삭제 실패: {e}")
        return False

def reset_database():
    """데이터베이스 초기화 (삭제 후 재생성)"""
    print("🔄 데이터베이스 초기화 중...")
    if drop_tables():
        if create_tables():
            print("✅ 데이터베이스 초기화 완료!")
            return True
    return False

def show_tables():
    """테이블 목록 및 정보 표시"""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # 테이블 목록 조회
            result = conn.execute(text("""
                SELECT 
                    t.table_name,
                    t.table_type,
                    COALESCE(s.n_tup_ins, 0) as row_count
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname
                WHERE t.table_schema = 'public'
                ORDER BY t.table_name
            """))
            
            print("📊 데이터베이스 테이블 현황:")
            print("=" * 60)
            for row in result:
                table_name, table_type, row_count = row
                print(f"  • {table_name}: {row_count:,} rows ({table_type})")
                
    except Exception as e:
        print(f"❌ 테이블 정보 조회 실패: {e}")

def show_table_structure(table_name):
    """특정 테이블의 구조 표시"""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            
            print(f"📋 {table_name} 테이블 구조:")
            print("=" * 60)
            for row in result:
                col_name, data_type, nullable, default = row
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f", DEFAULT: {default}" if default else ""
                print(f"  • {col_name}: {data_type} {nullable_str}{default_str}")
                
    except Exception as e:
        print(f"❌ 테이블 구조 조회 실패: {e}")

def test_db():
    """데이터베이스 연결 테스트"""
    print("🔍 데이터베이스 연결 테스트 중...")
    if test_connection():
        print("✅ 데이터베이스 연결 성공!")
        return True
    else:
        print("❌ 데이터베이스 연결 실패!")
        return False

def main() -> None:
    # If no subcommand, print help.
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(HELP)
        sys.exit(0)

    cmd, rest = sys.argv[1], sys.argv[2:]
    
    # 환경 변수 설정
    import os
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_DB", "rey")
    
    if cmd == "create":
        create_tables()
    elif cmd == "drop":
        drop_tables()
    elif cmd == "reset":
        reset_database()
    elif cmd == "list":
        show_tables()
    elif cmd == "structure":
        if len(rest) < 1:
            print("Error: table name required for structure command")
            print("Usage: sha-db structure <table_name>")
            sys.exit(1)
        show_table_structure(rest[0])
    elif cmd == "test":
        test_db()
    elif cmd == "migrate-pg":
        # Import and run migration
        import runpy
        sys.argv = ["backend.services.data_collection.cli.migrate_to_postgresql"] + rest
        runpy.run_module("backend.services.data_collection.cli.migrate_to_postgresql", run_name="__main__")
    elif cmd == "migrate-db":
        # Import and run migration
        import runpy
        sys.argv = ["backend.services.data_collection.cli.migrate_database"] + rest
        runpy.run_module("backend.services.data_collection.cli.migrate_database", run_name="__main__")
    elif cmd == "load-csv-mysql":
        # Import and run CSV loading
        import runpy
        sys.argv = ["backend.services.data_collection.cli.load_csv_to_mysql"] + rest
        runpy.run_module("backend.services.data_collection.cli.load_csv_to_mysql", run_name="__main__")
    elif cmd == "load-mysql":
        # Import and run MySQL loading
        import runpy
        sys.argv = ["backend.services.data_collection.cli.load_to_mysql"] + rest
        runpy.run_module("backend.services.data_collection.cli.load_to_mysql", run_name="__main__")
    elif cmd == "db-create-load":
        # Import and run DB create and load
        import runpy
        sys.argv = ["backend.services.data_collection.cli.db_create_and_load"] + rest
        runpy.run_module("backend.services.data_collection.cli.db_create_and_load", run_name="__main__")
    else:
        print(f"Unknown command: {cmd}\n")
        print(HELP)
        sys.exit(2)

if __name__ == "__main__":
    main()
