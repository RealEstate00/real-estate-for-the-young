# Entry point for "data-db ..." and "python -m backend.db.db_manager"
# Database management commands

import sys, os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.services.db.common.db_utils import get_engine, test_connection
from backend.services.db.common.db_setup import setup_schema
from sqlalchemy import text

HELP = f"""data-db <command> [args]

Commands:
  create              Create database tables
  drop [schema]       Drop tables (WARNING!)
                      - drop: Drop all tables
                      - drop housing: Drop housing schema tables
                      - drop infra: Drop infra schema tables
                      - drop rtms: Drop rtms schema tables
  reset               Reset database (drop + create)
  list                List all tables
  structure <table>   Show table structure
  test                Test database connection
  db-create-load      Create DB and load

Examples:
  data-db create
  data-db drop housing
  data-db drop infra
  data-db drop all
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

def drop_tables(schema_name=None):
    """테이블 삭제 (주의!)
    
    Args:
        schema_name: 삭제할 스키마명 (None이면 모든 스키마)
    """
    if schema_name:
        print(f"🗑️  {schema_name} 스키마의 모든 테이블을 삭제합니다...")
        schemas_to_drop = [schema_name]
    else:
        print("🗑️  모든 스키마의 테이블을 삭제합니다...")
        schemas_to_drop = ['housing', 'infra', 'rtms']
    
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # 외래키 제약조건 비활성화
            conn.execute(text("SET session_replication_role = replica;"))
            
            total_dropped = 0
            for schema in schemas_to_drop:
                # 해당 스키마의 모든 테이블 조회
                result = conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = :schema_name 
                    AND tablename NOT LIKE 'pg_%'
                """), {"schema_name": schema})
                
                tables = [row[0] for row in result]
                if tables:
                    print(f"📁 {schema} 스키마에서 {len(tables)}개 테이블 발견")
                    for table in tables:
                        conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE"))
                        print(f"🗑️  {schema}.{table} 테이블 삭제")
                        total_dropped += 1
                else:
                    print(f"📁 {schema} 스키마에 삭제할 테이블이 없습니다")
            
            # 외래키 제약조건 재활성화
            conn.execute(text("SET session_replication_role = DEFAULT;"))
            conn.commit()
            
        print(f"[COMPLETE] 총 {total_dropped}개 테이블 삭제 완료!")
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
                LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname AND t.table_schema = s.schemaname
                WHERE t.table_schema IN ('housing', 'infra', 'rtms')
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
        schema_name = rest[0] if rest else None
        if schema_name == "all":
            schema_name = None
        drop_tables(schema_name)
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
        # This command has been deprecated. Use 'data-db create' and 'data-load' separately.
        print("❌ 'db-create-load' 명령어는 더 이상 지원되지 않습니다.")
        print("💡 대신 다음 명령어를 사용하세요:")
        print("   data-db create    # 데이터베이스 생성")
        print("   data-load housing # 주택 데이터 로드")
        print("   data-load infra   # 공공시설 데이터 로드")
        sys.exit(1)
    else:
        print(f"Unknown command: {cmd}\n")
        print(HELP)
        sys.exit(2)

if __name__ == "__main__":
    main()