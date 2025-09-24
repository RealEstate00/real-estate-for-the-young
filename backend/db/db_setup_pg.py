# db/db_setup_pg.py
# Apply postgresql/schema.sql to PostgreSQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from db.db_utils_pg import get_engine

def setup_schema():
    """PostgreSQL 스키마 적용"""
    # 새로운 스키마 파일들 사용
    schema_files = [
        "backend/db/schema_setup.sql",
        "backend/db/housing/housing_schema.sql"
    ] # =======jina
    # postgresql 디렉토리의 모든 .sql 파일 자동 감지
    postgresql_dir = Path("backend/db/postgresql")
    
    if not postgresql_dir.exists():
        print(f"❌ PostgreSQL 스키마 디렉토리를 찾을 수 없습니다: {postgresql_dir}")
        return False
    
    # .sql 파일들을 자동으로 찾기
    schema_files = list(postgresql_dir.glob("*.sql"))
    schema_files.sort()  # 알파벳 순으로 정렬 ==========inha
    
    if not schema_files:
        print(f"❌ {postgresql_dir}에 .sql 파일이 없습니다.")
        return False
    
    print(f"📁 발견된 스키마 파일들: {[f.name for f in schema_files]}")
    
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
            for schema_file in schema_files:
                print(f"📄 스키마 적용 중: {schema_file.name}")
                sql = schema_file.read_text(encoding="utf-8")
                conn.execute(text(sql))
                print(f"✅ {schema_file.name} 적용 완료")
                
        print("🎉 모든 PostgreSQL 스키마 적용 완료!")
        return True
    except Exception as e:
        print(f"❌ 스키마 적용 실패: {e}")
        return False

def main():
    """PostgreSQL 스키마 적용"""
    return setup_schema()

if __name__ == "__main__":
    main()


