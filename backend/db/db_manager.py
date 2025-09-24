# Entry point for "data-db ..." and "python -m backend.db.db_manager"
# Database management commands

import sys, os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from db.db_utils_pg import get_engine, test_connection
from db.db_setup_pg import setup_schema
from sqlalchemy import text

HELP = f"""data-db <command> [args]

Commands:
  create              Create database tables
  drop                Drop all tables (WARNING!)
  reset               Reset database (drop + create)
  list                List all tables
  structure <table>   Show table structure
  test                Test database connection
  db-create-load      Create DB and load

Examples:
  data-db create
  data-db list
  data-db structure bus_stops
  data-db test
"""

def create_tables():
    """테이블 생성"""
    print("[On Progress]  데이터베이스 테이블 생성 중...")
    try:
        # 1. 스키마 생성
        create_schemas()
        # 2. 테이블 생성
        setup_schema()
        print("[COMPLETE] 테이블 생성 완료!")
        return True
    except Exception as e:
        print(f"[FAILED] 테이블 생성 실패: {e}")
        return False

def create_schemas():
    """필요한 스키마들 생성"""
    print("📁 스키마 생성 중...")
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # 스키마 생성
            schemas = ['infra', 'housing', 'rtms']
            for schema in schemas:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                print(f"✅ {schema} 스키마 생성 완료")
            
            conn.commit()
        print("📁 모든 스키마 생성 완료!")
        return True
    except Exception as e:
        print(f"❌ 스키마 생성 실패: {e}")
        return False

def drop_tables():
    """모든 테이블 삭제 (주의!)"""
    print("🗑️  모든 테이블을 삭제합니다...")
    # 자동으로 확인 (CI/CD 환경에서 사용)
    
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # 외래키 제약조건 비활성화
            conn.execute(text("SET session_replication_role = replica;"))
            
            # housing 스키마의 모든 테이블 삭제
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'housing' 
                AND tablename NOT LIKE 'pg_%'
            """))
            
            tables = [row[0] for row in result]
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS housing.{table} CASCADE"))
                print(f"🗑️  housing.{table} 테이블 삭제")
            
            # 외래키 제약조건 재활성화
            conn.execute(text("SET session_replication_role = DEFAULT;"))
            conn.commit()
            
        print("[COMPLETE] 모든 테이블 삭제 완료!")
        return True
    except Exception as e:
        print(f"[FAILED] 테이블 삭제 실패: {e}")
        return False

def reset_database():
    """데이터베이스 초기화 (삭제 후 재생성)"""
    print("[On Progress] 데이터베이스 초기화 중...")
    if drop_tables():
        if create_tables():
            print("[COMPLETE] 데이터베이스 초기화 완료!")
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
                    t.table_schema,
                    t.table_name,
                    t.table_type,
                    COALESCE(s.n_tup_ins, 0) as row_count
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname
                WHERE t.table_schema IN ('housing', 'facilities')
                ORDER BY t.table_schema, t.table_name
            """))
            
            print("📊 데이터베이스 테이블 현황:")
            print("=" * 60)
            current_schema = None
            for row in result:
                table_schema, table_name, table_type, row_count = row
                if current_schema != table_schema:
                    current_schema = table_schema
                    print(f"\n📁 {table_schema} 스키마:")
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
            print("Usage: data-db structure <table_name>")
            sys.exit(1)
        show_table_structure(rest[0])
    elif cmd == "test":
        test_db()
    elif cmd == "db-create-load":
        # Import and run DB create and load
        import runpy
        sys.argv = ["backend.services.ingestion.cli.db_create_and_load"] + rest
        runpy.run_module("backend.services.ingestion.cli.db_create_and_load", run_name="__main__")
    else:
        print(f"Unknown command: {cmd}\n")
        print(HELP)
        sys.exit(2)

if __name__ == "__main__":
    main()
