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
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

from backend.services.data_collection.curated.address_api import normalize_address, AddressNormalizerError
from backend.services.data_collection.curated.price_utils import parse_krw_one, parse_krw_range, sanity_monthly
from backend.services.data_collection.curated.building_form import map_building_form

logger = logging.getLogger(__name__)

def preprocess_address(addr_raw: str) -> str:
    """주소 전처리 - JUSO API 매칭률 향상을 위한 정리"""
    if not addr_raw:
        return addr_raw
    
    import re
    
    # 1. 건물번호가 비정상적으로 큰 경우 수정 (예: 217 912 -> 217)
    # 도로명 + 건물번호 패턴 찾기
    road_pattern = r'([가-힣]+로\d*[가-힣]*)\s+(\d+)\s+(\d{3,})'
    match = re.search(road_pattern, addr_raw)
    if match:
        road_name = match.group(1)
        building_num = match.group(2)
        large_num = match.group(3)
        # 큰 번호를 제거하고 도로명 + 건물번호만 사용
        addr_raw = re.sub(road_pattern, f'{road_name} {building_num}', addr_raw)
        logger.info(f"주소 전처리: 건물번호 정리 -> {addr_raw}")
    
    # 2. 지번 주소는 그대로 유지 (JUSO API가 지번 주소도 처리 가능)
    # 다만 불필요한 정보만 제거
    
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

