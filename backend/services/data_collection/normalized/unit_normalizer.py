#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
유닛 정규화 모듈 (Unit Normalizer)
===========================================
유닛 데이터 정규화, 건물 타입 분류, 특성 추출을 담당하는 모듈
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import hashlib
import random
from pathlib import Path


logger = logging.getLogger(__name__)

# ----------------------------
# 1) 유닛 정규화 클래스
# ----------------------------

class UnitNormalizer:
    """유닛 정규화를 담당하는 클래스"""
    
    def __init__(self):
        self.units = []
        self.unit_features = []
    
    def load_occupancy_data_from_tables(self, raw_data_dir: Path) -> Dict[str, List[Dict]]:
        """
        raw/tables 폴더에서 occupancy 데이터를 로드하여 record_id별로 그룹화
        
        Args:
            raw_data_dir: raw 데이터 디렉토리 경로
            
        Returns:
            record_id별로 그룹화된 occupancy 데이터 딕셔너리
        """
        all_occupancy_data = {}
        tables_dir = raw_data_dir / "tables"
        
        if not tables_dir.exists():
            logger.warning(f"tables 디렉토리가 존재하지 않습니다: {tables_dir}")
            return all_occupancy_data
        
        occupancy_files = list(tables_dir.glob("detail_*_occupancy.csv"))
        occupancy_files.sort(key=lambda x: int(x.stem.split('_')[1]))
        
        logger.info(f"📂 {len(occupancy_files)}개의 occupancy 파일 로드 중...")
        
        for occupancy_file in occupancy_files:
            try:
                df = pd.read_csv(occupancy_file)
                # notice_id를 그대로 사용하여 그룹화
                for notice_id, group_df in df.groupby('notice_id'):
                    if notice_id not in all_occupancy_data:
                        all_occupancy_data[notice_id] = []
                    all_occupancy_data[notice_id].extend(group_df.to_dict('records'))
            except Exception as e:
                logger.error(f"occupancy 파일 읽기 실패 {occupancy_file}: {e}")
        
        logger.info(f"📊 총 {len(all_occupancy_data)}개의 notice_id에 대한 occupancy 데이터 로드 완료")
        return all_occupancy_data
    
    def find_matching_record_id(self, notice: Dict, all_occupancy_data: Dict[str, List[Dict]]) -> List[str]:
        """
        notice의 notice_id에 해당하는 occupancy 데이터를 찾기
        
        Args:
            notice: 공고 데이터 (notice_id 포함)
            all_occupancy_data: 모든 occupancy 데이터
            
        Returns:
            매칭되는 notice_id 리스트
        """
        matching_record_ids = []
        # source_key를 사용하여 매칭
        notice_id = notice.get('source_key', '')
        
        # notice_id와 정확히 일치하는 occupancy 데이터 찾기
        if notice_id in all_occupancy_data:
            matching_record_ids.append(notice_id)
            logger.info(f"✅ notice_id 매칭 성공: {notice_id}")
        else:
            # 매칭 실패 시 로그 출력
            logger.warning(f"❌ notice_id 매칭 실패: {notice_id}")
            available_keys = list(all_occupancy_data.keys())[:5]  # 처음 5개만 표시
            logger.warning(f"   사용 가능한 notice_id: {available_keys}")
        
        return matching_record_ids
    
    def _load_raw_unit_types(self, raw_data_dir: Path) -> Dict[str, str]:
        """raw CSV 파일에서 notice_id별 unit_type 정보를 로드"""
        raw_unit_types = {}
        
        # cohouse와 sohouse 플랫폼의 raw CSV 파일들을 확인
        for platform in ['cohouse', 'sohouse']:
            raw_csv_path = raw_data_dir / platform / '2025-09-25' / 'raw.csv'
            if raw_csv_path.exists():
                try:
                    import pandas as pd
                    df = pd.read_csv(raw_csv_path)
                    for _, row in df.iterrows():
                        notice_id = row.get('notice_id', '')
                        unit_type = row.get('unit_type', '')
                        if notice_id and unit_type:
                            raw_unit_types[notice_id] = unit_type
                    logger.info(f"[DEBUG] {platform} raw CSV에서 {len([k for k in raw_unit_types.keys() if k.startswith(platform)])}개 unit_type 로드")
                except Exception as e:
                    logger.error(f"[ERROR] {raw_csv_path} 읽기 실패: {e}")
        
        return raw_unit_types
    
    def update_units_with_occupancy_data(self, normalized_data: Dict, raw_data_dir: Path) -> None:
        # raw CSV에서 unit_type 정보를 읽어오기 위한 매핑 생성
        raw_unit_types = self._load_raw_unit_types(raw_data_dir)
        """
        raw/tables의 occupancy 데이터로 units 업데이트
        
        Args:
            normalized_data: 정규화된 데이터
            raw_data_dir: raw 데이터 디렉토리 경로
        """
        units = normalized_data.get('units', [])
        notices = normalized_data.get('notices', [])
        
        # 모든 occupancy 데이터 로드
        all_occupancy_data = self.load_occupancy_data_from_tables(raw_data_dir)
        
        # 각 공고별로 units 데이터 수정
        for notice in notices:
            notice_id = notice['id']
            notice_units = [unit for unit in units if unit.get('notice_id') == notice_id]
            
            if not notice_units:
                continue
            
            # building_type은 notice에서 가져옴 (unit에서는 제거)
            
            # 매칭되는 notice_id 찾기
            matching_record_ids = self.find_matching_record_id(notice, all_occupancy_data)
            
            # occupancy 데이터 수집
            occupancy_data = []
            for notice_id in matching_record_ids:
                if notice_id in all_occupancy_data:
                    occupancy_data.extend(all_occupancy_data[notice_id])
                    logger.info(f"✅ occupancy 데이터 로드: {notice_id} -> {len(all_occupancy_data[notice_id])}개 레코드")
            
            # Units 데이터 수정
            for i, unit in enumerate(notice_units):
                # occupancy 데이터가 있으면 사용
                if i < len(occupancy_data):
                    occ_data = occupancy_data[i]
                    logger.info(f"[DEBUG] Unit {i}: raw/tables 데이터 사용 - {occ_data}")
                    
                    # unit_code를 space_id로 설정
                    unit['unit_code'] = occ_data.get('space_id', f"space_{hashlib.md5(f'{notice_id}_{i}'.encode()).hexdigest()[:12]}")
                    
                    # 면적 정보 설정 (m² 제거하고 숫자만 추출)
                    area_str = str(occ_data.get('면적', '0m²')).replace('m²', '').replace(',', '').strip()
                    try:
                        # 숫자 패턴 매칭으로 면적 추출
                        import re
                        area_match = re.search(r'(\d+\.?\d*)', area_str)
                        if area_match:
                            unit['area_m2'] = float(area_match.group(1))
                            logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 면적 {unit['area_m2']}㎡")
                        else:
                            unit['area_m2'] = None
                            logger.warning(f"[DEBUG] Unit {unit.get('unit_code', '')}: 면적 파싱 실패 - '{area_str}'")
                    except Exception as e:
                        unit['area_m2'] = None
                        logger.warning(f"[DEBUG] Unit {unit.get('unit_code', '')}: 면적 파싱 오류 - {e}")
                    
                    # 보증금, 월세, 관리비 설정 (원 제거하고 숫자만 추출)
                    deposit_str = str(occ_data.get('보증금', '0원')).replace('원', '').replace(',', '')
                    rent_str = str(occ_data.get('월임대료', '0원')).replace('원', '').replace(',', '')
                    maintenance_str = str(occ_data.get('관리비', '0원')).replace('원', '').replace(',', '')
                    
                    try:
                        unit['deposit'] = int(float(deposit_str)) if deposit_str.isdigit() else 0
                        unit['rent'] = int(float(rent_str)) if rent_str.isdigit() else 0
                        unit['maintenance_fee'] = int(float(maintenance_str)) if maintenance_str.isdigit() else 0
                    except:
                        unit['deposit'] = 0
                        unit['rent'] = 0
                        unit['maintenance_fee'] = 0
                    
                    # 층수 정보 설정
                    floor_str = str(occ_data.get('층', '1'))
                    try:
                        unit['floor'] = int(floor_str) if floor_str.isdigit() else 1
                    except:
                        unit['floor'] = 1
                    
                    # 방 수, 욕실 수 설정
                    # room_count, bathroom_count, direction은 unit_features로 이동
                    room_count_str = str(occ_data.get('인원', '1'))
                    try:
                        room_count = int(room_count_str) if room_count_str.isdigit() else 1
                    except:
                        room_count = 1
                    
                    bathroom_count = 1  # 기본값
                    direction = occ_data.get('방이름', '')
                    
                    # unit_features에 추가
                    unit_features = {
                        'unit_id': unit['id'],
                        'room_count': room_count,
                        'bathroom_count': bathroom_count,
                        'direction': direction
                    }
                    self.unit_features.append(unit_features)
                    
                    # 입주가능일 정보 추가 (raw/tables에서 가져오기)
                    occupancy_available_at = str(occ_data.get('입주가능일', '')).strip()
                    unit['occupancy_available_at'] = occupancy_available_at if occupancy_available_at else None
                    if occupancy_available_at:
                        logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 입주가능일 {occupancy_available_at}")
                    else:
                        logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 입주가능일 정보 없음")
                    
                    # 입주가능 여부 추가 (1: 가능, 0: 불가능)
                    occupancy_available = str(occ_data.get('입주가능', '0')).strip()
                    if occupancy_available == '1':
                        unit['occupancy_available'] = True
                        logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 입주가능 (True)")
                    elif occupancy_available == '0':
                        unit['occupancy_available'] = False
                        logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 입주불가 (False)")
                    else:
                        unit['occupancy_available'] = False  # 기본값
                        logger.warning(f"[DEBUG] Unit {unit.get('unit_code', '')}: 입주가능 정보 없음, 기본값 False 사용")
                    
                    # 인원 정보 추가
                    capacity_str = str(occ_data.get('인원', '1')).strip()
                    try:
                        unit['capacity'] = int(capacity_str) if capacity_str.isdigit() else 1
                        logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 인원 {unit['capacity']}명")
                    except:
                        unit['capacity'] = 1
                        logger.warning(f"[DEBUG] Unit {unit.get('unit_code', '')}: 인원 정보 파싱 실패, 기본값 1명 사용")
                else:
                    # occupancy 데이터가 없으면 기본값 설정
                    logger.warning(f"[DEBUG] Unit {i}: raw/tables 데이터 없음, 기본값 사용")
                    unit['unit_code'] = f"space_{hashlib.md5(f'{notice_id}_{i}'.encode()).hexdigest()[:12]}"
                    unit['area_m2'] = None
                    unit['deposit'] = 0
                    unit['rent'] = 0
                    unit['maintenance_fee'] = 0
                    unit['floor'] = random.randint(1, 5)
                    # room_count, bathroom_count, direction은 unit_features로 이동
                    unit_features = {
                        'unit_id': unit['id'],
                        'room_count': 1,
                        'bathroom_count': 1,
                        'direction': ''
                    }
                    self.unit_features.append(unit_features)
                    unit['occupancy_available_at'] = None  
                    unit['occupancy_available'] = False    
                    unit['capacity'] = 1                   
                
                # unit_type 설정 (raw CSV에서 직접 추출)
                notice_id = notice.get('notice_id', '')
                raw_unit_type = raw_unit_types.get(notice_id, '')
                
                if raw_unit_type:
                    unit['unit_type'] = raw_unit_type
                    logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: unit_type 설정 - '{raw_unit_type}' (raw CSV에서)")
                else:
                    unit['unit_type'] = 'unknown'
                    logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: unit_type 없음 - 'unknown' (raw CSV에서 찾을 수 없음)")
                
                # building_type 제거 (units에서는 사용하지 않음)
                if 'building_type' in unit:
                    del unit['building_type']
                
                # unit_type이 없으면 기본값 설정
                if 'unit_type' not in unit:
                    unit['unit_type'] = 'unknown'
                
                logger.info(f"[DEBUG] Unit {unit.get('unit_code', '')}: 최종 unit_type - '{unit['unit_type']}'")
                
                # unit_extra 삭제


