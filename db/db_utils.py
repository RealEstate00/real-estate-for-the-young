# db_utils.py
# Utility for MySQL connections via SQLAlchemy. No emojis in comments.
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

def get_engine():
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    pw   = os.getenv("MYSQL_PASSWORD", "")
    db   = os.getenv("MYSQL_DB", "SHA_bot")
    url = f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}?charset=utf8mb4"
    eng = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )
    return eng

def read_table(table_name: str, limit: int = 1000) -> pd.DataFrame:
    if not table_name.isidentifier():
        raise ValueError("Invalid table name")
    eng = get_engine()
    with eng.connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM {table_name} LIMIT :n"), conn, params={"n": limit})
