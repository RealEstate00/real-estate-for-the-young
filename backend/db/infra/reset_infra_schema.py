"""
기존 DB 데이터 삭제 및 새 스키마 설정 스크립트
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def reset_database():
    """기존 데이터 삭제 및 새 스키마 설정"""
    
    # .env 파일에서 DB 연결 정보 가져오기
    db_host = os.getenv('PG_HOST', 'localhost')
    db_port = os.getenv('PG_PORT', '5432')
    db_name = os.getenv('PG_DB', 'rey')
    db_user = os.getenv('PG_USER', 'postgres')
    db_password = os.getenv('PG_PASSWORD', 'post1234')
    
    # 연결 문자열
    if db_password:
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        connection_string = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"
    
    print(f"=== DB 연결 정보 ===")
    print(f"Host: {db_host}:{db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'***' if db_password else 'None'}")
    print()
    
    try:
        # DB 연결
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            
            try:
                print("🗑️ 기존 데이터 삭제 중...")
                
                # 기존 스키마/테이블 삭제
                conn.execute(text("DROP SCHEMA IF EXISTS infra CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS addresses CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS facility_info CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS transport_points CASCADE;"))
                
                print("✅ 기존 데이터 삭제 완료")
                
                # 새 스키마 생성
                print("📋 새 스키마 생성 중...")
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS infra;"))
                
                print("✅ 스키마 생성 완료")
                
                # 스키마 파일 읽기 및 실행
                schema_file = Path(__file__).resolve().parent / "infra_schema.sql"
                
                if schema_file.exists():
                    print(f"📄 스키마 파일 실행 중: {schema_file}")
                    
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # SQL 실행
                    conn.execute(text(schema_sql))
                    print("✅ 스키마 파일 실행 완료")
                else:
                    print(f"❌ 스키마 파일을 찾을 수 없습니다: {schema_file}")
                
                # 트랜잭션 커밋
                trans.commit()
                print("🎉 DB 재설정 완료!")
                
                # 테이블 확인
                result = conn.execute(text("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'infra'
                    ORDER BY tablename;
                """)).fetchall()
                
                print("\n📊 생성된 테이블:")
                for row in result:
                    print(f"  - {row.schemaname}.{row.tablename}")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 오류 발생: {e}")
                raise
                
    except Exception as e:
        print(f"❌ DB 연결 오류: {e}")
        print("\n💡 해결 방법:")
        print("1. PostgreSQL이 실행 중인지 확인")
        print("2. .env 파일의 DB 연결 정보 확인")
        print("3. DB 사용자 권한 확인")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 DB 스키마 재설정 시작...")
    success = reset_database()
    
    if success:
        print("\n✅ 모든 작업이 완료되었습니다!")
        print("이제 JSONL 데이터를 로드할 수 있습니다.")
    else:
        print("\n❌ 작업이 실패했습니다.")
        sys.exit(1)
