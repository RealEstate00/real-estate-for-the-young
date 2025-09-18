# db/db_setup_pg.py
# Apply postgresql/schema.sql to PostgreSQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from db.db_utils_pg import get_engine

def setup_schema():
    """PostgreSQL 스키마 적용"""
    # 기존 스키마 사용
    sql_path = Path("db/postgresql/schema.sql")
    if not sql_path.exists():
        print(f"Schema file not found: {sql_path}")
        return False
    
    sql = sql_path.read_text(encoding="utf-8")
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
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


