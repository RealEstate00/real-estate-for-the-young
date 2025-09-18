#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 실행 스크립트
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def get_engine():
    """PostgreSQL 엔진 생성"""
    host = os.getenv("PG_HOST", "localhost")
    port = int(os.getenv("PG_PORT", "5432"))
    user = os.getenv("PG_USER", "postgres")
    password = os.getenv("PG_PASSWORD", "post1234")
    db = os.getenv("PG_DB", "rey")
    
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url, pool_pre_ping=True)

def run_migration(migration_file: str):
    """마이그레이션 파일 실행"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # 트랜잭션 시작
            with conn.begin():
                # 마이그레이션 파일 읽기
                migration_path = Path(__file__).parent / "migrations" / migration_file
                
                if not migration_path.exists():
                    print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
                    return False
                
                with open(migration_path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # SQL 실행
                conn.execute(text(sql_content))
                print(f"✅ 마이그레이션 완료: {migration_file}")
                return True
                
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False

def list_migrations():
    """사용 가능한 마이그레이션 목록"""
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        print("마이그레이션 디렉토리가 없습니다.")
        return
    
    migration_files = sorted([f.name for f in migrations_dir.glob("*.sql")])
    print("📋 사용 가능한 마이그레이션:")
    for i, file in enumerate(migration_files, 1):
        print(f"  {i}. {file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python run_migration.py <migration_file>")
        print("예시: python run_migration.py 001_add_district_rating.sql")
        list_migrations()
        sys.exit(1)
    
    migration_file = sys.argv[1]
    run_migration(migration_file)
