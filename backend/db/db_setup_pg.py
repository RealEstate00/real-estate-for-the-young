# db/db_setup_pg.py
# Apply postgresql/schema.sql to PostgreSQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from db.db_utils_pg import get_engine

def setup_schema():
    """PostgreSQL 스키마 적용"""
<<<<<<< HEAD
    # 기존 스키마 사용
    sql_path = Path("db/postgresql/schema.sql")
    if not sql_path.exists():
        print(f"Schema file not found: {sql_path}")
        return False
    
    sql = sql_path.read_text(encoding="utf-8")
=======
    # 새로운 스키마 파일들 사용
    schema_files = [
        "backend/db/postgresql/schema_setup.sql",
        "backend/db/postgresql/housing_schema.sql", 
        "backend/db/postgresql/infra_schema.sql",
        "backend/db/postgresql/rtms_schema.sql"
    ]
    
>>>>>>> 23557d1 (feat:DB적재 완료)
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
<<<<<<< HEAD
            conn.execute(text(sql))
=======
            for schema_file in schema_files:
                sql_path = Path(schema_file)
                if not sql_path.exists():
                    print(f"Schema file not found: {sql_path}")
                    return False
                
                print(f"Applying schema: {schema_file}")
                sql = sql_path.read_text(encoding="utf-8")
                conn.execute(text(sql))
                
>>>>>>> 23557d1 (feat:DB적재 완료)
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


