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
    
    def _safe_int(self, value) -> Optional[int]:
        """안전하게 정수로 변환"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """안전하게 실수로 변환"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None
    
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
        """LocalData CSV 파일들을 파일명 기반으로 자동 분류/적재"""
        localdata_dir = Path(__file__).parent.parent.parent.parent.parent / "backend" / "data" / "public-api" / "localdata"
        
        logger.info(f"LocalData 디렉토리 스캔: {localdata_dir}")
        if not localdata_dir.exists():
            logger.warning(f"LocalData 디렉토리가 존재하지 않습니다: {localdata_dir}")
            return
        
        # 파일명 기반 자동 분류
        for file_path in localdata_dir.glob("*.csv"):
            file_name = file_path.name
            logger.info(f"처리 중: {file_name}")
            
            if "편의점" in file_name:
                self._load_convenience_store(file_path)
            elif "마트" in file_name:
                self._load_mart(file_path)
            elif "공공체육시설" in file_name:
                self._load_sports_facility(file_path)
            elif "병원" in file_name:
                self._load_hospital(file_path)
            else:
                logger.warning(f"인식되지 않은 파일: {file_name}")
        
        logger.info("LocalData 로드 완료")
    
    def _load_openseoul_facilities(self):
        """정규화된 JSON 파일에서 데이터 로드"""
        normalized_dir = Path("backend/data/normalized")
        
        # 가장 최근의 infra 폴더 찾기
        infra_dirs = []
        if normalized_dir.exists():
            for item in normalized_dir.iterdir():
                if item.is_dir() and (item / "infra").exists():
                    infra_dirs.append(item)
        
        if not infra_dirs:
            logger.warning("정규화된 인프라 데이터를 찾을 수 없습니다. 먼저 정규화를 실행하세요.")
            logger.info("실행 명령어: data-collection normalized process --platform infra")
            return
        
        # 가장 최근 디렉토리 선택
        latest_dir = max(infra_dirs, key=lambda x: x.name)
        infra_json_file = latest_dir / "infra" / "facilities.json"
        
        if not infra_json_file.exists():
            logger.warning(f"정규화된 JSON 파일을 찾을 수 없습니다: {infra_json_file}")
            return
        
        logger.info(f"정규화된 데이터 로드: {infra_json_file}")
        
        try:
            import json
            with open(infra_json_file, 'r', encoding='utf-8') as f:
                normalized_data = json.load(f)
            
            # 공공시설 데이터 저장
            facilities = normalized_data.get('public_facilities', [])
            for facility in facilities:
                self._insert_facility(facility)
            
            # 지하철역 데이터 저장
            stations = normalized_data.get('subway_stations', [])
            for station in stations:
                self._insert_subway_station(station)
            
            logger.info(f"인프라 데이터 로드 완료: 시설 {len(facilities)}개, 지하철역 {len(stations)}개")
            
            # 실패한 주소 정규화 정보 출력
            failed_addresses = normalized_data.get('failed_addresses', [])
            if failed_addresses:
                logger.warning(f"주소 정규화 실패: {len(failed_addresses)}건")
            
        except Exception as e:
            logger.error(f"정규화된 데이터 로드 실패: {e}")
            return
    
    def _load_convenience_store(self, file_path: Path):
        """편의점 데이터 로드"""
        df = pd.read_csv(file_path, encoding="utf-8")
        logger.info(f"편의점 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                "category_id": self._get_category_id("convenience"),
                "name": str(row.get("사업장명", "")),
                "address_raw": str(row.get("소재지전체주소", "")),
                "address_id": str(row.get("소재지전체주소", "")),   # 정규화 후 매핑 필요
                "lat": str(row.get("좌표정보X(EPSG5174)", "")),
                "lon": str(row.get("좌표정보Y(EPSG5174)", "")),
                "phone": str(row.get("소재지전화", "")),
                "website": str(row.get("홈페이지", "")),
                "operating_hours": None,  # 운영시간 정보 없음
                "is_24h": False,  # 24시간 정보 없음
                "is_emergency": False,
                "capacity": None,
                "grade_level": None,
                "facility_extra": {},
                "data_source": "localdata"
            }
            self._insert_facility(facility_data)
    
    def _load_mart(self, file_path: Path):
        """마트 데이터 로드"""
        df = pd.read_csv(file_path, encoding="utf-8")
        logger.info(f"마트 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                "category_id": self._get_category_id("mart"),
                "name": str(row.get("사업장명", "")),
                "address_raw": str(row.get("소재지전체주소", "")),
                "address_id": str(row.get("소재지전체주소", "")),
                "lat": str(row.get("좌표정보X(EPSG5174)", "")),
                "lon": str(row.get("좌표정보Y(EPSG5174)", "")),
                "phone": str(row.get("소재지전화", "")),
                "website": None,  # 홈페이지 정보 없음
                "operating_hours": None,  # 운영시간 정보 없음
                "is_24h": False,  # 24시간 정보 없음
                "is_emergency": False,
                "capacity": None,
                "grade_level": None,
                "facility_extra": {
                    "업태구분명": str(row.get("업태구분명", ""))
                },
                "data_source": "localdata"
            }
            self._insert_facility(facility_data)
    
    def _load_sports_facility(self, file_path: Path):
        """공공체육시설 데이터 로드"""
        df = pd.read_csv(file_path, encoding="utf-8")
        logger.info(f"공공체육시설 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                "category_id": self._get_category_id("gym"),
                "name": str(row.get("시설명", "")),
                "address_raw": str(row.get("시설주소", "")),
                "address_id": str(row.get("시설주소", "")),
                "lat": None,  # 좌표 정보 없음
                "lon": None,  # 좌표 정보 없음
                "phone": str(row.get("연락처", "")),
                "website": str(row.get("홈페이지", "")),
                "operating_hours": str(row.get("운영시간_평일", "")),
                "is_24h": False,  # 24시간 정보 없음
                "is_emergency": False,
                "capacity": None,
                "grade_level": None,
                "facility_extra": {
                    "시설종류": str(row.get("시설종류", "")),
                    "시설면적": str(row.get("시설규모", "")),
                    "부대정보": str(row.get("시설편의시설", "")),
                    "주차정보": str(row.get("주차정보", "")),
                    "운영시간_평일": str(row.get("운영시간_평일", "")),
                    "운영시간_주말": str(row.get("운영시간_주말", "")),
                    "운영기관": str(row.get("운영기관", ""))
                },
                "data_source": "localdata"
            }
            self._insert_facility(facility_data)
    
    def _load_hospital(self, file_path: Path):
        """병원 데이터 로드"""
        df = pd.read_csv(file_path, encoding="utf-8")
        logger.info(f"병원 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                "category_id": self._get_category_id("hospital"),
                "name": str(row.get("사업장명", "")),
                "address_raw": str(row.get("소재지전체주소", "")),
                "address_id": str(row.get("소재지전체주소", "")),
                "lat": str(row.get("좌표정보X(EPSG5174)", "")),
                "lon": str(row.get("좌표정보Y(EPSG5174)", "")),
                "phone": str(row.get("소재지전화", "")),
                "website": None,  # 홈페이지 정보 없음
                "operating_hours": None,  # 운영시간 정보 없음
                "is_24h": False,  # 24시간 정보 없음
                "is_emergency": "응급" in str(row.get("진료과목내용명", "")),  # 응급 여부 체크
                "capacity": None,
                "grade_level": None,
                "facility_extra": {
                    "진료과목내용명": str(row.get("진료과목내용명", "")),
                    "의료기관종별명": str(row.get("의료기관종별명", ""))
                },
                "data_source": "localdata"
            }
            self._insert_facility(facility_data)
    
    def _load_childcare(self, file_path: Path):
        """어린이집 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"어린이집 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('childcare'),
                'name': str(row.get('CRNAME', '')),                 # 어린이집명
                'address_raw': str(row.get('CRADDR', '')),          # 원문 주소
                'address_id': str(row.get('CRADDR', '')),           # 정규화 주소 (전처리 후 사용)
                'lat': str(row.get('LA', '')),                      # 위도
                'lon': str(row.get('LO', '')),                      # 경도
                'phone': str(row.get('CRTELNO', '')),               # 전화번호
                'website': str(row.get('CRHOME', '')),              # 홈페이지
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': str(row.get('CRCAPAT', '')),            # 정원
                'grade_level': None,
                'facility_extra': {
                    'childcare_type': str(row.get('CRTYPENAME', ''))  # 어린이집 유형
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_kindergarten(self, file_path: Path):
        """유치원 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"유치원 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('kindergarten'),
                'name': str(row.get('KDGT_NM', '')),                # 유치원명
                'address_raw': str(row.get('ADDR', '')),            # 원문 주소
                'address_id': str(row.get('ADDR', '')),             # 정규화 주소
                'lat': None,
                'lon': None,
                'phone': str(row.get('TELNO', '')),                 # 전화번호
                'website': str(row.get('HMPG', '')),                # 홈페이지
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': str(row.get('MIX_TDL_CNT', '')),        # 혼합유아수
                'grade_level': None,
                'facility_extra': {
                    'foundation_type': str(row.get('FNDN_TYPE', ''))  # 설립유형
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_pharmacy(self, file_path: Path):
        """약국 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"약국 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('pharmacy'),
                'name': str(row.get('DUTYNAME', '')),               # 약국명
                'address_raw': str(row.get('DUTYADDR', '')),        # 원문 주소
                'address_id': str(row.get('DUTYADDR', '')),         # 정규화 주소
                'lat': str(row.get('WGS84LAT', '')),                # 위도
                'lon': str(row.get('WGS84LON', '')),                # 경도
                'phone': str(row.get('DUTYTEL1', '')),              # 전화번호
                'website': None,
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {},
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_school(self, file_path: Path):
        """초중고 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"초중고 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('school'),
                'name': str(row.get('SCHUL_NM', '')),               # 학교명
                'address_raw': str(row.get('ORG_RDNMA', '')),       # 원문 주소
                'address_id': str(row.get('ORG_RDNMA', '')),        # 정규화 주소
                'lat': None,
                'lon': None,
                'phone': str(row.get('ORG_TELNO', '')),             # 전화번호
                'website': str(row.get('HMPG_ADRES', '')),          # 홈페이지
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': str(row.get('SCHUL_KND_SC_NM', '')), # 학교급
                'facility_extra': {
                    'foundation': str(row.get('FOND_SC_NM', '')),
                    'special_class': str(row.get('INDST_SPECL_CCCCL_EXST_YN', '')),
                    'business_code': str(row.get('HS_GNRL_BUSNS_SC_NM', '')),
                    'purpose': str(row.get('SPCILY_PURPS_HS_ORD_NM', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_college(self, file_path: Path):
        """대학 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"대학 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('college'),
                'name': str(row.get('NAME_KOR', '')),               # 대학명
                'address_raw': str(row.get('ADD_KOR_ROAD', '')),    # 원문 주소
                'address_id': str(row.get('ADD_KOR_ROAD', '')),     # 정규화 주소
                'lat': None,
                'lon': None,
                'phone': str(row.get('TEL', '')),                   # 전화번호
                'website': str(row.get('HP', '')),                  # 홈페이지
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'category': str(row.get('CATE1_NAME', '')),
                    'branch': str(row.get('BRANCH', '')),
                    'type': str(row.get('TYPE', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)
    
    def _load_park(self, file_path: Path):
        """공원 데이터 로드"""
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"공원 데이터 로드: {len(df)}개")

        for _, row in df.iterrows():
            facility_data = {
                'category_id': self._get_category_id('park'),
                'name': str(row.get('P_PARK', '')),                 # 공원명
                'address_raw': str(row.get('P_ADDR', '')),          # 원문 주소
                'address_id': str(row.get('P_ADDR', '')),           # 정규화 주소
                'lat': str(row.get('LATITUDE', '')),                # 위도
                'lon': str(row.get('LONGITUDE', '')),               # 경도
                'phone': str(row.get('P_ADMINTEL', '')),            # 관리부서 전화번호
                'website': str(row.get('TEMPLATE_URL', '')),        # 관련 링크
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'content': str(row.get('P_LIST_CONTENT', '')),
                    'area': str(row.get('AREA', '')),
                    'guidance': str(row.get('GUIDANCE', '')),
                    'use_refer': str(row.get('USE_REFER', '')),
                    'admin_name': str(row.get('P_NAME', ''))
                },
                'data_source': 'openseoul'
            }
            self._insert_facility(facility_data)

    def _load_subway_stations(self, stn_file: Path, addr_file: Path):
        """지하철역 데이터 로드 (역정보 + 주소 CSV 매핑)"""
        df_stn = pd.read_csv(stn_file, encoding='utf-8')
        df_addr = pd.read_csv(addr_file, encoding='utf-8')

        # 주소 매핑 (역명 기준)
        addr_map = dict(zip(df_addr['STATION_NM'], df_addr['OLD_ADDR']))

        logger.info(f"지하철역 데이터 로드: {len(df_stn)}개")

        for idx, row in df_stn.iterrows():
            station_name = str(row.get("STATION_NM", ""))
            line_name = str(row.get("LINE_NUM", ""))

            # 주소 가져오기
            address_raw = addr_map.get(station_name, None)

            # 환승 체크 (역명이 중복되는 경우 True)
            is_transfer = df_stn.duplicated(subset=['STATION_NM'], keep=False)[idx]

            # 환승 노선 목록
            transfer_lines = df_stn[df_stn['STATION_NM'] == station_name]['LINE_NUM'].unique().tolist()

            station_data = {
                "station_name": station_name,
                "line_name": line_name,
                "station_code": str(row.get("STATION_CD", "")),
                "address_raw": address_raw,
                "address_id": None,  # 정규화 후 매핑 필요
                "lat": None,
                "lon": None,
                "exit_count": None,
                "is_transfer": bool(is_transfer),
                "transfer_lines": transfer_lines,
                "station_extra": {},   # ✅ 항상 빈 JSON으로 넣기
                "data_source": "seoul_subway"
            }

            self._insert_subway_station(station_data)

    def _get_category_id(self, category_code: str) -> int:
        """카테고리 코드로 ID 조회"""
        query = "SELECT id FROM infra.facility_categories WHERE code = :code"
        result = self.connection.execute(text(query), {'code': category_code}).fetchone()
        return result[0] if result else 1  # 기본값 1
    
    def _insert_facility(self, facility_data: Dict):
        """공공시설 데이터 삽입"""
        query = """
        INSERT INTO infra.public_facilities 
        (category_id, name, address_raw, address_id, lat, lon, phone, website, operating_hours, 
         is_24h, is_emergency, capacity, grade_level, facility_extra, data_source, created_at)
        VALUES 
        (:category_id, :name, :address_raw, :address_id, :lat, :lon, :phone, :website, :operating_hours,
         :is_24h, :is_emergency, :capacity, :grade_level, :facility_extra, :data_source, now())
        ON CONFLICT DO NOTHING
        """
        
        # JSONB 필드 처리
        facility_data['facility_extra'] = json.dumps(facility_data.get('facility_extra', {}), ensure_ascii=False)
        
        self.connection.execute(text(query), facility_data)
    
    def _insert_subway_station(self, station_data: Dict):
        """지하철역 데이터 삽입"""
        query = """
        INSERT INTO infra.subway_stations 
        (station_name, line_name, station_code, address_raw, address_id, lat, lon, 
         exit_count, is_transfer, transfer_lines, station_extra, data_source, created_at)
        VALUES 
        (:station_name, :line_name, :station_code, :address_raw, :address_id, :lat, :lon,
         :exit_count, :is_transfer, :transfer_lines, :station_extra, :data_source, now())
        ON CONFLICT DO NOTHING
        """
        
        # JSONB 필드 처리
        station_data['station_extra'] = json.dumps(station_data.get('station_extra', {}), ensure_ascii=False)
        station_data['transfer_lines'] = json.dumps(station_data.get('transfer_lines', []), ensure_ascii=False)

        self.connection.execute(text(query), station_data)
    

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

