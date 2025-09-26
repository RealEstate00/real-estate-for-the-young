"""
공공시설 데이터 로더
CSV 데이터를 공공시설 테이블에 저장하는 모듈
"""
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

class InfraDataLoader:
    """공공시설 데이터를 DB에 로드하는 클래스"""
    
    def __init__(self, db_url: str = None):
        load_dotenv()
        self.db_url = db_url or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL이 설정되지 않았습니다.")
        
        self.engine = create_engine(self.db_url)
        self.connection = self.engine.connect()
    
    def load_all_infra(self):
        """모든 공공시설 데이터를 로드"""
        try:
            # 1. LocalData 시설들 로드
            self._load_localdata_facilities()

            # 2. OpenSeoul 시설들 로드
            self._load_openseoul_facilities()

            logger.info("모든 공공시설 데이터 로드 완료")
            return True

        except Exception as e:
            logger.error(f"공공시설 데이터 로드 실패: {e}")
            return False
        finally:
            self.connection.close()
    
    def _load_localdata_facilities(self):
        """LocalData CSV 파일들을 로드"""
        localdata_dir = Path(__file__).parent.parent.parent.parent / "data" / "api_pull" / "localdata"
        
        # 병원 데이터
        hospital_file = localdata_dir / "utf8_서울시병원_내과소아과응급의학과의학과.csv"
        if hospital_file.exists():
            self._load_hospitals(hospital_file)
        
        # 마트 데이터
        mart_file = localdata_dir / "utf8_서울시 마트.csv"
        if mart_file.exists():
            self._load_marts(mart_file)
        
        # 편의점 데이터
        convenience_file = localdata_dir / "utf8_서울시 편의점.csv"
        if convenience_file.exists():
            self._load_convenience_stores(convenience_file)
        
        # 체육시설 데이터
        gym_file = localdata_dir / "utf8_서울시 공공체육시설 정보.csv"
        if gym_file.exists():
            self._load_gyms(gym_file)
    
    def _load_openseoul_facilities(self):
        """OpenSeoul CSV 파일들을 로드"""
        openseoul_dir = Path(__file__).parent.parent.parent.parent / "data" / "api_pull" / "openseoul"
        
        # 어린이집 데이터
        childcare_file = openseoul_dir / "seoul_ChildCareInfo_20250919.csv"
        if childcare_file.exists():
            self._load_childcare_centers(childcare_file)
        
        # 학교 데이터
        school_files = [
            "seoul_childSchoolInfo_20250919.csv",
            "seoul_neisSchoolInfo_20250919.csv"
        ]
        for school_file in school_files:
            file_path = openseoul_dir / school_file
            if file_path.exists():
                self._load_schools(file_path)
        
        # 공원 데이터
        park_file = openseoul_dir / "seoul_SearchParkInfoService_20250919.csv"
        if park_file.exists():
            self._load_parks(park_file)
        
        # 지하철역 데이터
        subway_file = openseoul_dir / "seoul_SearchSTNBySubwayLineInfo_20250919.csv"
        if subway_file.exists():
            self._load_subway_stations(subway_file)
        
        # 약국 데이터
        pharmacy_file = openseoul_dir / "seoul_TbPharmacyOperateInfo_20250919.csv"
        if pharmacy_file.exists():
            self._load_pharmacies(pharmacy_file)
    
    def _load_hospitals(self, file_path: Path):
        """병원 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"병원 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('hospital'),
                'name': str(row.get('의료기관명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': False,  # 기본값
                'is_emergency': '응급실' in str(row.get('진료과목', '')),
                'capacity': None,  # 기본값
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'medical_departments': str(row.get('진료과목', '')),
                    'hospital_type': str(row.get('의료기관종별', ''))
                },
                'data_source': 'localdata'
            }
            self._insert_facility(facility_data)
    
    def _load_marts(self, file_path: Path):
        """마트 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"마트 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('mart'),
                'name': str(row.get('상호명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': False,  # 기본값
                'is_emergency': False,  # 기본값
                'capacity': None,  # 기본값
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'mart_type': str(row.get('업태', '')),
                    'business_hours': str(row.get('영업시간', ''))
                },
                'data_source': 'localdata'
            }
            self._insert_facility(facility_data)
    
    def _load_convenience_stores(self, file_path: Path):
        """편의점 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"편의점 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('convenience'),
                'name': str(row.get('상호명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': '24시간' in str(row.get('영업시간', '')),
                'is_emergency': False,  # 기본값
                'capacity': None,  # 기본값
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'brand': str(row.get('브랜드', '')),
                    'business_hours': str(row.get('영업시간', ''))
                },
                'data_source': 'localdata'
            }
            self._insert_facility(facility_data)
    
    def _load_gyms(self, file_path: Path):
        """체육시설 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"체육시설 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('gym'),
                'name': str(row.get('시설명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': False,  # 기본값
                'is_emergency': False,  # 기본값
                'capacity': None,  # 기본값
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'facility_type': str(row.get('시설종류', '')),
                    'sports_type': str(row.get('종목', ''))
                },
                'data_source': 'localdata'
            }
            self._insert_facility(facility_data)
    
    def _load_childcare_centers(self, file_path: Path):
        """어린이집 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"어린이집 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('kindergarten'),
                'name': str(row.get('어린이집명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': False,  # 기본값
                'is_emergency': False,  # 기본값
                'capacity': self._parse_int(row.get('정원', 0)),
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'director_name': str(row.get('원장명', '')),
                    'establishment_date': str(row.get('설립일', '')),
                    'operation_type': str(row.get('운영형태', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_schools(self, file_path: Path):
        """학교 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"학교 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('school'),
                'name': str(row.get('학교명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': False,  # 기본값
                'is_emergency': False,  # 기본값
                'capacity': self._parse_int(row.get('학생수', 0)),
                'grade_level': str(row.get('학교급', '')),
                'facility_extra': {
                    'school_type': str(row.get('학교유형', '')),
                    'establishment_date': str(row.get('설립일', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_parks(self, file_path: Path):
        """공원 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"공원 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('park'),
                'name': str(row.get('공원명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': None,  # 기본값
                'is_24h': False,  # 기본값
                'is_emergency': False,  # 기본값
                'capacity': None,  # 기본값
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'park_type': str(row.get('공원구분', '')),
                    'area': str(row.get('면적', '')),
                    'facilities': str(row.get('시설물', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_subway_stations(self, file_path: Path):
        """지하철역 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"지하철역 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            station_data = {
                'station_name': str(row.get('역명', '')),
                'line_name': str(row.get('노선명', '')),
                'station_code': str(row.get('역코드', '')),
                'address_raw': str(row.get('주소', '')),
                'is_transfer': '환승' in str(row.get('노선명', '')),
                'station_extra': {
                    'station_number': str(row.get('역번호', '')),
                    'operation_status': str(row.get('운영상태', ''))
                }
            }
            self._insert_subway_station(station_data)
    
    def _load_pharmacies(self, file_path: Path):
        """약국 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"약국 데이터 로드: {len(df)}개")
        
        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('pharmacy'),
                'name': str(row.get('약국명', '')),
                'address_raw': str(row.get('주소', '')),
                'phone': str(row.get('전화번호', '')),
                'is_24h': '24시간' in str(row.get('운영시간', '')),
                'is_emergency': False,  # 기본값
                'capacity': None,  # 기본값
                'grade_level': None,  # 기본값
                'facility_extra': {
                    'pharmacist_name': str(row.get('약사명', '')),
                    'business_hours': str(row.get('운영시간', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _get_category_id(self, category_code: str) -> int:
        """카테고리 코드로 ID 조회"""
        query = "SELECT id FROM infra.facility_categories WHERE code = :code"
        result = self.connection.execute(text(query), {'code': category_code}).fetchone()
        return result[0] if result else 1  # 기본값 1
    
    def _insert_facility(self, facility_data: Dict):
        """공공시설 데이터 삽입"""
        query = """
        INSERT INTO infra.public_facilities 
        (category_id, name, address_raw, phone, is_24h, is_emergency, capacity, 
         grade_level, facility_extra, data_source, created_at)
        VALUES 
        (:category_id, :name, :address_raw, :phone, :is_24h, :is_emergency, :capacity,
         :grade_level, :facility_extra, :data_source, now())
        ON CONFLICT DO NOTHING
        """
        
        # JSONB 필드 처리
        facility_data['facility_extra'] = json.dumps(facility_data.get('facility_extra', {}), ensure_ascii=False)
        
        self.connection.execute(text(query), facility_data)
    
    def _insert_subway_station(self, station_data: Dict):
        """지하철역 데이터 삽입"""
        query = """
        INSERT INTO infra.subway_stations 
        (station_name, line_name, station_code, address_raw, is_transfer, 
         transfer_lines, station_extra, created_at)
        VALUES 
        (:station_name, :line_name, :station_code, :address_raw, :is_transfer,
         :transfer_lines, :station_extra, now())
        ON CONFLICT DO NOTHING
        """
        
        # JSONB 필드 처리
        station_data['station_extra'] = json.dumps(station_data.get('station_extra', {}), ensure_ascii=False)
        station_data['transfer_lines'] = []  # 기본값
        
        self.connection.execute(text(query), station_data)
    
    def _parse_int(self, value) -> Optional[int]:
        """정수 파싱"""
        try:
            return int(float(str(value))) if str(value) != 'nan' else None
        except (ValueError, TypeError):
            return None

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='공공시설 데이터를 DB에 적재')
    parser.add_argument(
        '--db-url',
        type=str,
        help='데이터베이스 URL (기본값: DATABASE_URL 환경변수 사용)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    # 시설 데이터 로드
    loader = InfraDataLoader(db_url=args.db_url)
    success = loader.load_all_infra()
    
    if success:
        print("✅ 공공시설 데이터 로드 성공")
        return 0
    else:
        print("❌ 공공시설 데이터 로드 실패")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
