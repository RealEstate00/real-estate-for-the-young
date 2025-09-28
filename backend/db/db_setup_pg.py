# db/db_setup_pg.py
# Apply postgresql/schema.sql to PostgreSQL. No emojis in comments.
from pathlib import Path
from sqlalchemy import text
from db.db_utils_pg import get_engine

def setup_schema():
    """PostgreSQL 스키마 적용"""
    # 스키마 파일들을 순서대로 정의
    schema_files = [
        Path("backend/db/schema_setup.sql"),           # 기본 스키마 설정
        Path("backend/db/housing/housing_schema.sql"), # 주택 스키마
        Path("backend/db/infra/infra_schema.sql"),     # 인프라 스키마
        Path("backend/db/infra/rtms_schema.sql")       # RTMS 스키마
    ]
    
    # 존재하지 않는 파일들 필터링
    existing_files = [f for f in schema_files if f.exists()]
    
    if not existing_files:
        print("❌ 스키마 파일이 없습니다.")
        return False
    
    print(f"📁 적용할 스키마 파일들: {[f.name for f in existing_files]}")
    
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
            for schema_file in existing_files:
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


