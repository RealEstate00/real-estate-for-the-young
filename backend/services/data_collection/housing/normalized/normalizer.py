#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
데이터 정규화 모듈 (Data Normalizer)
===========================================
raw 데이터를 정규화된 테이블 데이터로 변환하는 모듈
"""

import json
import logging
import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# 주소 API 활성화
from backend.services.data_collection.housing.normalized.address_api import normalize_address, AddressNormalizerError

logger = logging.getLogger(__name__)

# ===========================================
# 1) 유틸리티 함수들
# ===========================================

def preprocess_address(addr_raw: str) -> str:
    """주소 전처리 - JUSO API 매칭률 향상을 위한 정리"""
    if not addr_raw:
        return ""
    
    # 1. 기본 정리
    addr_raw = str(addr_raw).strip()
    
    # 2. 불필요한 접미사 제거
    addr_raw = re.sub(r'\s*\([^)]*\)\s*$', '', addr_raw)  # 괄호 안의 내용 제거
    addr_raw = re.sub(r'\s*\[[^\]]*\]\s*$', '', addr_raw)  # 대괄호 안의 내용 제거
    
    # 3. 불필요한 층수 정보 제거
    addr_raw = re.sub(r'\s+\d+\s*층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+전층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+\d+\s*~\s*\d+\s*층.*$', '', addr_raw)
    
    # 4. 건물명 제거 (괄호 안의 내용)
    addr_raw = re.sub(r'\s*\([^)]*\)\s*', ' ', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+생활.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+빌.*$', '', addr_raw)
    
    # 5. 공백 정리
    addr_raw = re.sub(r'\s+', ' ', addr_raw).strip()
    
    return addr_raw


# ===========================================
# 2) DataNormalizer 클래스
# ===========================================

class DataNormalizer:
    """데이터 정규화를 담당하는 메인 클래스"""
    
    def __init__(self):
        self.platforms = []
        self.addresses = []
        self.notices = []
        self.units = []
        self.unit_features = []
        self.notice_tags = []
        self.address_id_map = {}  # 주소 중복 체크를 위한 맵
        self.raw_data_dir = None
        
        # 새로운 정규화 클래스들 (notice_normalizer 제거 - 함수만 사용)
        
    # ===========================================
    # 2-1) 메인 정규화 메서드
    # ===========================================
        
    def normalize_raw_data(self, raw_csv_path: Path, save_callback=None) -> Dict[str, List[Dict]]:
        """
        raw CSV 데이터를 정규화된 테이블 데이터로 변환
        
        Args:
            raw_csv_path: raw CSV 파일 경로
            save_callback: 실시간 저장을 위한 콜백 함수
            
        Returns:
            정규화된 테이블 데이터 딕셔너리
        """
        logger.info(f"정규화 시작: {raw_csv_path}")
        
        # raw_data_dir 설정 (가장 최근 날짜의 raw 데이터 디렉토리)
        self.raw_data_dir = self._get_latest_raw_data_dir()
        
        # CSV 데이터 로드
        df = pd.read_csv(raw_csv_path)
        logger.info(f"로드된 레코드 수: {len(df)}")
        
        # 각 행 정규화
        for idx, row in df.iterrows():
            try:
                self._normalize_row(row)
                
                # 실시간 저장 (콜백이 제공된 경우)
                if save_callback and (idx + 1) % 100 == 0:
                    normalized_data = {
                        'platforms': self.platforms,
                        'addresses': self.addresses,
                        'notices': self.notices,
                        'units': self.units,
                        'unit_features': self.unit_features,
                        'notice_tags': self.notice_tags
                    }
                    save_callback(normalized_data, f"batch_{idx+1}")
                    
            except Exception as e:
                logger.error(f"행 {idx} 정규화 실패: {e}")
                continue
        
        # 정규화된 데이터 반환
        normalized_data = {
            'platforms': self.platforms,
            'addresses': self.addresses,
            'notices': self.notices,
            'units': self.units,
            'unit_features': self.unit_features,
            'notice_tags': self.notice_tags
        }
        
        # 새로운 기능들 적용 (unit_normalizer 제거 - normalizer.py에서 직접 처리)
        
        # update_notices_with_kv_data 제거 - building_type은 이미 _normalize_notice_with_raw에서 올바르게 설정됨
        # logger.info("🔧 Notices 데이터를 KV JSON 데이터로 업데이트 중...")
        # self.notice_normalizer.update_notices_with_kv_data(normalized_data, self.raw_data_dir)
        
        # 실시간 저장 (콜백이 제공된 경우) - 모든 업데이트 후 저장
        if save_callback:
            # 각 테이블별로 저장
            for table_name, data in normalized_data.items():
                save_callback(table_name, data)
        
        logger.info(f"정규화 완료: 플랫폼 {len(self.platforms)}개, 주소 {len(self.addresses)}개, 공고 {len(self.notices)}개, 유닛 {len(self.units)}개")
        return normalized_data
    
    def _normalize_row(self, row: pd.Series):
        """단일 행 정규화"""
        # 1. 플랫폼 정규화
        platform_id = self._normalize_platform(row)
        
        # 2. 주소 정규화 (JUSO API 사용)
        address_id = self._normalize_address_from_raw(row.get('address', ''), row.get('notice_id', ''))
        
        # 3. 공고 정규화
        notice_id = self._normalize_notice_with_raw(row, address_id, row.to_dict())
        
        # 4. 유닛 정규화 (occupancy 데이터 사용)
        kv_data = self._load_kv_data(row.get('kv_json_path', ''))
        unit_index = int(row.get('unit_index', 0))
        units = self._normalize_units_from_occupancy(row.get('notice_id', ''), notice_id, kv_data, unit_index)
        self.units.extend(units)
        
        # 5. 공고 범위 업데이트 (유닛 데이터 기반)
        self._update_notice_ranges(notice_id, units)
        
        # 6. 태그 정규화
        self._normalize_tags(row, notice_id)
        
        # 7. 인근 시설 정보 태그 정규화 (KV 데이터 포함)
        # KV 데이터를 record에 추가
        record = row.to_dict()
        record['kv_data'] = kv_data
        facilities_tags = normalize_facilities_tags(record, notice_id)
        self.notice_tags.extend(facilities_tags)

    # ===========================================
    # 2-2) 주소 정규화 관련 (JUSO API 사용)
    # ===========================================
    
    def _normalize_address_from_raw(self, address_raw: str, notice_id: str) -> Optional[str]:
        """raw.csv에서 추출한 주소를 정규화 (JUSO API 사용)"""
        if not address_raw:
            return None
        
        # 중복 체크
        if address_raw in self.address_id_map:
            return self.address_id_map[address_raw]
        
        try:
            # JUSO API를 사용한 주소 정규화
            normalized_data = normalize_address(address_raw)
            
            if normalized_data and 'normalized' in normalized_data:
                # 정규화된 데이터를 사용하여 주소 ID 생성
                address_id = self._normalize_address_with_juso(normalized_data)
                return address_id
            else:
                # API 실패 시 기본 처리
                logger.warning(f"주소 정규화 API 실패: {address_raw}")
                return self._normalize_address_fallback(address_raw)
                
        except AddressNormalizerError as e:
            logger.warning(f"주소 정규화 오류: {address_raw} - {e}")
            return self._normalize_address_fallback(address_raw)
        except Exception as e:
            logger.error(f"주소 정규화 예외: {address_raw} - {e}")
            return self._normalize_address_fallback(address_raw)
    
    def _normalize_address_fallback(self, address_raw: str) -> str:
        """API 실패 시 기본 주소 정규화"""
        # 중복 체크
        if address_raw in self.address_id_map:
            return self.address_id_map[address_raw]
        
        # 고유한 address_id 생성
        import hashlib
        address_id = hashlib.md5(address_raw.encode('utf-8')).hexdigest()[:16]
        
        # 주소 정보 구성 (간단한 형태)
        address_info = {
            'address_id': address_id,
            'address_raw': address_raw,
            'ctpv_nm': None,
            'sgg_nm': None,
            'emd_nm': None,
            'emd_cd': None,
            'building_name': None,
            'road_name_full': None,
            'jibun_name_full': None,
            'latitude': None,
            'longitude': None
        }
        
        self.addresses.append(address_info)
        self.address_id_map[address_raw] = address_id
        
        logger.info(f"주소 정규화 완료 (fallback): {address_raw} -> ID {address_id}")
        return address_id
    
    def _normalize_address_with_juso(self, address_data: Dict) -> int:
        """JUSO API 결과를 사용한 주소 정규화"""
        address_raw = address_data['address_raw']
        normalized = address_data['normalized']
        
        # 중복 체크를 위한 키 생성
        dedup_key = f"{normalized.get('emd_cd', '')}_{normalized.get('road_name_full', '')}_{normalized.get('building_main_no', '')}"
        dedup_key = dedup_key.lower().strip()
        
        if dedup_key in self.addresses:
            return self.addresses[dedup_key]['address_id']
        
        # 고유한 address_id 생성 (주소 원본 텍스트의 MD5 해시값)
        import hashlib
        address_id = hashlib.md5(address_raw.encode('utf-8')).hexdigest()[:16]
        
        # 주소 정규화 데이터 구성 (vworld API 결과 사용)
        address_info = {
            'address_id': address_id,
            'address_raw': address_raw,
            'ctpv_nm': normalized.get('ctpv_nm', ''),  # 시도명
            'sgg_nm': normalized.get('sgg_nm', ''),    # 시군구명
            'emd_nm': normalized.get('emd_nm', ''),    # 읍면동명
            'emd_cd': normalized.get('emd_cd', ''),    # 읍면동코드
            'road_name_full': normalized.get('road_name_full', ''),  # 도로명주소 전체
            'jibun_name_full': normalized.get('jibun_name_full', ''),  # 지번주소 전체
            'main_jibun': normalized.get('main_jibun', ''),  # 주지번
            'sub_jibun': normalized.get('sub_jibun', ''),    # 부지번
            'building_name': normalized.get('building_name', ''),  # 건물명
            'building_main_no': normalized.get('building_main_no', ''),  # 건물주번호
            'building_sub_no': normalized.get('building_sub_no', ''),    # 건물부번호
            'lat': normalized.get('lat'),  # 위도
            'lon': normalized.get('lon')   # 경도
        }
        
        self.addresses[dedup_key] = address_info
        self.address_id_map[address_raw] = address_id
        
        logger.info(f"주소 정규화 완료: {address_raw} -> ID {address_id}")
        logger.info(f"  시도명: {normalized.get('ctpv_nm', '')}")
        logger.info(f"  시군구명: {normalized.get('sgg_nm', '')}")
        logger.info(f"  읍면동코드: {normalized.get('emd_cd', '')}, 읍면동명: {normalized.get('emd_nm', '')}")
        logger.info(f"  도로명주소: {normalized.get('road_name_full', '')}")
        logger.info(f"  지번주소: {normalized.get('jibun_name_full', '')}")
        logger.info(f"  주지번: {normalized.get('main_jibun', '')}, 부지번: {normalized.get('sub_jibun', '')}")
        logger.info(f"  좌표: ({normalized.get('lat', '')}, {normalized.get('lon', '')})")
        return address_id
    
    # ===========================================
    # 2-3) 가격/면적 추출 관련
    # ===========================================
    

    # ===========================================
    # 2-4) 공고 정규화 관련
    # ===========================================

    def _normalize_notice_with_raw(self, row: pd.Series, address_id: Optional[int], record: Dict) -> str:
        """raw 데이터를 사용한 공고 정규화"""
        notice_id = row.get('notice_id', '')  # 실제 notice_id 사용
        
        # 플랫폼 ID 결정 (문자열 코드 사용) - 통일된 코드 사용
        platform_id = 'sohouse' if 'sohouse' in str(row.get('notice_id', '')) else 'cohouse'
        
        # KV JSON 데이터 로드
        kv_data = self._load_kv_data(record.get('kv_json_path', ''))
        
        # 이미지, 플로어플랜, 문서 존재 여부 확인
        image_paths = row.get('image_paths', '')
        floorplan_paths = row.get('floorplan_paths', '')
        document_paths = row.get('document_paths', '')
        
        # floorplan_paths는 raw.csv에서 직접 가져옴 (KV에서 추출 불필요)
        
        has_images = bool(image_paths and str(image_paths).strip() and str(image_paths) != 'nan')
        has_floorplan = bool(floorplan_paths and str(floorplan_paths).strip() and str(floorplan_paths) != 'nan')
        has_documents = bool(document_paths and str(document_paths).strip() and str(document_paths) != 'nan')
        
        # occupancy 데이터에서 가격 및 면적 정보 추출
        # building_type은 raw.csv에서 직접 가져오기
        final_building_type = row.get('building_type', 'unknown')
        
        # 고유한 address_id 생성
        import hashlib
        address_raw = record.get('address', '')
        unique_address_id = hashlib.md5(address_raw.encode('utf-8')).hexdigest()[:16] if address_raw else None
        
        # 공고 정보 구성 
        notice_data = {
            'notice_id': row.get('notice_id', ''), 
            'platform_id': platform_id,
            'title': record.get('house_name', '') or record.get('building_details', {}).get('address', ''),
            'status': 'open',
            'address_raw': address_raw,
            'address_id': unique_address_id,  # 고유한 address_id 사용
            'building_type': final_building_type,
            'notice_extra': {
                'image_paths': image_paths,
                'floorplan_paths': floorplan_paths,
                'document_paths': document_paths
            },
            'has_images': has_images,
            'has_floorplan': has_floorplan,
            'has_documents': has_documents,
            'list_url': record.get('list_url', ''),
            'posted_at': self._parse_datetime(record.get('last_modified')),
            'last_modified': self._parse_datetime(record.get('last_modified')),
            'apply_start_at': None,
            'apply_end_at': None,
            'created_at': self._parse_datetime(record.get('crawl_date')),
            'updated_at': self._parse_datetime(record.get('crawl_date'))
        }
        
        self.notices.append(notice_data)
        return notice_id
    
    def _normalize_tags(self, row: pd.Series, notice_id: str):
        """태그 정규화"""
        tags = normalize_tags(row, notice_id)
        self.notice_tags.extend(tags)

    # ===========================================
    # 2-5) 유닛 정규화 관련
    # ===========================================

    def _normalize_units_from_occupancy(self, notice_id: str, notice_id_int: int, kv_data: Dict, unit_index: int = 0) -> List[Dict]:
        """occupancy 데이터에서 units 정규화"""
        occupancy_df = self._load_occupancy_data(notice_id, unit_index)
        units = []
        
        logger.info(f"[DEBUG] _normalize_units_from_occupancy: notice_id={notice_id}, occupancy_df.empty={occupancy_df.empty}")
        
        if occupancy_df.empty:
            # occupancy 데이터가 없으면 빈 리스트 반환
            logger.warning(f"[DEBUG] occupancy 데이터 없음: {notice_id}")
            return []
        
        logger.info(f"[DEBUG] occupancy 데이터 {len(occupancy_df)}개 레코드 처리 시작")
        
        # raw CSV에서 해당 notice_id의 unit_type 가져오기
        raw_unit_type = self._get_raw_unit_type(notice_id)
        
        for idx, unit_row in occupancy_df.iterrows():
            logger.info(f"[DEBUG] unit_row {idx}: {unit_row.to_dict()}")
            unit_id = len(self.units) + len(units) + 1
            
            # 면적 파싱 (예: "17.84m²" -> 17.84)
            area_str = str(unit_row.get('면적', ''))
            area_m2 = None
            if area_str and area_str != 'nan':
                area_match = re.search(r'(\d+\.?\d*)', area_str)
                if area_match:
                    area_m2 = float(area_match.group(1))
            
            # 보증금, 월임대료, 관리비 파싱
            deposit = self._parse_krw_amount(str(unit_row.get('보증금', '')))
            rent = self._parse_krw_amount(str(unit_row.get('월임대료', '')))
            maintenance_fee = self._parse_krw_amount(str(unit_row.get('관리비', '')))
            
            # 층수 파싱
            floor = self._parse_int(unit_row.get('층'))
            
            # 입주가능일 파싱
            occupancy_date = unit_row.get('입주가능일', '')
            occupancy_available_at = None
            if occupancy_date and str(occupancy_date) != 'nan' and str(occupancy_date).strip():
                try:
                    occupancy_available_at = pd.to_datetime(occupancy_date).strftime('%Y-%m-%d')
                except:
                    pass
            
            # 인원 수 파싱
            capacity = self._parse_int(unit_row.get('인원'))
            
            # 입주가능 여부 파싱
            occupancy_available = bool(unit_row.get('입주가능', 0))
            
            # 호수 정보 파싱 (방이름에서 추출)
            room_name = unit_row.get('방이름', '')
            if room_name and str(room_name).strip() and str(room_name).strip() != 'nan':
                room_number = str(room_name).strip()
                # "호"가 있으면 제거
                if room_number.endswith('호'):
                    room_number = room_number[:-1]
                # 숫자만 있는 경우 그대로 사용
                if room_number.isdigit():
                    room_number = room_number
            else:
                room_number = None
            
            unit_data = {
                'unit_id': unit_row.get('space_id', f'unit_{unit_id}'),
                'notice_id': notice_id,
                'unit_type': raw_unit_type, 
                'deposit': deposit,
                'rent': rent,
                'maintenance_fee': maintenance_fee,
                'area_m2': area_m2,
                'floor': floor,
                'room_number': room_number,  # 호수 정보 추가
                'occupancy_available': occupancy_available,  # 입주가능 여부
                'occupancy_available_at': occupancy_available_at,
                'capacity': capacity  # 인원 수
            }
            
            units.append(unit_data)
            
            # unit_features에 추가 (room_count, bathroom_count, direction)
            unit_type = raw_unit_type  # raw CSV에서 가져온 unit_type 사용
            unit_features = {
                'unit_id': unit_row.get('space_id', f'unit_{unit_id}'),  # unit_code를 unit_id로 사용
                'room_count': self._extract_room_count(unit_type),
                'bathroom_count': None,  # occupancy 데이터에는 없음
                'direction': None
            }
            self.unit_features.append(unit_features)
        
        return units

    # ===========================================
    # 2-6) 데이터 로드 관련
    # ===========================================
    
    def _load_occupancy_data(self, notice_id: str, unit_index: int = 0) -> pd.DataFrame:
        """occupancy CSV 파일 로드"""
        try:
            if 'sohouse' in notice_id:
                # sohouse의 경우 sohouse 디렉토리에서 occupancy 파일 검색
                sohouse_data_dir = Path("backend/data/housing/sohouse")
                # 가장 최근 날짜의 sohouse 디렉토리 찾기
                if sohouse_data_dir.exists():
                    date_dirs = [d for d in sohouse_data_dir.iterdir() if d.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', d.name)]
                    if date_dirs:
                        latest_sohouse_dir = max(date_dirs, key=lambda x: x.name)
                        tables_dir = latest_sohouse_dir / 'tables'
                    else:
                        logger.warning(f"sohouse 날짜 디렉토리를 찾을 수 없음: {sohouse_data_dir}")
                        return pd.DataFrame()
                else:
                    logger.warning(f"sohouse 디렉토리를 찾을 수 없음: {sohouse_data_dir}")
                    return pd.DataFrame()
                occupancy_files = list(tables_dir.glob("detail_*_occupancy.csv"))
                occupancy_files.sort(key=lambda x: int(x.stem.split('_')[1]))
                
                logger.info(f"[DEBUG] sohouse occupancy 파일 검색: {len(occupancy_files)}개 파일")
                
                for occupancy_file in occupancy_files:
                    try:
                        df = pd.read_csv(occupancy_file)
                        if not df.empty and 'notice_id' in df.columns:
                            # 따옴표 제거하여 비교
                            df['notice_id_clean'] = df['notice_id'].astype(str).str.strip('"')
                            logger.info(f"[DEBUG] sohouse occupancy 파일 {occupancy_file} - notice_id 샘플: {df['notice_id_clean'].iloc[0] if not df.empty else 'None'}")
                            logger.info(f"[DEBUG] 찾는 notice_id: {notice_id}")
                            matching_rows = df[df['notice_id_clean'] == notice_id]
                            if not matching_rows.empty:
                                logger.info(f"[DEBUG] sohouse occupancy 데이터 발견: {occupancy_file} - {len(matching_rows)}개 레코드")
                                return matching_rows
                    except Exception as e:
                        logger.warning(f"[DEBUG] occupancy 파일 읽기 실패 {occupancy_file}: {e}")
                        continue
                
                logger.warning(f"[DEBUG] sohouse notice_id {notice_id}에 해당하는 occupancy 데이터를 찾을 수 없음")
                return pd.DataFrame()
            else:
                # cohouse의 경우 cohouse 디렉토리에서 occupancy 파일 검색
                cohouse_data_dir = Path("backend/data/housing/cohouse")
                # 가장 최근 날짜의 cohouse 디렉토리 찾기
                if cohouse_data_dir.exists():
                    date_dirs = [d for d in cohouse_data_dir.iterdir() if d.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', d.name)]
                    if date_dirs:
                        latest_cohouse_dir = max(date_dirs, key=lambda x: x.name)
                        tables_dir = latest_cohouse_dir / 'tables'
                    else:
                        logger.warning(f"cohouse 날짜 디렉토리를 찾을 수 없음: {cohouse_data_dir}")
                        return pd.DataFrame()
                else:
                    logger.warning(f"cohouse 디렉토리를 찾을 수 없음: {cohouse_data_dir}")
                    return pd.DataFrame()
                occupancy_files = list(tables_dir.glob("detail_*_occupancy.csv"))
                occupancy_files.sort(key=lambda x: int(x.stem.split('_')[1]))
                
                logger.info(f"[DEBUG] cohouse occupancy 파일 검색: {len(occupancy_files)}개 파일")
                
                for occupancy_file in occupancy_files:
                    try:
                        df = pd.read_csv(occupancy_file)
                        if not df.empty and 'notice_id' in df.columns:
                            # 따옴표 제거하여 비교
                            df['notice_id_clean'] = df['notice_id'].astype(str).str.strip('"')
                            matching_rows = df[df['notice_id_clean'] == notice_id]
                            if not matching_rows.empty:
                                logger.info(f"[DEBUG] cohouse occupancy 데이터 발견: {occupancy_file} - {len(matching_rows)}개 레코드")
                                return matching_rows
                    except Exception as e:
                        logger.warning(f"[DEBUG] occupancy 파일 읽기 실패 {occupancy_file}: {e}")
                        continue
                
                logger.warning(f"[DEBUG] cohouse notice_id {notice_id}에 해당하는 occupancy 데이터를 찾을 수 없음")
        except Exception as e:
            logger.warning(f"occupancy 데이터 로드 실패: {notice_id}, 오류: {e}")
        
        return pd.DataFrame()

    def _load_kv_data(self, kv_json_path: str) -> Dict:
        """KV JSON 파일 로드"""
        if not kv_json_path or str(kv_json_path) == 'nan':
            return {}
        
        try:
            # raw 데이터 디렉토리에서 KV 파일 경로 구성
            kv_file_path = Path(self.raw_data_dir) / kv_json_path
            if kv_file_path.exists():
                with open(kv_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"KV JSON 파일 로드 실패: {kv_json_path}, 오류: {e}")
        
        return {}

    def _get_latest_raw_csv_paths(self) -> List[Path]:
        """가장 최근 날짜의 housing CSV 파일 경로들을 반환"""
        housing_data_dir = Path("backend/data/housing")
        csv_paths = []
        
        # cohouse와 sohouse 디렉토리에서 가장 최근 날짜 찾기
        for platform in ['cohouse', 'sohouse']:
            platform_dir = housing_data_dir / platform
            if platform_dir.exists():
                # 날짜 디렉토리들 찾기 (YYYY-MM-DD 형식)
                date_dirs = [d for d in platform_dir.iterdir() if d.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', d.name)]
                if date_dirs:
                    # 가장 최근 날짜 선택
                    latest_date_dir = max(date_dirs, key=lambda x: x.name)
                    csv_path = latest_date_dir / "raw.csv"
                    if csv_path.exists():
                        csv_paths.append(csv_path)
                        logger.info(f"최근 housing CSV 파일 발견: {csv_path}")
        
        return csv_paths

    def _get_latest_raw_data_dir(self) -> Path:
        """가장 최근 날짜의 housing 데이터 디렉토리를 반환"""
        housing_data_dir = Path("backend/data/housing")
        
        # cohouse와 sohouse 디렉토리에서 가장 최근 날짜 찾기
        latest_date = None
        for platform in ['cohouse', 'sohouse']:
            platform_dir = housing_data_dir / platform
            if platform_dir.exists():
                # 날짜 디렉토리들 찾기 (YYYY-MM-DD 형식)
                date_dirs = [d for d in platform_dir.iterdir() if d.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', d.name)]
                if date_dirs:
                    platform_latest = max(date_dirs, key=lambda x: x.name)
                    if latest_date is None or platform_latest.name > latest_date.name:
                        latest_date = platform_latest
        
        if latest_date:
            logger.info(f"최근 housing 데이터 디렉토리: {latest_date}")
            return latest_date
        else:
            # 기본값으로 cohouse/2025-09-25 사용 (fallback)
            fallback_dir = housing_data_dir / "cohouse" / "2025-09-25"
            logger.warning(f"최근 날짜를 찾을 수 없어 기본 디렉토리 사용: {fallback_dir}")
            return fallback_dir

    def _get_raw_unit_type(self, notice_id: str) -> str:
        """raw CSV에서 notice_id에 해당하는 unit_type을 가져오기"""
        # 가장 최근 날짜의 raw CSV 파일들 찾기
        raw_csv_paths = self._get_latest_raw_csv_paths()
        
        for csv_path in raw_csv_paths:
            if csv_path.exists():
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_path)
                    matching_rows = df[df['notice_id'] == notice_id]
                    if not matching_rows.empty:
                        unit_type = matching_rows.iloc[0].get('unit_type', '')
                        if unit_type and str(unit_type) != 'nan':
                            logger.info(f"[DEBUG] raw CSV에서 unit_type 찾음: {notice_id} -> {unit_type}")
                            return str(unit_type)
                except Exception as e:
                    logger.error(f"[ERROR] {csv_path} 읽기 실패: {e}")
        
        logger.warning(f"[DEBUG] raw CSV에서 unit_type을 찾을 수 없음: {notice_id}")
        return 'unknown'

    # ===========================================
    # 2-7) 파싱 유틸리티
    # ===========================================

    def _parse_krw_amount(self, amount_str: str) -> Optional[int]:
        """한국 원화 금액 파싱 (예: "15,000,000원" -> 15000000, "5500만원" -> 55000000)"""
        if not amount_str or str(amount_str) == 'nan':
            return None
        
        amount_str = str(amount_str).strip()
        
        # 만원 단위 처리
        if '만원' in amount_str:
            # "5500만원" -> 55000000
            numbers = re.findall(r'[\d,]+', amount_str.replace('만원', ''))
            if numbers:
                try:
                    return int(numbers[0].replace(',', '')) * 10000
                except:
                    pass
        
        # 억원 단위 처리
        elif '억원' in amount_str:
            # "1억원" -> 100000000
            numbers = re.findall(r'[\d,]+', amount_str.replace('억원', ''))
            if numbers:
                try:
                    return int(numbers[0].replace(',', '')) * 100000000
                except:
                    pass
        
        # 일반 원 단위 처리
        else:
            # 숫자만 추출
            numbers = re.findall(r'[\d,]+', amount_str.replace('원', ''))
            if numbers:
                try:
                    return int(numbers[0].replace(',', ''))
                except:
                    pass
        
        return None

    def _parse_datetime(self, value) -> Optional[datetime]:
        """날짜/시간 파싱"""
        if pd.isna(value) or not value:
            return None
        
        try:
            if isinstance(value, str):
                # ISO 형식 파싱 시도
                if 'T' in value:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                # 기타 형식들
                return pd.to_datetime(value)
            return pd.to_datetime(value)
        except:
            return None

    def _parse_numeric(self, value) -> Optional[float]:
        """숫자 파싱"""
        if pd.isna(value) or not value:
            return None
        
        try:
            if isinstance(value, str):
                # 쉼표 제거
                value = value.replace(',', '')
                # 숫자만 추출
                import re
                numbers = re.findall(r'\d+', value)
                return float(numbers[0]) if numbers else None
            return float(value)
        except:
            return None

    def _parse_int(self, value) -> Optional[int]:
        """정수 파싱"""
        numeric = self._parse_numeric(value)
        return int(numeric) if numeric is not None else None

    def _extract_room_count(self, unit_type: str) -> int:
        """유닛 타입에서 방 개수 추출"""
        if '원룸' in unit_type:
            return 1
        elif '투룸' in unit_type:
            return 2
        elif '쓰리룸' in unit_type or '3룸' in unit_type:
            return 3
        else:
            return 1  # 기본값

    # ===========================================
    # 2-8) 기타 유틸리티
    # ===========================================
    
    def _normalize_platform(self, row: pd.Series) -> str:
        """플랫폼 정규화 (문자열 코드 반환)"""
        platform_code = row.get('platform', 'unknown')
        platform_name = self._get_platform_name(platform_code)
        platform_url = self._get_platform_url(platform_code)
        
        # 코드마스터와 호환되는 코드로 변환
        code_master_code = f'platform_{platform_code}'
        
        # 중복 체크
        for platform in self.platforms:
            if platform['code'] == platform_code:
                return platform['code']  # code 반환
        
        platform_data = {
            'code': platform_code,
            'name': platform_name,
            'url': platform_url,
            'is_active': True,
            'platform_code': code_master_code  # 코드마스터 코드 추가
        }
        
        self.platforms.append(platform_data)
        return platform_code

    def _update_notice_ranges(self, notice_id: int, units: List[Dict]):
        """공고의 범위 정보 업데이트 (유닛 데이터 기반)"""
        if not units:
            return
        
        # 면적 범위 계산
        areas = [unit.get('area_m2') for unit in units if unit.get('area_m2')]
        if areas:
            area_min = min(areas)
            area_max = max(areas)
        else:
            area_min = area_max = None
        
        # 층수 범위 계산
        floors = [unit.get('floor') for unit in units if unit.get('floor')]
        if floors:
            floor_min = min(floors)
            floor_max = max(floors)
        else:
            floor_min = floor_max = None
        
        # 공고 데이터 업데이트
        for notice in self.notices:
            if notice['notice_id'] == notice_id:
                # min/max 필드는 제거되었으므로 업데이트하지 않음
                break

    def _get_platform_name(self, code: str) -> str:
        """플랫폼 코드로부터 이름 추출"""
        platform_names = {
            'cohouse': '서울시 공동체주택',
            'sohouse': '서울시 사회주택',
            'lh': 'LH공사',
            'sh': 'SH공사',
            'youth': '청년안심주택'
        }
        return platform_names.get(code, code)

    def _get_platform_url(self, code: str) -> str:
        """플랫폼 코드로부터 URL 추출"""
        platform_urls = {
            'cohouse': 'https://soco.seoul.go.kr/coHouse',
            'sohouse': 'https://soco.seoul.go.kr/soHouse',
            'lh': 'https://www.lh.or.kr',
            'sh': 'https://www.sh.co.kr',
            'youth': 'https://soco.seoul.go.kr/youth'
        }
        return platform_urls.get(code, '')

    
# ===========================================
# 3) 태그 정규화 함수들
# ===========================================

def normalize_tags(row: pd.Series, notice_id: str) -> List[Dict]:
    """태그 데이터 정규화 (notice_id, tag, description 구조)"""
    tags = []
    
    # 테마를 태그로 추가
    theme = str(row.get('theme', '')).strip()
    if theme and theme != 'nan':
        tags.append({
            'notice_id': notice_id,
            'tag': '테마',
            'description': theme
        })
    
    # 지하철역을 태그로 추가
    subway = str(row.get('subway_station', '')).strip()
    if subway and subway != 'nan':
        tags.append({
            'notice_id': notice_id,
            'tag': '지하철',
            'description': subway
        })
    
    # 자격요건을 태그로 추가
    eligibility = str(row.get('eligibility', '')).strip()
    if eligibility and eligibility != 'nan':
        tags.append({
            'notice_id': notice_id,
            'tag': '자격요건',
            'description': eligibility
        })
    
    return tags

def normalize_facilities_tags(record: Dict, notice_id: str) -> List[Dict]:
    """KV/JSON 파일의 시설 정보를 태그로 정규화 (notice_id, tag, description 구조)"""
    tags = []
    added_tags = set()  # 중복 방지를 위한 집합
    
    if not record:
        logger.warning(f"[DEBUG] normalize_facilities_tags: record이 비어있음 - notice_id: {notice_id}")
        return tags
    
    # KV 데이터에서 시설 정보 추출
    kv_data = record.get('kv_data', {})
    facilities = kv_data.get('facilities', {})
    
    logger.info(f"[DEBUG] normalize_facilities_tags: notice_id={notice_id}, kv_data keys={list(kv_data.keys())}, facilities keys={list(facilities.keys())}")
    
    # facilities 딕셔너리의 모든 키-값 쌍을 태그로 변환
    for key, value in facilities.items():
        if value and str(value).strip() and str(value).strip() != 'nan':
            # 키 이름을 한글로 매핑
            key_mapping = {
                'subway_station': '지하철',
                'subway': '지하철',  # subway_station과 동일하게 처리
                'bus': '버스',
                'nearby_마트': '마트',
                'nearby_병원': '병원',
                'nearby_학교': '학교',
                'nearby_시설': '시설',
                'nearby_카페': '카페'
            }
            
            tag_key = key_mapping.get(key, key)
            tag_value = str(value).strip()
            
            # 중복 체크 (tag + description 조합)
            tag_combination = f"{tag_key}:{tag_value}"
            if tag_combination not in added_tags:
                tags.append({
                    'notice_id': notice_id,
                    'tag': tag_key,
                    'description': tag_value
                })
                added_tags.add(tag_combination)
    
    logger.info(f"[DEBUG] normalize_facilities_tags: notice_id={notice_id}, 생성된 태그 수={len(tags)}")
    return tags