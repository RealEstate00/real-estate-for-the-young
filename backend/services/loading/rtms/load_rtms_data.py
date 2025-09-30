"""
RTMS 실거래가 데이터 로드 스크립트

CSV 파일을 읽어서 PostgreSQL 데이터베이스에 저장합니다.
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RTMSDataLoader:
    """RTMS 실거래 데이터 로더"""
    
    # CSV 컬럼명 매핑
    COLUMN_MAPPING = {
        '단독다가구': {
            '시군구': 'sigungu',
            '전용면적(㎡)': 'area_m2',
            '계약구분': 'contract_type',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '건축년도': 'construction_year',
            '계약월': 'contract_month',
            '전용구분': 'use_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        },
        '아파트': {
            '시군구': 'sigungu',
            '법정동': 'dong',
            '아파트': 'building_name',
            '전용면적(㎡)': 'area_m2',
            '계약구분': 'contract_type',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '층': 'floor',
            '건축년도': 'construction_year',
            '계약월': 'contract_month',
            '전용구분': 'use_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        },
        '연립다세대': {
            '시군구': 'sigungu',
            '법정동': 'dong',
            '단지명': 'building_name',
            '전용면적(㎡)': 'area_m2',
            '계약구분': 'contract_type',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '층': 'floor',
            '건축년도': 'construction_year',
            '계약월': 'contract_month',
            '전용구분': 'use_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        },
        '오피스텔': {
            '시군구': 'sigungu',
            '법정동': 'dong',
            '단지명': 'building_name',
            '전용면적(㎡)': 'area_m2',
            '계약구분': 'contract_type',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '층': 'floor',
            '건축년도': 'construction_year',
            '계약월': 'contract_month',
            '전용구분': 'use_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        }
    }
    
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
        schema_file = Path(__file__).parent.parent.parent.parent / 'backend' / 'db' / 'postgresql' / 'schema.sql'
        
        if not schema_file.exists():
            logger.error(f"스키마 파일을 찾을 수 없습니다: {schema_file}")
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
    
    def load_csv_file(self, csv_path: Path, building_type: str, batch_size: int = 10000):
        """
        CSV 파일을 읽어서 데이터베이스에 로드
        
        Args:
            csv_path: CSV 파일 경로
            building_type: 주택유형 ('단독다가구', '아파트', '연립다세대', '오피스텔')
            batch_size: 배치 크기
        """
        logger.info(f"파일 로드 시작: {csv_path.name}")
        
        try:
            # CSV 읽기
            df = pd.read_csv(csv_path, encoding='utf-8')
            logger.info(f"총 {len(df):,}개 행 읽음")
            
            # 컬럼명 매핑
            column_map = self.COLUMN_MAPPING[building_type]
            df = df.rename(columns=column_map)
            
            # building_type과 area_type 추가
            df['building_type'] = building_type
            df['area_type'] = '전용면적'  # RTMS 데이터는 모두 전용면적
            
            # 데이터 정제
            df = self._clean_data(df, building_type)
            
            # 데이터베이스에 삽입
            self._insert_batch(df, batch_size)
            
            logger.info(f"파일 로드 완료: {csv_path.name}")
            
        except Exception as e:
            logger.error(f"파일 로드 실패 ({csv_path.name}): {e}")
            raise
    
    def _clean_data(self, df: pd.DataFrame, building_type: str) -> pd.DataFrame:
        """데이터 정제"""
        # NaN을 None으로 변환
        df = df.where(pd.notna(df), None)
        
        # '-' 를 None으로 변환
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            df[col] = df[col].replace('-', None)
        
        # 월세금이 없으면 0으로
        if 'monthly_rent' in df.columns:
            df['monthly_rent'] = df['monthly_rent'].fillna(0)
        else:
            df['monthly_rent'] = 0
        
        # 단독다가구는 층 정보 없음
        if building_type == '단독다가구':
            df['floor'] = None
            df['dong'] = None
            df['building_name'] = None
        
        return df
    
    def _insert_batch(self, df: pd.DataFrame, batch_size: int):
        """배치 삽입"""
        insert_query = """
            INSERT INTO rtms.transactions_rent (
                building_type, sigungu, dong, building_name,
                area_type, area_m2, floor, contract_type, contract_year_month,
                deposit_amount, monthly_rent, construction_year, contract_month,
                use_type, contract_start_ym, contract_end_ym
            ) VALUES (
                %(building_type)s, %(sigungu)s, %(dong)s, %(building_name)s,
                %(area_type)s, %(area_m2)s, %(floor)s, %(contract_type)s, %(contract_year_month)s,
                %(deposit_amount)s, %(monthly_rent)s, %(construction_year)s, %(contract_month)s,
                %(use_type)s, %(contract_start_ym)s, %(contract_end_ym)s
            )
            ON CONFLICT ON CONSTRAINT uq_rtms_transaction DO NOTHING
        """
        
        try:
            with self.conn.cursor() as cur:
                records = df.to_dict('records')
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
    
    def refresh_materialized_view(self):
        """Materialized View 갱신"""
        try:
            with self.conn.cursor() as cur:
                logger.info("Materialized View 갱신 중...")
                cur.execute("SELECT rtms.refresh_area_statistics_rent()")
                self.conn.commit()
                logger.info("Materialized View 갱신 완료")
        except Exception as e:
            logger.error(f"Materialized View 갱신 실패: {e}")
            self.conn.rollback()
            raise
    
    def load_all_files(self, rtms_dir: Path, batch_size: int = 10000):
        """모든 RTMS CSV 파일 로드"""
        file_mapping = {
            '단독다가구(전월세)_202009중순~202509중순.csv': '단독다가구',
            '아파트(전월세)_202009중순~202509중순.csv': '아파트',
            '연립다세대(전월세)_202009중순~202509중순.csv': '연립다세대',
            '오피스텔(전월세)_202009중순~202509중순.csv': '오피스텔',
        }
        
        for filename, building_type in file_mapping.items():
            csv_path = rtms_dir / filename
            
            if not csv_path.exists():
                logger.warning(f"파일을 찾을 수 없습니다: {csv_path}")
                continue
            
            self.load_csv_file(csv_path, building_type, batch_size)
        
        # Materialized View 갱신
        self.refresh_materialized_view()


def main():
    """메인 실행 함수"""
    # 데이터베이스 설정 (환경변수에서 읽기)
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'real_estate'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
    }
    
    # RTMS 데이터 디렉토리
    rtms_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'rtms'
    
    # 로더 생성 및 실행
    loader = RTMSDataLoader(db_config)
    
    try:
        loader.connect()
        loader.create_schema()
        loader.load_all_files(rtms_dir)
        
    except Exception as e:
        logger.error(f"데이터 로드 중 오류 발생: {e}")
        raise
    
    finally:
        loader.close()


if __name__ == '__main__':
    main()
