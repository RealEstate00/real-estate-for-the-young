# DB 연결 테스트 스크립트

import os
import sys
import traceback

# 경로 설정
current_file = os.path.abspath(__file__)
services_dir = os.path.abspath(os.path.join(os.path.dirname(current_file), '..', '..', '..'))
services_dir = os.path.normpath(services_dir)

if services_dir not in sys.path:
    sys.path.insert(0, services_dir)

print("[INFO] DB 연결 테스트 시작")
print(f"[INFO] Services 디렉토리: {services_dir}")

# 1. 기본 PostgreSQL 연결 테스트
def test_basic_connection():
    print("\n=== 1. 기본 PostgreSQL 연결 테스트 ===")
    try:
        import psycopg2
        
        # 연결 정보
        conn_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }
        
        print(f"[TEST] 연결 시도: {conn_params}")
        
        # 연결 테스트
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # 간단한 쿼리 실행
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"[SUCCESS] PostgreSQL 버전: {version[0]}")
        
        # 스키마 확인
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'housing';")
        housing_schema = cursor.fetchone()
        if housing_schema:
            print(f"[SUCCESS] housing 스키마 존재: {housing_schema[0]}")
        else:
            print("[WARNING] housing 스키마가 존재하지 않습니다")
        
        # 테이블 확인
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'housing' 
            AND table_name IN ('notices', 'units');
        """)
        tables = cursor.fetchall()
        print(f"[INFO] housing 스키마의 테이블: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("[ERROR] psycopg2 라이브러리가 설치되지 않았습니다")
        print("[FIX] pip install psycopg2-binary 실행하세요")
        return False
    except Exception as e:
        print(f"[ERROR] PostgreSQL 연결 실패: {e}")
        print("[DEBUG] 상세 오류:")
        traceback.print_exc()
        return False

# 2. SQLAlchemy 연결 테스트
def test_sqlalchemy_connection():
    print("\n=== 2. SQLAlchemy 연결 테스트 ===")
    try:
        from sqlalchemy import create_engine, text
        
        # 연결 URI
        db_uri = "postgresql://postgres:post1234@localhost:5432/rey"
        print(f"[TEST] SQLAlchemy URI: {db_uri}")
        
        # 엔진 생성
        engine = create_engine(db_uri)
        
        # 연결 테스트
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_result = result.fetchone()
            print(f"[SUCCESS] SQLAlchemy 연결 성공: {test_result}")
            
            # 테이블 존재 확인
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'housing'
            """))
            tables = result.fetchall()
            print(f"[INFO] 발견된 테이블: {[t[0] for t in tables]}")
        
        return True
        
    except ImportError as e:
        print(f"[ERROR] SQLAlchemy 라이브러리 문제: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] SQLAlchemy 연결 실패: {e}")
        print("[DEBUG] 상세 오류:")
        traceback.print_exc()
        return False

# 3. LangChain SQLDatabase 연결 테스트
def test_langchain_sqldatabase():
    print("\n=== 3. LangChain SQLDatabase 연결 테스트 ===")
    try:
        from langchain_community.utilities import SQLDatabase
        
        db_uri = "postgresql://postgres:post1234@localhost:5432/rey"
        print(f"[TEST] LangChain SQLDatabase URI: {db_uri}")
        
        # SQLDatabase 객체 생성
        db = SQLDatabase.from_uri(
            db_uri,
            include_tables=["housing.notices", "housing.units"]
        )
        
        print(f"[SUCCESS] SQLDatabase 객체 생성 성공")
        print(f"[INFO] 포함된 테이블: {db.get_usable_table_names()}")
        
        # 스키마 정보 확인
        schema_info = db.get_table_info()
        print(f"[INFO] 스키마 정보 (처음 500자):")
        print(schema_info[:500] + "..." if len(schema_info) > 500 else schema_info)
        
        return True
        
    except ImportError as e:
        print(f"[ERROR] LangChain 라이브러리 문제: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] LangChain SQLDatabase 연결 실패: {e}")
        print("[DEBUG] 상세 오류:")
        traceback.print_exc()
        return False

# 4. 환경 변수 확인
def check_environment():
    print("\n=== 4. 환경 변수 확인 ===")
    
    env_vars = [
        'DATABASE_URL',
        'DB_HOST', 
        'DB_PORT',
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # 비밀번호는 마스킹
            if 'PASSWORD' in var or 'PASS' in var:
                value = '*' * len(value)
            print(f"[INFO] {var}: {value}")
        else:
            print(f"[INFO] {var}: 설정되지 않음")

def main():
    print("=" * 60)
    print("DB 연결 진단 도구")
    print("=" * 60)
    
    # 환경 변수 확인
    check_environment()
    
    # 연결 테스트들
    tests = [
        ("기본 PostgreSQL", test_basic_connection),
        ("SQLAlchemy", test_sqlalchemy_connection), 
        ("LangChain SQLDatabase", test_langchain_sqldatabase)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"[ERROR] {test_name} 테스트 중 예외 발생: {e}")
            results[test_name] = False
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")
    
    # 권장사항
    print("\n[권장사항]")
    if not any(results.values()):
        print("- PostgreSQL 서버가 실행 중인지 확인하세요")
        print("- 연결 정보(호스트, 포트, 데이터베이스명, 사용자명, 비밀번호)를 확인하세요")
        print("- 방화벽 설정을 확인하세요")
    elif not results.get("LangChain SQLDatabase", False):
        print("- LangChain 관련 라이브러리 버전을 확인하세요")
        print("- Python 3.13과 SQLAlchemy 호환성 문제일 수 있습니다")

if __name__ == "__main__":
    main()