# ----------------------------
# 2) 유닛 특성 추출 함수들
# ----------------------------

def _add_unit_features(self, unit_id: int, row: pd.Series, record: Dict):
    """유닛 특성 추가"""
    features = []
    
    # 기본 특성들
    basic_features = [
        'heating', 'cooling', 'parking', 'elevator', 'balcony',
        'security', 'cctv', 'intercom', 'air_conditioner'
    ]
    
    for feature in basic_features:
        value = row.get(feature)
        if value and str(value).strip() and str(value).strip() != 'nan':
            features.append({
                'unit_id': unit_id,
                'feature_type': feature,
                'feature_value': str(value).strip()
            })
    
    # 추가 특성들 (record에서 추출)
    if record.get('building_details'):
        building_details = record['building_details']
        for key, value in building_details.items():
            if value and str(value).strip() and str(value).strip() != 'nan':
                features.append({
                    'unit_id': unit_id,
                    'feature_type': f"building_{key}",
                    'feature_value': str(value).strip()
                })
    
    self.unit_features.extend(features)

# ----------------------------
# 3) 유틸리티 함수들
# ----------------------------

def _parse_numeric(value) -> Optional[float]:
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

def _parse_int(value) -> Optional[int]:
    """정수 파싱"""
    numeric = _parse_numeric(value)
    return int(numeric) if numeric is not None else None
