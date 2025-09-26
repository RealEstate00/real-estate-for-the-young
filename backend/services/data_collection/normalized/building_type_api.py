#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
건물 타입 API 모듈 (Building Type API)
===========================================
건물과 주거 유형을 분류하는 API 모듈
"""

import requests
import logging
from typing import Dict, Optional
import json

logger = logging.getLogger(__name__)

# ----------------------------
# 1) 건물 타입 API 클래스
# ----------------------------

class BuildingTypeAPI:
    """건물 타입 분류 API 클래스"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or self._load_api_key()
        self.base_url = "https://data.seoul.go.kr/dataList/OA-22415/S/1/datasetView.do"  # 서울시 데이터
    
    def _load_api_key(self) -> str:
        """API 키 로드"""
        import os
        api_key = os.getenv('SEOUL_API_KEY')
        if not api_key:
            raise ValueError("SEOUL_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return api_key
    
    def classify_building_type(self, address: str, building_name: str, description: str) -> Optional[Dict]:
        """
        건물과 주거 유형 분류 (USG_CD_NM API 사용)
        
        Args:
            address: 주소
            building_name: 건물명
            description: 설명
            
        Returns:
            분류 결과 딕셔너리
        """
        try:
            # USG_CD_NM API를 사용하여 건물 타입 분류
            usg_cd_nm = self._get_usg_cd_nm_from_address(address, building_name)
            
            if usg_cd_nm:
                return {
                    'building_type': usg_cd_nm,
                    'usg_cd_nm': usg_cd_nm,
                    'confidence': 0.9
                }
            else:
                # API 실패시 키워드 기반 분류로 fallback
                return self._classify_by_keywords(address, building_name, description)
            
        except Exception as e:
            logger.error(f"건물 타입 분류 오류: {e}")
            return None
    
    def _get_usg_cd_nm_from_address(self, address: str, building_name: str) -> Optional[str]:
        """
        주소와 건물명을 사용하여 USG_CD_NM 조회
        
        Args:
            address: 주소
            building_name: 건물명
            
        Returns:
            USG_CD_NM (용도코드명) 또는 None
        """
        try:
            # 서울시 공공데이터 API 엔드포인트
            base_url = "http://openapi.seoul.go.kr:8088"
            service_name = "vBigJtrFlrCbOuln"  # 서울시 건물용도코드 API
            
            # API 요청 URL 구성
            url = f"{base_url}/{self.api_key}/xml/{service_name}/1/5"
            
            # 요청 파라미터 (주소와 건물명으로 검색)
            params = {
                'ADDR': address,
                'BLDG_NM': building_name
            }
            
            logger.info(f"USG_CD_NM API 요청: {address}, {building_name}")
            
            # API 요청
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # XML 응답 파싱
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # 디버깅을 위한 XML 응답 로깅
            logger.info(f"[DEBUG] API 응답 XML: {response.text[:500]}...")
            
            # USG_CD_NM 추출
            rows = root.findall('.//row')
            logger.info(f"[DEBUG] API 응답에서 찾은 row 개수: {len(rows)}")
            
            if rows:
                first_row = rows[0]
                usg_cd_nm = first_row.find('USG_CD_NM')
                if usg_cd_nm is not None:
                    usg_cd_nm_text = usg_cd_nm.text
                    logger.info(f"USG_CD_NM 조회 성공: {usg_cd_nm_text}")
                    return usg_cd_nm_text
                else:
                    logger.warning("USG_CD_NM 필드를 찾을 수 없습니다.")
                    return None
            else:
                logger.warning(f"API 응답에 데이터가 없습니다: {address}, {building_name}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"USG_CD_NM API 요청 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"USG_CD_NM 조회 오류: {e}")
            return None
    
    def _classify_by_keywords(self, address: str, building_name: str, description: str) -> Dict:
        """키워드 기반 분류 (임시 구현)"""
        text = f"{address} {building_name} {description}".lower()
        
        # 건물 타입 분류
        building_type = 'unknown'
        if any(keyword in text for keyword in ['아파트', 'apartment', 'apt']):
            building_type = 'apartment'
        elif any(keyword in text for keyword in ['빌라', 'villa', '연립']):
            building_type = 'villa'
        elif any(keyword in text for keyword in ['원룸', '원룸', 'oneroom']):
            building_type = 'oneroom'
        elif any(keyword in text for keyword in ['오피스텔', 'office', '오피스']):
            building_type = 'officetel'
        elif any(keyword in text for keyword in ['단독', '주택', 'house']):
            building_type = 'house'
        
        # 주거 유형 분류
        housing_type = 'unknown'
        if any(keyword in text for keyword in ['전세', 'jeonse']):
            housing_type = 'jeonse'
        elif any(keyword in text for keyword in ['월세', 'wolse', 'rent']):
            housing_type = 'wolse'
        elif any(keyword in text for keyword in ['매매', 'sale', 'purchase']):
            housing_type = 'sale'
        
        return {
            'building_type': building_type,
            'housing_type': housing_type,
            'confidence': 0.8  # 신뢰도 (0-1)
        }

# ----------------------------
# 2) 편의 함수
# ----------------------------

def classify_building_type(address: str, building_name: str = "", description: str = "") -> Dict[str, str]:
    """건물 타입 분류 편의 함수"""
    api = BuildingTypeAPI()
    result = api.classify_building_type(address, building_name, description)
    if result:
        return {
            'building_type': result.get('building_type', 'other'),
            'housing_type': result.get('housing_type', 'other')
        }
    return {'building_type': 'other', 'housing_type': 'other'}
