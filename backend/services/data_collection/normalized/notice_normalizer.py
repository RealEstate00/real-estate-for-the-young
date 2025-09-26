#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
공고 정규화 모듈 (Notice Normalizer)
===========================================
공고 데이터 정규화, 태그 처리, 메타데이터 관리를 담당하는 모듈
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import json
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ----------------------------
# 1) 공고 정규화 클래스
# ----------------------------

class NoticeNormalizer:
    """공고 정규화를 담당하는 클래스"""
    
    def __init__(self):
        self.notices = []
        self.raw_data_dir = None
    
    def _parse_krw(self, value_str: str) -> int:
        """한국 원화 문자열을 정수로 변환"""
        try:
            # 쉼표 제거 후 정수 변환
            return int(float(value_str.replace(',', '')))
        except:
            return 0
    
    def _load_text_file(self, text_path: str) -> str:
        """텍스트 파일 내용을 로드"""
        if not text_path:
            return ''
        
        try:
            from pathlib import Path
            text_file = Path(text_path)
            if text_file.exists():
                return text_file.read_text(encoding='utf-8')
            else:
                logger.warning(f"텍스트 파일을 찾을 수 없습니다: {text_path}")
                return ''
        except Exception as e:
            logger.error(f"텍스트 파일 로드 실패: {text_path} - {e}")
            return ''
    
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
    
    def _extract_floorplan_from_kv(self, kv_data: Dict) -> str:
        """KV 데이터에서 floorplan 정보 추출"""
        # building_details에서 floorplan 관련 정보 찾기
        building_details = kv_data.get('building_details', {})
        total_people = building_details.get('total_people', '')
        
        # floorplan 관련 키워드가 있는지 확인
        floorplan_keywords = ['floorplan', 'floor_plan', '도면', '평면도', '배치도']
        for keyword in floorplan_keywords:
            if keyword in str(total_people).lower():
                return f"floorplan_{keyword}"
        
        return ""
    
    def _extract_prices_from_kv(self, kv_data: Dict) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """KV 데이터에서 가격 정보 추출"""
        try:
            sohouse_info = kv_data.get('sohouse_text_extracted_info', {})
            
            # 보증금 정보 추출
            deposit_info = sohouse_info.get('deposit', '')
            deposit_min = None
            deposit_max = None
            
            if deposit_info:
                # "1,500만원 ~ 5,500만원" 형태 파싱
                if '~' in deposit_info:
                    parts = deposit_info.split('~')
                    if len(parts) == 2:
                        try:
                            deposit_min = float(parts[0].replace('만원', '').replace(',', '').strip()) * 10000
                            deposit_max = float(parts[1].replace('만원', '').replace(',', '').strip()) * 10000
                        except:
                            pass
                else:
                    # 단일 값인 경우
                    try:
                        deposit_value = float(deposit_info.replace('만원', '').replace(',', '').strip()) * 10000
                        deposit_min = deposit_value
                        deposit_max = deposit_value
                    except:
                        pass
            
            # 월세 정보 추출
            rent_info = sohouse_info.get('monthly_rent', '')
            rent_min = None
            rent_max = None
            
            if rent_info:
                if '~' in rent_info:
                    parts = rent_info.split('~')
                    if len(parts) == 2:
                        try:
                            rent_min = float(parts[0].replace('만원', '').replace(',', '').strip()) * 10000
                            rent_max = float(parts[1].replace('만원', '').replace(',', '').strip()) * 10000
                        except:
                            pass
                else:
                    try:
                        rent_value = float(rent_info.replace('만원', '').replace(',', '').strip()) * 10000
                        rent_min = rent_value
                        rent_max = rent_value
                    except:
                        pass
            
            return deposit_min, deposit_max, rent_min, rent_max
            
        except Exception as e:
            logger.error(f"KV 데이터에서 가격 정보 추출 실패: {e}")
            return None, None, None, None
    
    def _extract_area_from_kv(self, kv_data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """KV 데이터에서 면적 정보 추출"""
        try:
            sohouse_info = kv_data.get('sohouse_text_extracted_info', {})
            extracted_patterns = sohouse_info.get('extracted_patterns', {})
            areas = extracted_patterns.get('areas', [])
            
            # 숫자로 변환 가능한 면적들만 필터링
            numeric_areas = []
            if areas:
                for area in areas:
                    try:
                        area_value = float(area)
                        # 주거 면적으로 보이는 값들만 선택 (50㎡ 제한)
                        if 10 <= area_value <= 50:  # 10㎡ ~ 50㎡ 범위 (주거 면적만)
                            numeric_areas.append(area_value)
                    except:
                        continue
            
            if numeric_areas:
                return min(numeric_areas), max(numeric_areas)
            
            return None, None
            
        except Exception as e:
            logger.error(f"KV 데이터에서 면적 정보 추출 실패: {e}")
            return None, None
    
    def extract_prices_from_kv(self, kv_data: Dict) -> tuple:
        """
        KV JSON 데이터에서 보증금/월세 정보 추출
        
        Args:
            kv_data: KV JSON 데이터
        
        Returns:
            (deposit_min, deposit_max, rent_min, rent_max)
        """
        try:
            # housing_specific에서 직접 가격 정보 추출
            housing_specific = kv_data.get('housing_specific', {})
            
            deposit_range = housing_specific.get('deposit_range', '')
            monthly_rent_range = housing_specific.get('monthly_rent_range', '')
            
            # cohouse_text_extracted_info에서도 가격 정보 추출 시도
            cohouse_info = kv_data.get('cohouse_text_extracted_info', {})
            if not deposit_range and cohouse_info.get('deposit'):
                deposit_range = cohouse_info.get('deposit', '')
            if not monthly_rent_range and cohouse_info.get('rent'):
                monthly_rent_range = cohouse_info.get('rent', '')
            
            # sohouse_text_extracted_info에서도 가격 정보 추출 시도
            sohouse_info = kv_data.get('sohouse_text_extracted_info', {})
            if not deposit_range and sohouse_info.get('deposit'):
                deposit_range = sohouse_info.get('deposit', '')
            if not monthly_rent_range and sohouse_info.get('rent'):
                monthly_rent_range = sohouse_info.get('rent', '')
            
            # 보증금 범위 파싱 (예: "15,000,000원 ~ 55,000,000원")
            deposit_min, deposit_max = None, None
            if deposit_range:
                deposit_values = re.findall(r'[\d,]+', deposit_range.replace('원', ''))
                if len(deposit_values) >= 2:
                    deposit_min = self._parse_krw(deposit_values[0])
                    deposit_max = self._parse_krw(deposit_values[1])
                elif len(deposit_values) == 1:
                    deposit_min = deposit_max = self._parse_krw(deposit_values[0])
            
            # 월세 범위 파싱 (예: "350,000원 ~ 44,000원")
            rent_min, rent_max = None, None
            if monthly_rent_range:
                rent_values = re.findall(r'[\d,]+', monthly_rent_range.replace('원', ''))
                if len(rent_values) >= 2:
                    rent_min = self._parse_krw(rent_values[0])
                    rent_max = self._parse_krw(rent_values[1])
                elif len(rent_values) == 1:
                    rent_min = rent_max = self._parse_krw(rent_values[0])
            
            logger.info(f"[DEBUG] 가격 정보 추출: deposit_range='{deposit_range}', monthly_rent_range='{monthly_rent_range}'")
            logger.info(f"[DEBUG] 파싱 결과: deposit={deposit_min}~{deposit_max}, rent={rent_min}~{rent_max}")
            
            return deposit_min, deposit_max, rent_min, rent_max
            
        except Exception as e:
            logger.error(f"KV 데이터에서 가격 정보 추출 실패: {e}")
            return None, None, None, None

    def extract_area_from_kv(self, kv_data: Dict) -> tuple:
        """
        KV JSON 데이터에서 면적 정보 추출
        
        Args:
            kv_data: KV JSON 데이터
        
        Returns:
            (area_min_m2, area_max_m2)
        """
        try:
            # housing_specific에서 면적 정보 추출
            housing_specific = kv_data.get('housing_specific', {})
            
            # building_details에서 면적 정보 추출
            building_details = kv_data.get('building_details', {})
            total_floor_area = building_details.get('total_floor_area', '')
            
            # 면적 정보 파싱 (예: "498.94㎡")
            area_values = []
            if total_floor_area:
                try:
                    area_match = re.search(r'([\d.]+)㎡', total_floor_area)
                    if area_match:
                        area_value = float(area_match.group(1))
                        if 10 <= area_value <= 200:  # 10㎡ ~ 200㎡ 범위
                            area_values.append(area_value)
                except:
                    pass
            
            if area_values:
                return min(area_values), max(area_values)
            
            return None, None
            
        except Exception as e:
            logger.error(f"KV 데이터에서 면적 정보 추출 실패: {e}")
            return None, None

    def update_notices_with_kv_data(self, normalized_data: Dict, raw_data_dir: Path) -> None:
        """
        KV JSON 데이터를 사용하여 notices 업데이트 (테스트 파일 로직 완전 반영)
        
        Args:
            normalized_data: 정규화된 데이터
            raw_data_dir: raw 데이터 디렉토리 경로
        """
        notices = normalized_data.get('notices', [])
        units = normalized_data.get('units', [])
        
        logger.info(f"🔧 update_notices_with_kv_data 시작: {len(notices)}개 공고 처리")
        
        for notice in notices:
            notice_id = notice['id']
            
            # 1. original_data 제거
            if 'notice_extra' in notice and 'original_data' in notice['notice_extra']:
                del notice['notice_extra']['original_data']
            
            # 2. unit_type 관련 필드 제거
            if 'unit_type' in notice:
                del notice['unit_type']
            
            # 3. building_type은 이미 _normalize_notice_with_raw에서 올바르게 설정되었으므로 건드리지 않음
            
            # 3. 1차: KV JSON 파일에서 보증금/월세/면적 정보 가져오기
            kv_json_path = notice.get('notice_extra', {}).get('kv_json_path', '')
            if kv_json_path:
                kv_file_path = raw_data_dir / kv_json_path
                if kv_file_path.exists():
                    try:
                        with open(kv_file_path, 'r', encoding='utf-8') as f:
                            kv_data = json.load(f)
                        
                        # KV에서 가격 정보 추출
                        kv_deposit_min, kv_deposit_max, kv_rent_min, kv_rent_max = self.extract_prices_from_kv(kv_data)
                        if kv_deposit_min is not None:
                            notice['deposit_min'] = kv_deposit_min
                            notice['deposit_max'] = kv_deposit_max
                            logger.info(f"✅ 공고 {notice_id}: 가격 정보 업데이트 - 보증금 {kv_deposit_min}~{kv_deposit_max}, 월세 {kv_rent_min}~{kv_rent_max}")
                        if kv_rent_min is not None:
                            notice['rent_min'] = kv_rent_min
                            notice['rent_max'] = kv_rent_max
                        
                        # KV에서 면적 정보 추출
                        kv_area_min, kv_area_max = self.extract_area_from_kv(kv_data)
                        if kv_area_min is not None:
                            notice['area_min_m2'] = kv_area_min
                            notice['area_max_m2'] = kv_area_max
                            logger.info(f"✅ 공고 {notice_id}: 면적 정보 업데이트 - {kv_area_min}~{kv_area_max}㎡")
                            
                    except Exception as e:
                        logger.error(f"KV 파일 읽기 실패 {kv_file_path}: {e}")
                else:
                    logger.warning(f"KV 파일이 존재하지 않음: {kv_file_path}")
            else:
                logger.warning(f"공고 {notice_id}: kv_json_path가 없음")
            
            # 4. 2차: Units 데이터에서 실제 값들을 검증하여 min/max 업데이트 (0이 아닌 값만)
            unit_areas = []
            unit_deposits = []
            unit_rents = []
            
            for unit in units:
                if unit.get('notice_id') == notice_id:
                    # 면적 정보 (0이 아닌 값만)
                    if unit.get('area_m2') is not None and unit.get('area_m2') != 0:
                        unit_areas.append(unit['area_m2'])
                    
                    # 보증금 정보 (0이 아닌 값만)
                    if unit.get('deposit') is not None and unit.get('deposit') != 0:
                        unit_deposits.append(unit['deposit'])
                    
                    # 월세 정보 (0이 아닌 값만)
                    if unit.get('rent') is not None and unit.get('rent') != 0:
                        unit_rents.append(unit['rent'])
            
            # Units 데이터로 업데이트 (기존 KV 데이터가 있으면 보완, 없으면 대체)
            if unit_areas:
                if notice.get('area_min_m2') is None:
                    notice['area_min_m2'] = min(unit_areas)
                    notice['area_max_m2'] = max(unit_areas)
                else:
                    # KV 데이터와 Units 데이터를 비교하여 더 정확한 값 사용
                    kv_area_min = notice.get('area_min_m2', 0)
                    kv_area_max = notice.get('area_max_m2', 0)
                    unit_area_min = min(unit_areas)
                    unit_area_max = max(unit_areas)
                    
                    # Units 데이터가 더 상세하면 업데이트
                    if (unit_area_max - unit_area_min) > (kv_area_max - kv_area_min):
                        notice['area_min_m2'] = unit_area_min
                        notice['area_max_m2'] = unit_area_max
            
            if unit_deposits:
                if notice.get('deposit_min') is None:
                    notice['deposit_min'] = min(unit_deposits)
                    notice['deposit_max'] = max(unit_deposits)
                else:
                    # Units 데이터로 검증 및 업데이트
                    notice['deposit_min'] = min(notice.get('deposit_min', 0), min(unit_deposits))
                    notice['deposit_max'] = max(notice.get('deposit_max', 0), max(unit_deposits))
            
            if unit_rents:
                if notice.get('rent_min') is None:
                    notice['rent_min'] = min(unit_rents)
                    notice['rent_max'] = max(unit_rents)
                else:
                    # Units 데이터로 검증 및 업데이트
                    notice['rent_min'] = min(notice.get('rent_min', 0), min(unit_rents))
                    notice['rent_max'] = max(notice.get('rent_max', 0), max(unit_rents))
            
            # 5. 타임스탬프를 JSON 뒤로 이동 (테스트 파일과 동일한 순서)
            # 타임스탬프와 URL 필드들을 임시 저장
            detail_url = notice.pop('detail_url', '')
            list_url = notice.pop('list_url', '')
            posted_at = notice.pop('posted_at', None)
            last_modified = notice.pop('last_modified', None)
            apply_start_at = notice.pop('apply_start_at', None)
            apply_end_at = notice.pop('apply_end_at', None)
            
            # notice_extra 뒤에 추가
            notice['detail_url'] = detail_url
            notice['list_url'] = list_url
            notice['posted_at'] = posted_at
            notice['last_modified'] = last_modified
            notice['apply_start_at'] = apply_start_at
            notice['apply_end_at'] = apply_end_at

    # normalize_notice_with_raw 함수 제거 - normalizer.py의 _normalize_notice_with_raw 사용
    
    # normalize_notice_with_enriched 함수 제거 - normalizer.py의 _normalize_notice_with_raw 사용

# ----------------------------
# 2) 태그 정규화 함수들
# ----------------------------

def normalize_tags(row: pd.Series, notice_id: int) -> List[Dict]:
    """태그 데이터 정규화"""
    tags = []
    
    # 테마를 태그로 추가
    theme = str(row.get('theme', '')).strip()
    if theme and theme != 'nan':
        tags.append({
            'notice_id': notice_id,
            'tag': theme
        })
    
    # 지하철역을 태그로 추가
    subway = str(row.get('subway_station', '')).strip()
    if subway and subway != 'nan':
        tags.append({
            'notice_id': notice_id,
            'tag': f"지하철:{subway}"
        })
    
    # 자격요건을 태그로 추가
    eligibility = str(row.get('eligibility', '')).strip()
    if eligibility and eligibility != 'nan':
        tags.append({
            'notice_id': notice_id,
            'tag': f"자격요건:{eligibility}"
        })
    
    return tags

def normalize_facilities_tags(record: Dict, notice_id: int) -> List[Dict]:
    """KV/JSON 파일의 시설 정보를 태그로 정규화"""
    tags = []
    
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
                'subway': '지하철_중복',  # subway_station과 중복되므로 제외
                'bus': '버스',
                'nearby_마트': '마트',
                'nearby_병원': '병원',
                'nearby_학교': '학교',
                'nearby_시설': '시설',
                'nearby_카페': '카페'
            }
            
            tag_key = key_mapping.get(key, key)
            tags.append({
                'notice_id': notice_id,
                'tag': f"{tag_key}:{value}"
            })
    
    logger.info(f"[DEBUG] normalize_facilities_tags: notice_id={notice_id}, 생성된 태그 수={len(tags)}")
    return tags

# ----------------------------
# 3) 유틸리티 함수들
# ----------------------------

def _parse_datetime(value) -> Optional[datetime]:
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