def postprocess_enrich(record: dict) -> dict:
    """Enrich the parsed record with address, price, and typed enums."""
    # 1) Address
    addr_raw = record.get("address")
    if addr_raw:
        logger.info(f"원본 주소: {addr_raw}")
        
        # 주소 전처리
        addr_processed = preprocess_address(addr_raw)
        logger.info(f"전처리된 주소: {addr_processed}")
        
        # 여러 패턴으로 주소 정규화 시도
        success = False
        for attempt, addr_to_try in enumerate([addr_processed, addr_raw]):
            if attempt > 0:
                logger.info(f"주소 정규화 재시도 ({attempt+1}): {addr_to_try}")
            else:
                logger.info(f"주소 정규화 시도: {addr_to_try}")
            
            try:
                addr = normalize_address(addr_to_try)
                record.setdefault("_normalized", {})["address"] = addr
                logger.info(f"주소 정규화 성공: {addr}")
                success = True
                break
            except AddressNormalizerError as e:
                logger.warning(f"주소 정규화 실패 (시도 {attempt+1}): {addr_to_try} - {e}")
                if attempt == 1:  # 마지막 시도
                    logger.error(f"주소 정규화 최종 실패: {addr_raw} - {e}")
                    record.setdefault("_rejects", []).append({"field":"address","reason":str(e)})
    else:
        logger.warning("주소가 없습니다")

    # 2) Building form (기타 치환)
    text_blob = str(record)
    form_raw = (
        record.get("cohouse_text_extracted_info", {}) or
        record.get("sohouse_text_extracted_info", {})
    )
    form_val = None
    if form_raw:
        form_val = form_raw.get("housing_form") or form_raw.get("housing_type")
    mapped = map_building_form(form_val, text_blob)
    record.setdefault("_normalized", {})["building_form"] = mapped
    if mapped == "기타":
        record.setdefault("_audit", {})["building_form_hint"] = form_val

    # 3) Prices (deposit/monthly/maintenance)
    # Strategy: prefer structured fields; fallback to extracted_patterns.prices
    deposit_min = deposit_max = monthly_min = monthly_max = 0

    hs = record.get("housing_specific", {})
    if "deposit_range" in hs:
        deposit_min, deposit_max = parse_krw_range(hs["deposit_range"])
    if "monthly_rent_range" in hs:
        monthly_min, monthly_max = parse_krw_range(hs["monthly_rent_range"])

    # Fallback from extracted_patterns.prices
    if not (deposit_min or deposit_max or monthly_min or monthly_max):
        prices = (form_raw or {}).get("extracted_patterns", {}).get("prices", [])
        # Heuristic: large numbers → deposit, smaller → monthly/maintenance
        nums = [parse_krw_one(p) for p in prices]
        deposits = [n for n in nums if n >= 5_000_000]
        monthlies = [n for n in nums if 0 < n < 5_000_000]
        if deposits:
            deposit_min, deposit_max = min(deposits), max(deposits)
        if monthlies:
            monthly_min, monthly_max = min(monthlies), max(monthlies)

    # Sanity check for monthly (e.g., 44,000 bug)
    if monthly_min and not sanity_monthly(monthly_min):
        record.setdefault("_rejects", []).append(
            {"field":"monthly_min","value":monthly_min,"reason":"monthly < 100,000"}
        )
    if monthly_max and not sanity_monthly(monthly_max):
        record.setdefault("_rejects", []).append(
            {"field":"monthly_max","value":monthly_max,"reason":"monthly < 100,000"}
        )

    record["_normalized"].update({
        "deposit_min": deposit_min, "deposit_max": deposit_max,
        "monthly_min": monthly_min, "monthly_max": monthly_max
    })
    return record

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

        # 0) 원본+부가 JSON 구성 (후처리 훅에 넘길 record)
        kv_json_path = row.get('kv_json_path', '')
        extracted = {}
        if kv_json_path and Path(kv_json_path).exists():
            try:
                with open(kv_json_path, 'r', encoding='utf-8') as f:
                    extracted = json.load(f)
            except Exception as e:
                logger.warning(f"JSON 파싱 실패 {kv_json_path}: {e}")

        record = {
            "address": str(row.get('address', '')).strip(),
            "building_details": {"address": str(row.get('address', '')).strip()},
            # 플랫폼별 추출 결과(있으면 훅이 사용)
            "cohouse_text_extracted_info": extracted.get("cohouse_text_extracted_info", {}),
            "sohouse_text_extracted_info": extracted.get("sohouse_text_extracted_info", {}),
            "housing_specific": extracted.get("housing_specific", {}),
        }

        # 0-1) 후처리 훅 실행(주소/가격/유형)
        enriched = postprocess_enrich(record)

        # 0-2) 하드 실패(격리 대상)이면 스킵
        if enriched.get("_rejects"):
            logger.error(f"격리 대상: {enriched['_rejects']}")
            return

        # 1. 플랫폼 정규화
        platform_id = self._normalize_platform(row)
        
        # 2. 주소 정규화
        address_id = self._normalize_address_with_enriched(enriched)
        
        # 3. 공고 정규화
        notice_id  = self._normalize_notice_with_enriched(row, platform_id, address_id, enriched)
        
        # 4. 유닛 정규화
        self._normalize_unit_with_enriched(row, notice_id, enriched)
        
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
    
    def _normalize_address_with_enriched(self, enriched: dict) -> Optional[int]:
        addr = (enriched.get("_normalized") or {}).get("address")
        if not addr:
            return None
        dedup_key = (addr.get("road_full") or "").lower().strip()
        if not dedup_key:
            dedup_key = f"{addr.get('bcode','')}|{(addr.get('jibun_full') or '').lower().strip()}"

        if dedup_key not in self.addresses:
            address_id = len(self.addresses) + 1
            # 시군구/법정동/지번 형태로 정규화
            si_do = addr.get("sido", "")
            si_gun_gu = addr.get("sigungu", "")
            eupmyeon_dong = addr.get("eupmyeon_dong", "")
            jibun_full = addr.get("jibun_full", "")
            
            # 시군구/법정동/지번 형태의 정규화된 주소 생성
            normalized_address = f"{si_do} {si_gun_gu} {eupmyeon_dong}"
            if jibun_full:
                # 지번에서 시군구/법정동/지번만 추출
                jibun_parts = jibun_full.split()
                if len(jibun_parts) >= 3:
                    # "서울특별시 동대문구 회기동 103-271" -> "서울특별시 동대문구 회기동 103-271"
                    normalized_address = " ".join(jibun_parts[:3]) + " " + jibun_parts[3] if len(jibun_parts) > 3 else " ".join(jibun_parts[:3])
            
            self.addresses[dedup_key] = {
                'id': address_id,
                'address_raw': addr.get("road_full") or addr.get("jibun_full"),
                'address_norm': normalized_address,
                'si_do': si_do,
                'si_gun_gu': si_gun_gu,
                'eupmyeon_dong': eupmyeon_dong,
                'road_name': None,  # 도로명 주소 제거
                'zipcode': None,
                'lat': addr.get("y"),   # API returns y(lat), x(lon)
                'lon': addr.get("x"),
                'bcode': addr.get("bcode"),
                'jibun_full': jibun_full,
            }
        return self.addresses[dedup_key]['id']

    def _normalize_notice_with_enriched(self, row, platform_id: int, address_id: int, enriched: dict) -> int:
        notice_id = len(self.notices) + 1
        posted_at = self._parse_datetime(row.get('last_modified'))
        crawl_date = self._parse_datetime(row.get('crawl_date'))
        nm = enriched.get("_normalized", {})
        deposit_min = nm.get("deposit_min") or self._parse_numeric(row.get('deposit_min'))
        deposit_max = nm.get("deposit_max") or self._parse_numeric(row.get('deposit_max'))
        rent_min    = nm.get("monthly_min") or self._parse_numeric(row.get('rent_min'))
        rent_max    = nm.get("monthly_max") or self._parse_numeric(row.get('rent_max'))

        notice = {
            'id': notice_id,
            'platform_id': platform_id,
            'source': row.get('platform', ''),
            'source_key': str(row.get('record_id', '')),
            'title': str(row.get('house_name', '')).strip(),
            'detail_url': str(row.get('detail_url', '')).strip(),
            'list_url': str(row.get('list_url', '')).strip(),
            'status': 'open',
            'posted_at': posted_at,
            'last_modified': posted_at,
            'apply_start_at': None,
            'apply_end_at': None,
            'address_raw': str(row.get('address', '')).strip(),
            'address_id': address_id,
            'deposit_min': deposit_min,
            'deposit_max': deposit_max,
            'rent_min': rent_min,
            'rent_max': rent_max,
            'area_min_m2': self._parse_numeric(row.get('area_min_m2')),
            'area_max_m2': self._parse_numeric(row.get('area_max_m2')),
            'floor_min': self._parse_int(row.get('floor_min')),
            'floor_max': self._parse_int(row.get('floor_max')),
            'description_raw': str(row.get('description', '')).strip(),
            'notice_extra': {},
            'has_images': bool(row.get('image_paths', '')),
            'has_floorplan': False,
            'has_documents': False,
            'created_at': crawl_date,
            'updated_at': crawl_date
        }
        self.notices.append(notice)
        return notice_id

    def _normalize_unit_with_enriched(self, row, notice_id: int, enriched: dict):
        unit_id = len(self.units) + 1
        unit_type = str(row.get('unit_type', '')).strip()
        nm = enriched.get("_normalized", {})
        building_form = nm.get("building_form")
        area_m2 = self._extract_area_from_unit_type(unit_type)

        unit = {
            'id': unit_id,
            'notice_id': notice_id,
            'unit_code': f"unit_{unit_id}",
            'unit_type': unit_type,              # fix: no 'unit_t'
            'tenure': 'rent',
            'deposit': nm.get("deposit_min"),
            'rent': nm.get("monthly_min"),
            'maintenance_fee': self._parse_numeric(row.get('maintenance_fee')),
            'area_m2': area_m2,
            'room_count': self._extract_room_count(unit_type),
            'bathroom_count': 1,
            'floor': self._parse_int(row.get('floor')),
            'direction': None,
            'occupancy_available_at': None,
            'unit_extra': {
                'building_type': building_form,
                'theme': str(row.get('theme', '')).strip(),
                'subway_station': str(row.get('subway_station', '')).strip(),
                'eligibility': str(row.get('eligibility', '')).strip()
            },
            'created_at': self._parse_datetime(row.get('crawl_date')),
            'updated_at': self._parse_datetime(row.get('crawl_date'))
        }
        self.units.append(unit)
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
        """Infer room count from Korean keywords."""
        if '쓰리룸' in unit_type or '3룸' in unit_type:
            return 3
        if '투룸' in unit_type or '2룸' in unit_type:
            return 2
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
