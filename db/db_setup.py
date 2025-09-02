# scripts/db_setup.py
# Apply db/create_tables.sql to MySQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from db.db_utils import get_engine

def main():
    sql_path = Path("db/create_tables.sql")
    sql = sql_path.read_text(encoding="utf-8")
    eng = get_engine()
    with eng.begin() as conn:
        stmts = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in stmts:
            conn.execute(text(stmt))
    print("Schema created or verified.")

if __name__ == "__main__":
    main()
