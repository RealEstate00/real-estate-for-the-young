#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
데이터 정규화 모듈
크롤링된 raw 데이터를 정규화된 다중 테이블 구조로 변환
"""

import pandas as pd
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataNormalizer:
    """크롤링 데이터를 정규화된 테이블 구조로 변환하는 클래스"""
    
    def __init__(self):
        self.platforms = {}
        self.addresses = {}
        self.notices = []
        self.units = []
        self.unit_features = []
        self.notice_tags = []
        
    def normalize_raw_data(self, raw_csv_path: Path) -> Dict[str, List[Dict]]:
        """
        raw CSV 데이터를 정규화된 테이블 데이터로 변환
        
        Args:
            raw_csv_path: raw.csv 파일 경로
            
        Returns:
            정규화된 테이블 데이터 딕셔너리
        """
        logger.info(f"정규화 시작: {raw_csv_path}")
        
        # CSV 데이터 로드
        df = pd.read_csv(raw_csv_path)
        logger.info(f"로드된 레코드 수: {len(df)}")
        
        # 각 행을 정규화
        for idx, row in df.iterrows():
            try:
                self._normalize_row(row)
            except Exception as e:
                logger.error(f"행 {idx} 정규화 실패: {e}")
                continue
                
        return {
            'platforms': list(self.platforms.values()),
            'addresses': list(self.addresses.values()),
            'notices': self.notices,
            'units': self.units,
            'unit_features': self.unit_features,
            'notice_tags': self.notice_tags
        }
    
    def _normalize_row(self, row: pd.Series):
        """단일 행을 정규화"""
        # 1. 플랫폼 정규화
        platform_id = self._normalize_platform(row)
        
        # 2. 주소 정규화
        address_id = self._normalize_address(row)
        
        # 3. 공고 정규화
        notice_id = self._normalize_notice(row, platform_id, address_id)
        
        # 4. 유닛 정규화
        self._normalize_unit(row, notice_id)
        
        # 5. 태그 정규화
        self._normalize_tags(row, notice_id)
    
    def _normalize_platform(self, row: pd.Series) -> int:
        """플랫폼 데이터 정규화"""
        platform_code = row.get('platform', '')
        platform_id = row.get('platform_id', 1)
        
        if platform_code not in self.platforms:
            self.platforms[platform_code] = {
                'id': platform_id,
                'code': platform_code,
                'name': self._get_platform_name(platform_code),
                'base_url': self._get_platform_url(platform_code),
                'is_active': True
            }
        
        return platform_id
    
    def _normalize_address(self, row: pd.Series) -> int:
        """주소 데이터 정규화"""
        address_raw = str(row.get('address', '')).strip()
        
        if not address_raw or address_raw == 'nan':
            return None
            
        # 주소 정규화 키 생성 (중복 방지)
        address_key = address_raw.lower().strip()
        
        if address_key not in self.addresses:
            address_id = len(self.addresses) + 1
            normalized_address = self._normalize_address_string(address_raw)
            
            self.addresses[address_key] = {
                'id': address_id,
                'address_raw': address_raw,
                'address_norm': normalized_address,
                'si_do': self._extract_si_do(address_raw),
                'si_gun_gu': self._extract_si_gun_gu(address_raw),
                'road_name': self._extract_road_name(address_raw),
                'zipcode': None,
                'lat': None,
                'lon': None
            }
        
        return self.addresses[address_key]['id']
    
    def _normalize_notice(self, row: pd.Series, platform_id: int, address_id: int) -> int:
        """공고 데이터 정규화 (schema.sql 구조에 맞춤)"""
        notice_id = len(self.notices) + 1
        
        # 날짜 파싱
        posted_at = self._parse_datetime(row.get('last_modified'))
        crawl_date = self._parse_datetime(row.get('crawl_date'))
        
        # JSON 데이터 파싱
        kv_json_path = row.get('kv_json_path', '')
        notice_extra = {}
        if kv_json_path and Path(kv_json_path).exists():
            try:
                with open(kv_json_path, 'r', encoding='utf-8') as f:
                    notice_extra = json.load(f)
            except Exception as e:
                logger.warning(f"JSON 파싱 실패 {kv_json_path}: {e}")
        
        # schema.sql의 notices 테이블 구조에 맞춤
        notice = {
            'id': notice_id,
            'platform_id': platform_id,
            'source': row.get('platform', ''),
            'source_key': str(row.get('record_id', '')),
            'title': str(row.get('house_name', '')).strip(),
            'detail_url': str(row.get('detail_url', '')).strip(),
            'list_url': str(row.get('list_url', '')).strip(),
            'status': 'open',  # listing_status enum
            'posted_at': posted_at,
            'last_modified': posted_at,
            'apply_start_at': None,
            'apply_end_at': None,
            'address_raw': str(row.get('address', '')).strip(),
            'address_id': address_id,
            'deposit_min': self._parse_numeric(row.get('deposit_min')),
            'deposit_max': self._parse_numeric(row.get('deposit_max')),
            'rent_min': self._parse_numeric(row.get('rent_min')),
            'rent_max': self._parse_numeric(row.get('rent_max')),
            'area_min_m2': self._parse_numeric(row.get('area_min_m2')),
            'area_max_m2': self._parse_numeric(row.get('area_max_m2')),
            'floor_min': self._parse_int(row.get('floor_min')),
            'floor_max': self._parse_int(row.get('floor_max')),
            'description_raw': str(row.get('description', '')).strip(),
            'notice_extra': notice_extra,
            'has_images': bool(row.get('image_paths', '')),
            'has_floorplan': False,
            'has_documents': False,
            'created_at': crawl_date,
            'updated_at': crawl_date
        }
        
        self.notices.append(notice)
        return notice_id
    
    def _normalize_unit(self, row: pd.Series, notice_id: int):
        """유닛 데이터 정규화"""
        unit_id = len(self.units) + 1
        
        # 유닛 정보 추출
        unit_type = str(row.get('unit_type', '')).strip()
        building_type = str(row.get('building_type', '')).strip()
        
        # 면적 정보 추출 (unit_type에서 추출 시도)
        area_m2 = self._extract_area_from_unit_type(unit_type)
        
        # unit_index 추출 (새로 추가된 필드)
        unit_index = row.get('unit_index', 0)
        unit = {
            'id': unit_id,
            'notice_id': notice_id,
            'unit_code': f"unit_{unit_id}",
            'unit_type': unit_t,
            'tenure': 'rent',  # 기본값
            'deposit': self._parse_numeric(row.get('deposit')),
            'rent': self._parse_numeric(row.get('rent')),
            'maintenance_fee': self._parse_numeric(row.get('maintenance_fee')),
            'area_m2': area_m2,
            'room_count': self._extract_room_count(unit_type),
            'bathroom_count': 1,  # 기본값
            'floor': self._parse_int(row.get('floor')),
            'direction': None,
            'occupancy_available_at': None,
            'unit_extra': {
                'building_type': building_type,
                'theme': str(row.get('theme', '')).strip(),
                'subway_station': str(row.get('subway_station', '')).strip(),
                'eligibility': str(row.get('eligibility', '')).strip(),
                'unit_index': unit_index,  # unit_index 추가
                'record_id': str(row.get('record_id', '')),  # record_id 추가
            },
            'created_at': self._parse_datetime(row.get('crawl_date')),
            'updated_at': self._parse_datetime(row.get('crawl_date'))
        }
        
        self.units.append(unit)
        
        # 유닛 특징 추가
        self._add_unit_features(unit_id, unit)
    
    def _normalize_tags(self, row: pd.Series, notice_id: int):
        """태그 데이터 정규화"""
        # 테마를 태그로 추가
        theme = str(row.get('theme', '')).strip()
        if theme and theme != 'nan':
            self.notice_tags.append({
                'notice_id': notice_id,
                'tag': theme
            })
        
        # 지하철역을 태그로 추가
        subway = str(row.get('subway_station', '')).strip()
        if subway and subway != 'nan':
            self.notice_tags.append({
                'notice_id': notice_id,
                'tag': f"지하철:{subway}"
            })
    
    def _add_unit_features(self, unit_id: int, unit: Dict):
        """유닛 특징 추가"""
        features = [
            ('building_type', unit['unit_extra'].get('building_type', '')),
            ('theme', unit['unit_extra'].get('theme', '')),
            ('subway_station', unit['unit_extra'].get('subway_station', '')),
            ('eligibility', unit['unit_extra'].get('eligibility', ''))
        ]
        
        for feature, value in features:
            if value and str(value).strip() and str(value).strip() != 'nan':
                self.unit_features.append({
                    'unit_id': unit_id,
                    'feature': feature,
                    'value': str(value).strip()
                })
    
    # 유틸리티 메서드들
    def _get_platform_name(self, code: str) -> str:
        """플랫폼 코드로 이름 반환"""
        names = {
            'sohouse': '서울시 사회주택',
            'cohouse': '서울시 공동체주택',
            'youth': '청년안심주택',
            'sh': 'SH공사',
            'lh': 'LH공사'
        }
        return names.get(code, code)
    
    def _get_platform_url(self, code: str) -> str:
        """플랫폼 코드로 URL 반환"""
        urls = {
            'sohouse': 'https://soco.seoul.go.kr',
            'cohouse': 'https://soco.seoul.go.kr',
            'youth': 'https://youth.seoul.go.kr',
            'sh': 'https://www.sh.co.kr',
            'lh': 'https://www.lh.or.kr'
        }
        return urls.get(code, '')
    
    def _normalize_address_string(self, address: str) -> str:
        """주소 문자열 정규화"""
        # 기본 정규화 로직
        normalized = re.sub(r'\s+', ' ', address.strip())
        return normalized
    
    def _extract_si_do(self, address: str) -> str:
        """시/도 추출"""
        if '서울' in address:
            return '서울특별시'
        return ''
    
    def _extract_si_gun_gu(self, address: str) -> str:
        """시/군/구 추출"""
        # 서울시 구 추출
        gu_pattern = r'([가-힣]+구)'
        match = re.search(gu_pattern, address)
        return match.group(1) if match else ''
    
    def _extract_road_name(self, address: str) -> str:
        """도로명 추출"""
        # 도로명 추출 로직 (간단한 버전)
        road_pattern = r'([가-힣]+로\d*[가-힣]*)'
        match = re.search(road_pattern, address)
        return match.group(1) if match else ''
    
    def _extract_area_from_unit_type(self, unit_type: str) -> Optional[float]:
        """유닛 타입에서 면적 추출"""
        # 예: "원룸(20㎡)" -> 20.0
        area_pattern = r'(\d+(?:\.\d+)?)㎡'
        match = re.search(area_pattern, unit_type)
        return float(match.group(1)) if match else None
    
    def _extract_room_count(self, unit_type: str) -> int:
        """유닛 타입에서 방 개수 추출"""
        if '원룸' in unit_type:
            return 1
        elif '투룸' in unit_type or '쓰리룸' in unit_type:
            return 2
        elif '쓰리룸' in unit_type:
            return 3
        return 1
    
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
                numbers = re.findall(r'\d+', value)
                return float(numbers[0]) if numbers else None
            return float(value)
        except:
            return None
    
    def _parse_int(self, value) -> Optional[int]:
        """정수 파싱"""
        numeric = self._parse_numeric(value)
        return int(numeric) if numeric is not None else None
