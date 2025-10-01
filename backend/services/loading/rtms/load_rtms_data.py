"""
RTMS 실거래가 데이터 로드 스크립트

정규화된 JSONL 파일을 읽어서 PostgreSQL 데이터베이스에 저장합니다.
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
from typing import List, Dict
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RTMSDataLoader:
    """RTMS 실거래 데이터 로더 (JSONL → PostgreSQL)"""
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Args:
            db_config: 데이터베이스 연결 설정
                - host: DB 호스트
                - port: DB 포트
                - database: DB 이름
                - user: DB 사용자
                - password: DB 비밀번호
        """
        self.db_config = db_config
        self.conn = None
        
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("데이터베이스 연결 성공")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            logger.info("데이터베이스 연결 종료")
    
    def create_schema(self):
        """스키마 생성"""
        # 현재: backend/services/loading/rtms/load_rtms_data.py
        # 목표: backend/services/db/schema/rtms_schema.sql
        current_file = Path(__file__)  # load_rtms_data.py
        services_dir = current_file.parent.parent.parent  # backend/services/
        schema_file = services_dir / 'db' / 'schema' / 'rtms_schema.sql'
        
        if not schema_file.exists():
            logger.error(f"스키마 파일을 찾을 수 없습니다: {schema_file}")
            logger.info("스키마 생성을 건너뜁니다. 수동으로 스키마를 생성해주세요.")
            return
        
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with self.conn.cursor() as cur:
                cur.execute(schema_sql)
                self.conn.commit()
            
            logger.info("스키마 생성 완료")
        except Exception as e:
            logger.error(f"스키마 생성 실패: {e}")
            self.conn.rollback()
            raise
    
    def load_jsonl_file(self, jsonl_path: Path, batch_size: int = 10000):
        """
        JSONL 파일을 읽어서 데이터베이스에 로드
        
        Args:
            jsonl_path: JSONL 파일 경로
            batch_size: 배치 크기
        """
        logger.info(f"파일 로드 시작: {jsonl_path.name}")
        
        try:
            # JSONL 읽기
            records = []
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            
            total_records = len(records)
            logger.info(f"총 {total_records:,}개 레코드 읽음")
            
            # 데이터베이스에 삽입
            self._insert_batch(records, batch_size)
            
            logger.info(f"파일 로드 완료: {jsonl_path.name}")
            
        except Exception as e:
            logger.error(f"파일 로드 실패 ({jsonl_path.name}): {e}")
            raise
    
    def _insert_batch(self, records: List[Dict], batch_size: int):
        """배치 삽입"""
        insert_query = """
            INSERT INTO rtms.transactions_rent (
                building_type, sigungudong, emd_code, road_address, building_name,
                area_type, area_m2, area_range, floor,
                contract_type, contract_year_month,
                contract_status, contract_start_ym, contract_end_ym,
                deposit_amount, monthly_rent,
                converted_price, construction_year
            ) VALUES (
                %(building_type)s, %(sigungudong)s, %(emd_code)s, %(road_address)s, %(building_name)s,
                %(area_type)s, %(area_m2)s, %(area_range)s, %(floor)s,
                %(contract_type)s, %(contract_year_month)s,
                %(contract_status)s, %(contract_start_ym)s, %(contract_end_ym)s,
                %(deposit_amount)s, %(monthly_rent)s,
                %(converted_price)s, %(construction_year)s
            )
        """
        
        try:
            with self.conn.cursor() as cur:
                total_inserted = 0
                
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    execute_batch(cur, insert_query, batch)
                    self.conn.commit()
                    
                    total_inserted += len(batch)
                    logger.info(f"진행률: {total_inserted:,} / {len(records):,} ({total_inserted/len(records)*100:.1f}%)")
            
            logger.info(f"총 {total_inserted:,}개 행 삽입 완료")
            
        except Exception as e:
            logger.error(f"데이터 삽입 실패: {e}")
            self.conn.rollback()
            raise
    
    def clear_existing_data(self):
        """기존 데이터 삭제 (테이블 구조는 유지)"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE rtms.transactions_rent CASCADE")
                self.conn.commit()
                logger.info("기존 데이터 삭제 완료")
        except Exception as e:
            logger.error(f"기존 데이터 삭제 실패: {e}")
            self.conn.rollback()
            raise

    def load_all_files(self, normalized_dir: Path, batch_size: int = 10000):
        """모든 RTMS JSONL 파일 로드"""
        jsonl_files = [
            '단독다가구_rent.jsonl',
            '아파트_rent.jsonl',
            '연립다세대_rent.jsonl',
            '오피스텔_rent.jsonl',
        ]
        
        for filename in jsonl_files:
            jsonl_path = normalized_dir / filename
            
            if not jsonl_path.exists():
                logger.warning(f"파일을 찾을 수 없습니다: {jsonl_path}")
                continue
            
            self.load_jsonl_file(jsonl_path, batch_size)
    
    def refresh_materialized_views(self):
        """MATERIALIZED VIEW 갱신 (통계 데이터 재계산)"""
        try:
            with self.conn.cursor() as cur:
                logger.info("MATERIALIZED VIEW 갱신 시작...")
                cur.execute("SELECT rtms.refresh_statistics_rent()")
                self.conn.commit()
                logger.info("MATERIALIZED VIEW 갱신 완료")
        except Exception as e:
            logger.error(f"MATERIALIZED VIEW 갱신 실패: {e}")
            self.conn.rollback()
            raise
    
    def clear_and_load(self, normalized_dir: Path, batch_size: int = 10000):
        """기존 데이터 삭제 후 새로 로드"""
        logger.info("기존 데이터 삭제 시작...")
        self.clear_existing_data()
        
        logger.info("새 데이터 로드 시작...")
        self.load_all_files(normalized_dir, batch_size)
        
        logger.info("통계 테이블 갱신 시작...")
        self.refresh_materialized_views()


def main():
    """메인 실행 함수"""
    # 데이터베이스 설정 (환경변수에서 읽기)
    db_config = {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5432'),
        'database': os.getenv('PG_DB', 'rey'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'post1234'),
    }
    
    # 정규화된 JSONL 파일 디렉토리
    base_dir = Path(__file__).parent.parent.parent.parent
    normalized_dir = base_dir / 'data' / 'normalized' / 'rtms'
    
    # 로더 생성 및 실행
    loader = RTMSDataLoader(db_config)
    
    try:
        loader.connect()
        loader.create_schema()
        loader.clear_and_load(normalized_dir, batch_size=10000)
        
    except Exception as e:
        logger.error(f"데이터 로드 중 오류 발생: {e}")
        raise
    
    finally:
        loader.close()


if __name__ == '__main__':
    main()
