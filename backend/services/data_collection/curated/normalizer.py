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

# 외부 라이브러리 디버그 로그 억제
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)

# 환경변수 로드
load_dotenv()

from backend.services.data_collection.normalized.address_api import normalize_address, AddressNormalizerError
from backend.services.data_collection.normalized.building_type_api import classify_building_type
from backend.services.data_collection.normalized.price_utils import parse_krw_one, parse_krw_range, sanity_monthly
from backend.services.data_collection.normalized.building_form import map_building_form
from backend.services.data_collection.normalized.unit_normalizer import UnitNormalizer
from backend.services.data_collection.normalized.notice_normalizer import NoticeNormalizer

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

    # 2) Building type and Unit type mapping
    text_blob = str(record)
    form_raw = (
        record.get("cohouse_text_extracted_info", {}) or
        record.get("sohouse_text_extracted_info", {})
    )
    
    # Map building_type from extracted info
    building_type_val = None
    if form_raw:
        building_type_val = form_raw.get("building_type")
    building_type_mapped = map_building_form(building_type_val, text_blob)
    record.setdefault("_normalized", {})["building_type"] = building_type_mapped
    if building_type_mapped == "기타":
        record.setdefault("_audit", {})["building_type_hint"] = building_type_val
    
    # Map unit_type from extracted info
    unit_type_val = None
    if form_raw:
        unit_type_val = form_raw.get("unit_type")
    record.setdefault("_normalized", {})["unit_type"] = unit_type_val or ""

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
        self.address_id_map = {}  # 주소 중복 체크를 위한 맵
        self.raw_data_dir = None
        
        # 새로운 정규화 클래스들
        self.unit_normalizer = UnitNormalizer()
        self.notice_normalizer = NoticeNormalizer()
        
    def normalize_raw_data(self, raw_csv_path: Path, save_callback=None) -> Dict[str, List[Dict]]:
        """
        raw CSV 데이터를 정규화된 테이블 데이터로 변환
        
        Args:
            raw_csv_path: raw.csv 파일 경로
            
        Returns:
            정규화된 테이블 데이터 딕셔너리
        """
        logger.info(f"정규화 시작: {raw_csv_path}")
        
        # raw_data_dir 설정
        self.raw_data_dir = raw_csv_path.parent
        
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
        
        # 정규화된 데이터 준비
        normalized_data = {
            'platforms': list(self.platforms.values()),
            'addresses': list(self.addresses.values()),
            'notices': self.notices,
            'units': self.units,
            'unit_features': self.unit_features,
            'notice_tags': self.notice_tags
        }
        
        # 새로운 기능들 적용
        logger.info("🔧 Units 데이터를 raw/tables 데이터로 업데이트 중...")
        self.unit_normalizer.update_units_with_occupancy_data(normalized_data, self.raw_data_dir)
        
        # update_notices_with_kv_data 제거 - building_type은 이미 _normalize_notice_with_raw에서 올바르게 설정됨
        # logger.info("🔧 Notices 데이터를 KV JSON 데이터로 업데이트 중...")
        # self.notice_normalizer.update_notices_with_kv_data(normalized_data, self.raw_data_dir)
        
        # 실시간 저장 (콜백이 제공된 경우) - 모든 업데이트 후 저장
        if save_callback:
            for table_name, data in normalized_data.items():
                save_callback(table_name, data)
        
        return normalized_data
    
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
            # 추가 raw 데이터
            "house_name": str(row.get('house_name', '')).strip(),
            "description": str(row.get('description', '')).strip(),
            "theme": str(row.get('theme', '')).strip(),
            "subway_station": str(row.get('subway_station', '')).strip(),
            "eligibility": str(row.get('eligibility', '')).strip(),
            "deposit": row.get('deposit'),
            "rent": row.get('rent'),
            "maintenance_fee": row.get('maintenance_fee'),
            "area_m2": row.get('area_m2'),
            "room_count": row.get('room_count'),
            "bathroom_count": row.get('bathroom_count'),
            "floor": row.get('floor'),
            "unit_type": str(row.get('unit_type', '')).strip(),
            "image_paths": str(row.get('image_paths', '')).strip(),
            "floorplan_paths": str(row.get('floorplan_paths', '')).strip(),
            "document_paths": str(row.get('document_paths', '')).strip(),
            "kv_json_path": str(row.get('kv_json_path', '')).strip(),
            "last_modified": row.get('last_modified'),
            "crawl_date": row.get('crawl_date'),
            "detail_url": str(row.get('detail_url', '')).strip(),
            "list_url": str(row.get('list_url', '')).strip(),
        }

        # 0-1) 후처리 훅 실행(주소/가격/유형)
        enriched = postprocess_enrich(record)

        # 0-2) 하드 실패(격리 대상)이면 스킵
        if enriched.get("_rejects"):
            logger.error(f"격리 대상: {enriched['_rejects']}")
            return

        # 1. 플랫폼 정규화
        platform_id = self._normalize_platform(row)
        
        # 2. 주소 정규화 (vworld API 사용)
        address_id = self._normalize_address_from_raw(record["address"], row.get('notice_id', ''))
        
        # 3. 공고 정규화
        notice_id = self._normalize_notice_with_raw(row, address_id, record)
        
        # 4. 유닛 정규화 (occupancy 데이터 사용)
        kv_data = self._load_kv_data(record.get('kv_json_path', ''))
        unit_index = int(row.get('unit_index', 0))
        units = self._normalize_units_from_occupancy(row.get('notice_id', ''), notice_id, kv_data, unit_index)
        self.units.extend(units)
        
        # 5. 공고의 면적/층수 범위 업데이트
        self._update_notice_ranges(notice_id, units)
        
        # 6. 태그 정규화
        self._normalize_tags(row, notice_id)
        
        # 7. 인근 시설 정보 태그 정규화 (KV 데이터 포함)
        from .notice_normalizer import normalize_facilities_tags
        # KV 데이터를 record에 추가
        record['kv_data'] = kv_data
        facilities_tags = normalize_facilities_tags(record, notice_id)
        self.notice_tags.extend(facilities_tags)

    def _update_notice_ranges(self, notice_id: int, units: List[Dict]):
        """공고의 면적/층수/가격 범위 업데이트"""
        if not units:
            return
        
        # 면적 범위 계산
        areas = [unit.get('area_m2') for unit in units if unit.get('area_m2') is not None]
        floors = [unit.get('floor') for unit in units if unit.get('floor') is not None]
        
        # 가격 범위 계산
        deposits = [unit.get('deposit') for unit in units if unit.get('deposit') is not None and unit.get('deposit', 0) > 0]
        rents = [unit.get('rent') for unit in units if unit.get('rent') is not None and unit.get('rent', 0) > 0]
        
        # 해당 공고 찾아서 업데이트
        for notice in self.notices:
            if notice['id'] == notice_id:
                if areas:
                    notice['area_min_m2'] = min(areas)
                    notice['area_max_m2'] = max(areas)
                if floors:
                    notice['floor_min'] = min(floors)
                    notice['floor_max'] = max(floors)
                if deposits:
                    notice['deposit_min'] = min(deposits)
                    notice['deposit_max'] = max(deposits)
                    logger.info(f"✅ 공고 {notice_id}: 가격 정보 업데이트 - 보증금 {min(deposits)}~{max(deposits)}")
                if rents:
                    notice['rent_min'] = min(rents)
                    notice['rent_max'] = max(rents)
                    logger.info(f"✅ 공고 {notice_id}: 가격 정보 업데이트 - 월세 {min(rents)}~{max(rents)}")
                break
    
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
                'address_raw': normalized_address,
                'PLAT_PLC': self._extract_plat_plc(normalized_address),  # 대지위치
                'SGG_CD_NM': self._extract_sgg_cd_nm(normalized_address),  # 시군구코드
                'STDG_CD_NM': self._extract_stdg_cd_nm(normalized_address),  # 법정동코드
                'MN_LOTNO': self._extract_mn_lotno(normalized_address),  # 주지번
                'SUB_LOTNO': self._extract_sub_lotno(normalized_address),  # 부지번
                'lat': None,
                'lon': None
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
            'source_key': str(row.get('notice_id', '')),
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
        nm = enriched.get("_normalized", {})
        # Use normalized unit_type if available, otherwise fallback to CSV data
        unit_type = nm.get("unit_type") or str(row.get('unit_type', '')).strip()
        building_type = nm.get("building_type")
        area_m2 = self._extract_area_from_unit_type(unit_type)

        unit = {
            'id': unit_id,
            'notice_id': notice_id,
            'unit_code': f"unit_{unit_id}",
            'unit_type': unit_type,
            'deposit': self._parse_numeric(row.get('deposit')),
            'rent': self._parse_numeric(row.get('rent')),
            'maintenance_fee': self._parse_numeric(row.get('maintenance_fee')),
            'area_m2': area_m2,
            'room_number': self._extract_room_count(unit_type),
            'occupancy': None,  # 기본값
            'occupancy_available_at': None,
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
        
        # 지하철역 태그는 normalize_facilities_tags에서 처리하므로 여기서는 제거
    
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
    
    def _extract_plat_plc(self, address: str) -> str:
        """대지위치 추출 (전체 주소)"""
        return address.strip()
    
    def _extract_sgg_cd_nm(self, address: str) -> str:
        """시군구코드명 추출 (API 활용)"""
        # 1차: 정규식으로 추출 시도
        gu_pattern = r'([가-힣]+구)'
        match = re.search(gu_pattern, address)
        if match:
            return match.group(1)
        
        # 2차: API 호출로 정확한 정보 획득
        return self._get_address_from_api(address, 'sgg_cd_nm')
    
    def _extract_stdg_cd_nm(self, address: str) -> str:
        """법정동코드명 추출 (API 활용)"""
        # 1차: 정규식으로 추출 시도
        dong_pattern = r'([가-힣]+(?:동|가|나|다|라|마|바|사|아|자|차|카|타|파|하))'
        match = re.search(dong_pattern, address)
        if match:
            return match.group(1)
        
        # 2차: API 호출로 정확한 정보 획득
        return self._get_address_from_api(address, 'stdg_cd_nm')
    
    def _extract_mn_lotno(self, address: str) -> Optional[int]:
        """주지번 추출 (API 활용)"""
        # 1차: 정규식으로 추출 시도
        lot_pattern = r'(\d+)(?:-\d+)?'
        match = re.search(lot_pattern, address)
        if match:
            return int(match.group(1))
        
        # 2차: API 호출로 정확한 정보 획득
        api_result = self._get_address_from_api(address, 'mn_lotno')
        return int(api_result) if api_result else None
    
    def _extract_sub_lotno(self, address: str) -> Optional[int]:
        """부지번 추출 (API 활용)"""
        # 1차: 정규식으로 추출 시도
        sub_lot_pattern = r'\d+-(\d+)'
        match = re.search(sub_lot_pattern, address)
        if match:
            return int(match.group(1))
        
        # 2차: API 호출로 정확한 정보 획득
        api_result = self._get_address_from_api(address, 'sub_lotno')
        return int(api_result) if api_result else None
    
    def _get_address_from_api(self, address: str, field: str) -> str:
        """주소 API를 통한 정확한 주소 정보 획득"""
        try:
            # 환경변수 로딩
            from dotenv import load_dotenv
            load_dotenv()
            
            from .address_api import AddressAPI
            
            # API 클라이언트 초기화 (캐싱을 위해 한 번만 생성)
            if not hasattr(self, '_address_api'):
                self._address_api = AddressAPI()
            
            # API 키가 유효하지 않으면 정규식으로 대체
            if not self._address_api.api_key or self._address_api.api_key == "YOUR_API_KEY_HERE":
                return ''
            
            # 주소 정규화
            normalized = self._address_api.normalize_address(address)
            
            if normalized:
                return normalized.get(field, '')
            
        except ImportError:
            # API 모듈이 없으면 조용히 정규식으로 대체
            pass
        except Exception as e:
            # API 오류 시 조용히 정규식으로 대체 (로그 스팸 방지)
            pass
        
        return ''
    
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
    
    def _normalize_address_from_raw(self, address_raw: str, notice_id: str) -> Optional[int]:
        """raw.csv에서 추출한 주소를 JUSO API로 정규화"""
        logger.info(f"raw.csv에서 추출한 주소: '{address_raw}'")
        if not address_raw:
            logger.info("주소가 비어있음")
            return None
        address_raw = preprocess_address(address_raw)
        if address_raw in self.address_id_map:
            return self.address_id_map[address_raw]
        try:
            normalized = normalize_address(address_raw)
            if not normalized:
                logger.warning(f"주소 정규화 실패: {address_raw}")
                return None
            return self._normalize_address_with_juso({
                'address_raw': address_raw,
                'notice_id': notice_id,
                'normalized': normalized
            })
        except Exception as e:
            logger.error(f"주소 정규화 API 오류: {e}")
            return None
    
    def _normalize_address_with_juso(self, address_data: Dict) -> int:
        """JUSO API 결과를 사용한 주소 정규화"""
        address_raw = address_data['address_raw']
        normalized = address_data['normalized']
        
        # 중복 체크를 위한 키 생성
        dedup_key = f"{normalized.get('emd_cd', '')}_{normalized.get('road_name_full', '')}_{normalized.get('building_main_no', '')}"
        dedup_key = dedup_key.lower().strip()
        
        if dedup_key in self.addresses:
            return self.addresses[dedup_key]['id']
        
        address_id = len(self.addresses) + 1
        
        # 주소 정규화 데이터 구성 (vworld API 결과 사용)
        address_info = {
            'id': address_id,
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
    
    def _classify_building_type(self, building_info: str) -> Dict[str, str]:
        """건물 정보에서 건물 유형과 주거 유형을 분류"""
        return classify_building_type(building_info)
    
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
        """KV 데이터에서 가격 정보 추출 - notice_normalizer의 로직 사용"""
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
                    try:
                        deposit_value = float(deposit_info.replace('만원', '').replace(',', '').strip()) * 10000
                        deposit_min = deposit_value
                        deposit_max = deposit_value
                    except:
                        pass
            
            # 월세 정보 추출
            rent_info = sohouse_info.get('rent', '')
            rent_min = None
            rent_max = None
            
            if rent_info:
                # "35만원 ~ 4.4만원" 형태 파싱
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


    def _normalize_notice_with_raw(self, row: pd.Series, address_id: Optional[int], record: Dict) -> int:
        """raw 데이터를 사용한 공고 정규화"""
        notice_id = len(self.notices) + 1
        
        # 플랫폼 ID 결정
        platform_id = 2 if 'sohouse' in str(row.get('notice_id', '')) else 1
        
        # KV JSON 데이터 로드
        kv_data = self._load_kv_data(record.get('kv_json_path', ''))
        
        # 이미지, 플로어플랜, 문서 존재 여부 확인
        image_paths = row.get('image_paths', '')
        floorplan_paths = row.get('floorplan_paths', '')
        document_paths = row.get('document_paths', '')
        
        # KV 데이터에서 floorplan 정보 추출
        if not floorplan_paths or str(floorplan_paths) == 'nan':
            floorplan_paths = self._extract_floorplan_from_kv(kv_data)
        
        has_images = bool(image_paths and str(image_paths).strip() and str(image_paths) != 'nan')
        has_floorplan = bool(floorplan_paths and str(floorplan_paths).strip() and str(floorplan_paths) != 'nan')
        has_documents = bool(document_paths and str(document_paths).strip() and str(document_paths) != 'nan')
        
        # KV 데이터에서 가격 정보 추출
        deposit_min, deposit_max, rent_min, rent_max = self._extract_prices_from_kv(kv_data)
        
        # KV 데이터에서 면적 정보 추출
        area_min_m2, area_max_m2 = self._extract_area_from_kv(kv_data)
        
        # building_type 처리 (raw.csv와 API 값 비교)
        raw_building_type = row.get('building_type', '')  # raw.csv에서 가져오기
        api_building_type = ''
        
        # API로 building_type 조회
        try:
            from .building_type_api import BuildingTypeAPI
            building_type_api = BuildingTypeAPI()
            address = record.get('address', '')
            building_name = record.get('house_name', '')
            description = record.get('description', '')
            
            building_type_result = building_type_api.classify_building_type(address, building_name, description)
            api_building_type = building_type_result.get('building_type', '')
        except Exception as e:
            logger.warning(f"building_type API 조회 실패: {e}")
        
        # building_type 최종 결정 (raw.csv 우선, API는 참고용으로만 사용)
        final_building_type = 'unknown'
        if raw_building_type:
            # raw 데이터가 있으면 우선 사용
            final_building_type = raw_building_type
            if api_building_type and api_building_type != raw_building_type:
                # API 결과가 다르면 참고용으로 추가 (하지만 신뢰도 낮음)
                final_building_type = f"{raw_building_type} (API: {api_building_type})"
        elif api_building_type:
            # raw 데이터가 없을 때만 API 결과 사용
            final_building_type = f"{api_building_type}(공식)"
        
        logger.info(f"[DEBUG] building_type 결정: raw='{raw_building_type}', api='{api_building_type}', final='{final_building_type}'")
        
        # 공고 정보 구성 (테스트 파일과 동일한 순서)
        notice_data = {
            'id': notice_id,
            'platform_id': platform_id,
            'source': 'unknown',
            'source_key': row.get('notice_id', ''),
            'title': record.get('house_name', '') or record.get('building_details', {}).get('address', ''),
            'status': 'open',
            'address_raw': record.get('address', ''),
            'address_id': address_id,
            'building_type': final_building_type,  # API와 비교한 최종 값
            'deposit_min': deposit_min,
            'deposit_max': deposit_max,
            'rent_min': rent_min,
            'rent_max': rent_max,
            'area_min_m2': area_min_m2,
            'area_max_m2': area_max_m2,
            'floor_min': None,    # units에서 계산
            'floor_max': None,    # units에서 계산
            'description_raw': record.get('description', ''),
            'notice_extra': {
                'image_paths': image_paths,
                'floorplan_paths': floorplan_paths,
                'document_paths': document_paths,
                'kv_json_path': record.get('kv_json_path', '')
            },
            'has_images': has_images,
            'has_floorplan': has_floorplan,
            'has_documents': has_documents,
            'detail_url': record.get('detail_url', ''),
            'list_url': record.get('list_url', ''),
            'posted_at': self._parse_datetime(record.get('last_modified')),
            'last_modified': self._parse_datetime(record.get('last_modified')),
            'apply_start_at': None,
            'apply_end_at': None
        }
        
        self.notices.append(notice_data)
        return notice_id
    
    def _load_occupancy_data(self, notice_id: str, unit_index: int = 0) -> pd.DataFrame:
        """occupancy CSV 파일 로드"""
        try:
            if 'sohouse' in notice_id:
                # sohouse의 경우 모든 occupancy 파일을 검색해서 해당 notice_id가 있는 파일 찾기
                tables_dir = Path(self.raw_data_dir) / 'tables'
                occupancy_files = list(tables_dir.glob("detail_*_occupancy.csv"))
                occupancy_files.sort(key=lambda x: int(x.stem.split('_')[1]))
                
                logger.info(f"[DEBUG] sohouse occupancy 파일 검색: {len(occupancy_files)}개 파일")
                
                for occupancy_file in occupancy_files:
                    try:
                        df = pd.read_csv(occupancy_file)
                        if not df.empty and 'notice_id' in df.columns:
                            matching_rows = df[df['notice_id'] == notice_id]
                            if not matching_rows.empty:
                                logger.info(f"[DEBUG] sohouse occupancy 데이터 발견: {occupancy_file} - {len(matching_rows)}개 레코드")
                                return matching_rows
                    except Exception as e:
                        logger.warning(f"[DEBUG] occupancy 파일 읽기 실패 {occupancy_file}: {e}")
                        continue
                
                logger.warning(f"[DEBUG] sohouse notice_id {notice_id}에 해당하는 occupancy 데이터를 찾을 수 없음")
                return pd.DataFrame()
            else:
                # cohouse의 경우 unit_index 사용
                detail_num = f"{unit_index:04d}"
                occupancy_file = Path(self.raw_data_dir) / 'tables' / f'detail_{detail_num}_occupancy.csv'
                
                logger.info(f"[DEBUG] cohouse occupancy 파일: {occupancy_file}")
                
                if occupancy_file.exists():
                    df = pd.read_csv(occupancy_file)
                    logger.info(f"[DEBUG] cohouse occupancy 데이터 로드 성공: {len(df)}개 레코드")
                    return df
                else:
                    logger.warning(f"[DEBUG] cohouse occupancy 파일이 존재하지 않음: {occupancy_file}")
        except Exception as e:
            logger.warning(f"occupancy 데이터 로드 실패: {notice_id}, 오류: {e}")
        
        return pd.DataFrame()

    def _normalize_units_from_occupancy(self, notice_id: str, notice_id_int: int, kv_data: Dict, unit_index: int = 0) -> List[Dict]:
        """occupancy 데이터에서 units 정규화"""
        occupancy_df = self._load_occupancy_data(notice_id, unit_index)
        units = []
        
        logger.info(f"[DEBUG] _normalize_units_from_occupancy: notice_id={notice_id}, occupancy_df.empty={occupancy_df.empty}")
        
        if occupancy_df.empty:
            # occupancy 데이터가 없으면 기본 unit 생성
            logger.info(f"[DEBUG] occupancy 데이터 없음, 기본 unit 생성")
            default_unit = self._create_default_unit(notice_id, kv_data)
            
            # unit_features에 추가 (room_count, bathroom_count, direction)
            unit_features = {
                'unit_id': default_unit['id'],
                'room_count': None,
                'bathroom_count': None,
                'direction': None
            }
            self.unit_features.append(unit_features)
            
            return [default_unit]
        
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
                    occupancy_available_at = pd.to_datetime(occupancy_date).strftime('%Y-%m-%d %H:%M:%S')
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
                'id': unit_id,
                'notice_id': notice_id,
                'unit_code': unit_row.get('space_id', f'unit_{unit_id}'),
                'unit_type': raw_unit_type or 'unknown', 
                'deposit': deposit,
                'rent': rent,
                'maintenance_fee': maintenance_fee,
                'area_m2': area_m2,
                'floor': floor,
                'room_number': room_number,  # 호수 정보 추가
                'occupancy_available_at': occupancy_available_at,
                'capacity': capacity,  # 인원 수
                'occupancy_available': occupancy_available,  # 입주가능 여부
            }
            
            units.append(unit_data)
            
            # unit_features에 추가 (room_count, bathroom_count, direction)
            unit_features = {
                'unit_id': unit_id,
                'room_count': None,  # occupancy 데이터에는 없음
                'bathroom_count': None,  # occupancy 데이터에는 없음
                'direction': None
            }
            self.unit_features.append(unit_features)
        
        return units

    def _get_raw_unit_type(self, notice_id: str) -> str:
        """raw CSV에서 notice_id에 해당하는 unit_type을 가져오기"""
        # raw CSV 파일 경로들
        raw_csv_paths = [
            Path("backend/data/raw/cohouse/2025-09-25/raw.csv"),
            Path("backend/data/raw/sohouse/2025-09-25/raw.csv")
        ]
        
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

    def _create_default_unit(self, notice_id: str, kv_data: Dict) -> Dict:
        """기본 unit 생성 (occupancy 데이터가 없는 경우)"""
        unit_id = len(self.units) + 1
        
        # raw CSV에서 해당 notice_id의 unit_type 가져오기
        raw_unit_type = self._get_raw_unit_type(notice_id)
        
        return {
            'id': unit_id,
            'notice_id': str(notice_id),
            'unit_code': f'unit_{unit_id}',
            'unit_type': raw_unit_type or 'unknown',  # raw CSV에서 가져온 unit_type 사용
            'deposit': None,
            'rent': None,
            'maintenance_fee': None,
            'area_m2': None,
            'floor': None,
            'room_number': None,  # 호수 정보 추가
            'occupancy_available_at': None,
        }

    def _parse_krw_amount(self, amount_str: str) -> Optional[int]:
        """한국 원화 금액 파싱 (예: "15,000,000원" -> 15000000)"""
        if not amount_str or str(amount_str) == 'nan':
            return None
        
        # 숫자만 추출
        numbers = re.findall(r'[\d,]+', amount_str.replace('원', ''))
        if numbers:
            try:
                return int(numbers[0].replace(',', ''))
            except:
                pass
        return None


    def _normalize_unit_with_building_type(self, row: pd.Series, notice_id: int, record: Dict):
        """building type 분류를 포함한 유닛 정규화 (deprecated - occupancy 데이터 사용)"""
        # 이 메서드는 이제 occupancy 데이터를 사용하므로 호출하지 않음
        pass
    
    def _add_unit_features(self, unit_id: int, type_classification: Dict, record: Dict):
        """유닛 특성 추가"""
        # 건물 유형 특성
        building_type = type_classification.get('building_type', 'other')
        self.unit_features.append({
            'id': len(self.unit_features) + 1,
            'unit_id': unit_id,
            'feature_type': 'building_type',
            'feature_value': building_type,
            'feature_extra': {
                'classification': type_classification,
                'description': f"건물 유형: {building_type}"
            }
        })
    