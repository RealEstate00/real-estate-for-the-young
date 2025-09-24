#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
서울 열린데이터광장 API 데이터 정규화
7개 서비스 데이터를 DB 스키마에 맞게 변환
"""

import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SeoulDataNormalizer:
    """서울 열린데이터광장 API 데이터 정규화 클래스"""
    
    def __init__(self):
        self.normalized_data = {}
    
    def normalize_all_services(self, data_dir: Path) -> Dict[str, List[Dict]]:
        """모든 서비스 데이터를 정규화"""
        logger.info(f"서울 API 데이터 정규화 시작: {data_dir}")
        
        # 7개 서비스별 정규화
        services = [
            "ChildCareInfo",           # 어린이집
            "childSchoolInfo",         # 어린이학교
            "neisSchoolInfo",          # NEIS 학교정보
            "SearchSTNBySubwayLineInfo", # 지하철역
            "SearchParkInfoService",   # 공원
            "SebcCollegeInfoKor",      # 대학
            "TbPharmacyOperateInfo"    # 약국
        ]
        
        for service in services:
            csv_file = data_dir / f"seoul_{service}_20250919.csv"
            if csv_file.exists():
                logger.info(f"정규화 중: {service}")
                normalized = self._normalize_service(csv_file, service)
                self.normalized_data[service] = normalized
            else:
                logger.warning(f"파일 없음: {csv_file}")
        
        return self.normalized_data
    
    def _normalize_service(self, csv_file: Path, service_name: str) -> List[Dict]:
        """개별 서비스 데이터 정규화"""
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            logger.info(f"{service_name}: {len(df)}개 레코드 로드")
            
            if service_name == "ChildCareInfo":
                return self._normalize_childcare(df)
            elif service_name == "childSchoolInfo":
                return self._normalize_child_school(df)
            elif service_name == "neisSchoolInfo":
                return self._normalize_neis_school(df)
            elif service_name == "SearchSTNBySubwayLineInfo":
                return self._normalize_subway_station(df)
            elif service_name == "SearchParkInfoService":
                return self._normalize_park(df)
            elif service_name == "SebcCollegeInfoKor":
                return self._normalize_college(df)
            elif service_name == "TbPharmacyOperateInfo":
                return self._normalize_pharmacy(df)
            else:
                logger.error(f"알 수 없는 서비스: {service_name}")
                return []
                
        except Exception as e:
            logger.error(f"{service_name} 정규화 실패: {e}")
            return []
    
    def _normalize_childcare(self, df: pd.DataFrame) -> List[Dict]:
        """어린이집 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                # 주소 정규화
                address_raw = str(row.get('CRADDR', ''))
                address_norm = self._normalize_address(address_raw)
                
                # 좌표 정규화
                lat = self._safe_float(row.get('LA'))
                lon = self._safe_float(row.get('LO'))
                
                record = {
                    'source': 'seoul_childcare',
                    'source_key': str(row.get('STCODE', '')),
                    'name': str(row.get('CRNAME', '')),
                    'type': str(row.get('CRTYPENAME', '')),
                    'status': str(row.get('CRSTATUSNAME', '')),
                    'address_raw': address_raw,
                    'address_norm': address_norm,
                    'zipcode': str(row.get('ZIPCODE', '')),
                    'phone': str(row.get('CRTELNO', '')),
                    'fax': str(row.get('CRFAXNO', '')),
                    'homepage': str(row.get('CRHOME', '')),
                    'room_count': self._safe_int(row.get('NRTRROOMCNT')),
                    'room_size': self._safe_float(row.get('NRTRROOMSIZE')),
                    'capacity': self._safe_int(row.get('CRCAPAT')),
                    'child_count': self._safe_int(row.get('CRCHCNT')),
                    'lat': lat,
                    'lon': lon,
                    'si_do': '서울특별시',
                    'si_gun_gu': str(row.get('SIGUNNAME', '')),
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"어린이집 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_child_school(self, df: pd.DataFrame) -> List[Dict]:
        """어린이학교 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                address_raw = str(row.get('ADDR', ''))
                address_norm = self._normalize_address(address_raw)
                
                lat = self._safe_float(row.get('LAT'))
                lon = self._safe_float(row.get('LON'))
                
                record = {
                    'source': 'seoul_child_school',
                    'source_key': str(row.get('ATPT_OFCDC_SC_CODE', '')) + '_' + str(row.get('SD_SCHUL_CODE', '')),
                    'name': str(row.get('SCHUL_NM', '')),
                    'type': str(row.get('SCHUL_KND_SC_NM', '')),
                    'level': str(row.get('SCHUL_CRSE_SC_NM', '')),
                    'address_raw': address_raw,
                    'address_norm': address_norm,
                    'phone': str(row.get('ORG_TELNO', '')),
                    'homepage': str(row.get('HMPG_ADRES', '')),
                    'lat': lat,
                    'lon': lon,
                    'si_do': '서울특별시',
                    'si_gun_gu': str(row.get('ATPT_OFCDC_SC_NM', '')),
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"어린이학교 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_neis_school(self, df: pd.DataFrame) -> List[Dict]:
        """NEIS 학교정보 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                address_raw = str(row.get('ATPT_OFCDC_SC_NM', '')) + ' ' + str(row.get('SCHUL_NM', ''))
                address_norm = self._normalize_address(address_raw)
                
                record = {
                    'source': 'seoul_neis_school',
                    'source_key': str(row.get('ATPT_OFCDC_SC_CODE', '')) + '_' + str(row.get('SD_SCHUL_CODE', '')),
                    'name': str(row.get('SCHUL_NM', '')),
                    'type': str(row.get('SCHUL_KND_SC_NM', '')),
                    'level': str(row.get('SCHUL_CRSE_SC_NM', '')),
                    'address_raw': address_raw,
                    'address_norm': address_norm,
                    'phone': str(row.get('ORG_TELNO', '')),
                    'homepage': str(row.get('HMPG_ADRES', '')),
                    'si_do': '서울특별시',
                    'si_gun_gu': str(row.get('ATPT_OFCDC_SC_NM', '')),
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"NEIS 학교 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_subway_station(self, df: pd.DataFrame) -> List[Dict]:
        """지하철역 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                record = {
                    'source': 'seoul_subway',
                    'source_key': str(row.get('STATION_CD', '')),
                    'name': str(row.get('STATION_NM', '')),
                    'name_eng': str(row.get('STATION_NM_ENG', '')),
                    'name_chn': str(row.get('STATION_NM_CHN', '')),
                    'name_jpn': str(row.get('STATION_NM_JPN', '')),
                    'line_num': str(row.get('LINE_NUM', '')),
                    'fr_code': str(row.get('FR_CODE', '')),
                    'si_do': '서울특별시',
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"지하철역 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_park(self, df: pd.DataFrame) -> List[Dict]:
        """공원 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                address_raw = str(row.get('P_ADDR', ''))
                address_norm = self._normalize_address(address_raw)
                
                lat = self._safe_float(row.get('LATITUDE'))
                lon = self._safe_float(row.get('LONGITUDE'))
                
                record = {
                    'source': 'seoul_park',
                    'source_key': str(row.get('P_IDX', '')),
                    'name': str(row.get('P_PARK', '')),
                    'description': str(row.get('P_LIST_CONTENT', '')),
                    'area': self._safe_float(row.get('AREA')),
                    'open_date': str(row.get('OPEN_DT', '')),
                    'main_equipment': str(row.get('MAIN_EQUIP', '')),
                    'main_plants': str(row.get('MAIN_PLANTS', '')),
                    'guidance': str(row.get('GUIDANCE', '')),
                    'visit_road': str(row.get('VISIT_ROAD', '')),
                    'use_refer': str(row.get('USE_REFER', '')),
                    'address_raw': address_raw,
                    'address_norm': address_norm,
                    'phone': str(row.get('P_ADMINTEL', '')),
                    'lat': lat,
                    'lon': lon,
                    'si_do': '서울특별시',
                    'si_gun_gu': str(row.get('P_ZONE', '')),
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"공원 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_college(self, df: pd.DataFrame) -> List[Dict]:
        """대학 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                address_raw = str(row.get('ADDR', ''))
                address_norm = self._normalize_address(address_raw)
                
                lat = self._safe_float(row.get('LAT'))
                lon = self._safe_float(row.get('LON'))
                
                record = {
                    'source': 'seoul_college',
                    'source_key': str(row.get('ATPT_OFCDC_SC_CODE', '')) + '_' + str(row.get('SD_SCHUL_CODE', '')),
                    'name': str(row.get('SCHUL_NM', '')),
                    'type': str(row.get('SCHUL_KND_SC_NM', '')),
                    'level': str(row.get('SCHUL_CRSE_SC_NM', '')),
                    'address_raw': address_raw,
                    'address_norm': address_norm,
                    'phone': str(row.get('ORG_TELNO', '')),
                    'homepage': str(row.get('HMPG_ADRES', '')),
                    'lat': lat,
                    'lon': lon,
                    'si_do': '서울특별시',
                    'si_gun_gu': str(row.get('ATPT_OFCDC_SC_NM', '')),
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"대학 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_pharmacy(self, df: pd.DataFrame) -> List[Dict]:
        """약국 데이터 정규화"""
        normalized = []
        
        for _, row in df.iterrows():
            try:
                address_raw = str(row.get('DUTYADDR', ''))
                address_norm = self._normalize_address(address_raw)
                
                lat = self._safe_float(row.get('WGS84LAT'))
                lon = self._safe_float(row.get('WGS84LON'))
                
                record = {
                    'source': 'seoul_pharmacy',
                    'source_key': str(row.get('HOSID', '')),
                    'name': str(row.get('DUTYNAME', '')),
                    'type': '약국',
                    'address_raw': address_raw,
                    'address_norm': address_norm,
                    'phone': str(row.get('DUTYTEL1', '')),
                    'lat': lat,
                    'lon': lon,
                    'si_do': '서울특별시',
                    'si_gun_gu': str(row.get('SIGUN_NM', '')),
                    'created_at': datetime.now().isoformat(),
                    'raw_data': row.to_dict()
                }
                normalized.append(record)
                
            except Exception as e:
                logger.error(f"약국 레코드 정규화 실패: {e}")
                continue
        
        return normalized
    
    def _normalize_address(self, address: str) -> str:
        """주소 정규화 (간단한 버전)"""
        if not address or address == 'nan':
            return ''
        
        # 기본 정리
        address = str(address).strip()
        address = address.replace('  ', ' ')  # 중복 공백 제거
        
        return address
    
    def _safe_float(self, value) -> Optional[float]:
        """안전한 float 변환"""
        try:
            if pd.isna(value) or value == '' or value == 'nan':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """안전한 int 변환"""
        try:
            if pd.isna(value) or value == '' or value == 'nan':
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def save_normalized_data(self, output_dir: Path):
        """정규화된 데이터를 JSON으로 저장"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for service, data in self.normalized_data.items():
            output_file = output_dir / f"{service}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"{service}: {len(data)}개 레코드 저장 → {output_file}")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="서울 API 데이터 정규화")
    parser.add_argument("--data-dir", default="backend/data/public-api/openseoul", help="CSV 데이터 디렉토리")
    parser.add_argument("--output-dir", default="backend/data/normalized/seoul", help="정규화된 데이터 출력 디렉토리")
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 정규화 실행
    normalizer = SeoulDataNormalizer()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    if not data_dir.exists():
        logger.error(f"데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return
    
    # 정규화 실행
    normalized_data = normalizer.normalize_all_services(data_dir)
    
    # 결과 저장
    normalizer.save_normalized_data(output_dir)
    
    # 통계 출력
    total_records = sum(len(data) for data in normalized_data.values())
    logger.info(f"정규화 완료: {len(normalized_data)}개 서비스, 총 {total_records}개 레코드")


if __name__ == "__main__":
    main()





