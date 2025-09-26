#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
주소 API 모듈 (Address API)
===========================================
vworld API를 사용하여 주소 정규화를 담당하는 모듈
"""

import requests
import json
import logging
from typing import Dict, Optional, List
from pathlib import Path
import time
from .jibun_api import JusoAPI
from .building_type_api import BuildingTypeAPI
from .coordinate_api import VWorldCoordinateAPI

logger = logging.getLogger(__name__)

# ----------------------------
# 1) 주소 API 클래스
# ----------------------------

class AddressAPI:
    """통합 주소 정규화 클래스 - JUSO API와 주거유형 API 통합"""
    
    def __init__(self, juso_api_key: str = None, vworld_api_key: str = None, housing_data_dir: str = None):
        self.juso_api_key = juso_api_key or self._load_juso_api_key()
        self.vworld_api_key = vworld_api_key or self._load_vworld_api_key()
        
        # API 클래스들 초기화
        self.juso_api = JusoAPI(self.juso_api_key) if self.juso_api_key else None
        self.vworld_api = VWorldCoordinateAPI(self.vworld_api_key) if self.vworld_api_key else None
        self.building_type_api = BuildingTypeAPI() if self.juso_api_key else None
        
        self.session = requests.Session()
    
    def _load_juso_api_key(self) -> str:
        """JUSO API 키 로드"""
        import os
        api_key = os.getenv('JUSO_API_KEY')
        if not api_key:
            raise ValueError("JUSO_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return api_key
    
    def _load_vworld_api_key(self) -> str:
        """VWorld API 키 로드"""
        import os
        api_key = os.getenv('VWORLD_API_KEY')
        if not api_key:
            logger.warning("VWORLD_API_KEY 환경변수가 설정되지 않았습니다. 좌표 정보를 가져올 수 없습니다.")
        return api_key
    
    
    def normalize_address(self, address: str, building_name: str = '', description: str = '') -> Optional[Dict]:
        """통합 주소 정규화 - JUSO API와 주거유형 API 통합"""
        try:
            result = {
                'address_raw': address,
                'road_name_full': '',
                'jibun_name_full': '',
                'main_jibun': '',
                'sub_jibun': '',
                'ctpv_nm': '',
                'sgg_nm': '',
                'emd_cd': '',
                'emd_nm': '',
                'road_name': '',
                'building_name': building_name,
                'building_main_no': '',
                'building_sub_no': '',
                'lat': None,
                'lon': None
            }
            
            # 1. JUSO API로 도로명주소 및 지번주소 정보 가져오기
            if self.juso_api:
                juso_info = self.juso_api.search_address(address)
                if juso_info:
                    result.update({
                        'road_name_full': juso_info.get('road_addr', ''),
                        'jibun_name_full': juso_info.get('jibun_addr', ''),
                        'ctpv_nm': juso_info.get('si_nm', ''),
                        'sgg_nm': juso_info.get('sgg_nm', ''),
                        'emd_nm': juso_info.get('emd_nm', ''),
                        'road_name': juso_info.get('road_name', ''),
                        'building_main_no': juso_info.get('building_main_no', ''),
                        'building_sub_no': juso_info.get('building_sub_no', ''),
                        'emd_cd': juso_info.get('adm_cd', '')
                    })
                    
                    # 지번주소에서 주지번, 부지번 추출
                    jibun_addr = juso_info.get('jibun_addr', '')
                    if jibun_addr:
                        main_jibun, sub_jibun = self._extract_jibun_numbers(jibun_addr)
                        result.update({
                            'main_jibun': main_jibun,
                            'sub_jibun': sub_jibun
                        })
                    
                    # 도로명주소에서 빌딩명 추출
                    road_addr = juso_info.get('road_addr', '')
                    if road_addr:
                        building_name = self._extract_building_name(road_addr)
                        if building_name:
                            result['building_name'] = building_name
                    
                    # VWorld API로 좌표 정보 가져오기
                    if self.vworld_api:
                        road_addr = juso_info.get('road_addr', '')
                        if road_addr:
                            # 괄호 안의 동 정보 제거 (VWorld API 호환성을 위해)
                            import re
                            clean_road_addr = re.sub(r'\s*\([^)]*\)', '', road_addr).strip()
                            coords = self.vworld_api.get_coordinates(clean_road_addr)
                            if coords:
                                lat, lon = coords
                                result.update({
                                    'lat': lat,
                                    'lon': lon
                                })
                else:
                    # JUSO API 응답이 없을 때 기본값 설정
                    logger.warning(f"JUSO API 응답 없음: {address}")
                    # 주소에서 기본 정보 추출 시도
                    address_parts = address.split()
                    if len(address_parts) >= 2:
                        result['ctpv_nm'] = address_parts[0]  # 시도명
                        if len(address_parts) >= 3:
                            result['sgg_nm'] = address_parts[1]  # 시군구명
                            if len(address_parts) >= 4:
                                result['emd_nm'] = address_parts[2]  # 읍면동명
            
            
            return result
            
        except Exception as e:
            logger.error(f"주소 정규화 오류: {e}")
            return None
    
    def _extract_jibun_numbers(self, jibun_addr: str) -> tuple:
        """지번주소에서 주지번, 부지번 추출"""
        import re
        
        if not jibun_addr:
            return '', ''
        
        # 지번 패턴 찾기: "동 123-456" 또는 "동 123"
        # 예: "서울특별시 중구 충무로4가 120-3" -> main_jibun="120", sub_jibun="3"
        # 동 이름 뒤의 공백과 숫자 패턴을 찾음 (동 이름에 숫자가 포함된 경우 고려)
        pattern = r'[가-힣0-9]+\s+(\d+)(?:-(\d+))?'
        match = re.search(pattern, jibun_addr)
        
        if match:
            main_jibun = match.group(1)
            sub_jibun = match.group(2) if match.group(2) else ''
            return main_jibun, sub_jibun
        
        return '', ''
    
    def _extract_building_name(self, road_addr: str) -> str:
        """도로명주소에서 빌딩명 추출"""
        import re
        
        if not road_addr:
            return ''
        
        # 괄호 안의 빌딩명 추출
        # 예: "서울특별시 동대문구 회기로12나길 18 (회기동, 소리소문 회기)" -> "소리소문 회기"
        pattern = r'\([^,]+,\s*([^)]+)\)'
        match = re.search(pattern, road_addr)
        
        if match:
            building_name = match.group(1).strip()
            # 불필요한 단어 제거
            building_name = re.sub(r'\s+(주택|빌라|아파트|오피스텔|건물)$', '', building_name)
            return building_name
        
        return ''
    
    

# ----------------------------
# 2) 편의 함수
# ----------------------------

def normalize_address(address: str, building_name: str = '', description: str = '') -> Optional[Dict]:
    """주소 정규화 편의 함수"""
    api = AddressAPI()
    return api.normalize_address(address, building_name, description)

# ----------------------------
# 3) 예외 클래스
# ----------------------------

class AddressNormalizerError(Exception):
    """주소 정규화 오류"""
    pass
