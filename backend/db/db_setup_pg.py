# db/db_setup_pg.py
# Apply postgresql/schema.sql to PostgreSQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from db.db_utils_pg import get_engine

def setup_schema():
    """PostgreSQL 스키마 적용"""
    # 새로운 스키마 파일들 사용
    schema_files = [
        "backend/db/postgresql/schema_setup.sql",
        "backend/db/postgresql/housing_schema.sql", 
        "backend/db/postgresql/infra_schema.sql",
        "backend/db/postgresql/rtms_schema.sql"
    ]
    
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
            for schema_file in schema_files:
                sql_path = Path(schema_file)
                if not sql_path.exists():
                    print(f"Schema file not found: {sql_path}")
                    return False
                
                print(f"Applying schema: {schema_file}")
                sql = sql_path.read_text(encoding="utf-8")
                conn.execute(text(sql))
                
        print("PostgreSQL schema created/verified successfully.")
        return True
    except Exception as e:
        print(f"Error applying schema: {e}")
        return False

def main():
    """PostgreSQL 스키마 적용"""
    return setup_schema()

if __name__ == "__main__":
    main()
