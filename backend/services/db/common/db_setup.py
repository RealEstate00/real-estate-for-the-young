# db/db_setup_pg.py
# Apply postgresql/schema.sql to PostgreSQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from backend.services.db.common.db_utils import get_engine

def setup_schema():
    """PostgreSQL 스키마 적용"""
    # 스키마 파일 경로 설정 (상대 경로 사용)
    base_dir = Path(__file__).parent
    schema_files = [
        base_dir / "schema_setup.sql",
        base_dir.parent / "schema" / "housing_schema.sql",
        base_dir.parent / "schema" / "infra_schema.sql",
        base_dir.parent / "schema" / "rtms_schema.sql"
    ]
    
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
            for schema_file in schema_files:
                if not schema_file.exists():
                    print(f"Schema file not found: {schema_file}")
                    return False
                
                print(f"Applying schema: {schema_file}")
                sql = schema_file.read_text(encoding="utf-8")
                conn.execute(text(sql))
                
        print("PostgreSQL schema created/verified successfully.")
        return True
    except Exception as e:
        print(f"Error applying schema: {e}")
        return False

def main():
    """PostgreSQL 스키마 적용"""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("PostgreSQL 스키마 설정 도구")
        print("사용법: python -m backend.db.db_setup_pg")
        print("기능: PostgreSQL 데이터베이스에 housing 스키마를 생성/업데이트합니다.")
        return 0
    return setup_schema()

if __name__ == "__main__":
    exit(main())


