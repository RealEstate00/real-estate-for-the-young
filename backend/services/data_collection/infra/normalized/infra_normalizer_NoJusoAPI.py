#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
인프라 데이터 정규화 모듈
서울 열린데이터광장 API 데이터를 infra 스키마에 맞게 정규화
"""

import pandas as pd
from pathlib import Path
import os
import json
import re
import requests
import time
from typing import List, Dict, Optional, Any, Tuple
import logging
from dotenv import load_dotenv
import chardet
from datetime import datetime

# 환경변수 로드
load_dotenv()

# JUSO API 대신 좌표 API만 사용

logger = logging.getLogger(__name__)

# ----- API 클라이언트 클래스들 -----

class CoordinateAPI:
    """좌표 변환 API 클라이언트 (주소 정규화 + 좌표 변환 통합)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.vworld.kr/req/address"
        self.bcode_data = self._load_bcode_data()
    
    def _load_bcode_data(self) -> Dict[str, str]:
        """법정동코드 전체자료.txt 파일을 로드하여 딕셔너리로 변환"""
        bcode_file = Path(__file__).resolve().parents[5] / "backend" / "data" / "rtms" / "법정동코드 전체자료.txt"
        
        if not bcode_file.exists():
            logger.error(f"법정동코드 파일을 찾을 수 없습니다: {bcode_file}")
            return {}
        
        bcode_dict = {}
        try:
            with open(bcode_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 헤더 스킵하고 데이터 파싱
            for line in lines[1:]:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    bcode, bname, status = parts[0], parts[1], parts[2]
                    if status == '존재':  # 폐지여부가 '존재'인 경우만
                        bcode_dict[bname] = bcode
            
            logger.info(f"법정동코드 데이터 로드 완료: {len(bcode_dict)}개")
            return bcode_dict
            
        except Exception as e:
            logger.error(f"법정동코드 파일 로드 실패: {e}")
            return {}
    
    def normalize_address(self, address: str, address_type: str = 'ROAD') -> Dict[str, Any]:
        """주소를 정규화하고 좌표, 법정동코드를 추출"""
        if not address:
            return {
                'address_raw': address,
                'address_nm': None,
                'address_id': None,
                'lat': None,
                'lon': None,
                'normalization_success': False
            }
            
        try:
            params = {
                'service': 'address',
                'request': 'getcoord',
                'version': '2.0',
                'crs': 'epsg:4326',
                'address': address,
                'refine': 'true',
                'simple': 'false',
                'format': 'xml',
                'type': address_type,
                'key': self.api_key
            }
            
            logger.info(f"🌍 좌표 변환 API 요청: {address}")
            logger.info(f"📋 좌표 변환 API 요청 파라미터: {params}")
            
            response = requests.get(self.base_url, params=params, timeout=10)
            logger.info(f"🔍 좌표 변환 API 응답 상태: {response.status_code}")
            logger.info(f"📄 좌표 변환 API 전체 응답 내용:")
            logger.info(f"{response.text}")
            
            response.raise_for_status()
            
            # XML 파싱하여 좌표, 주소명, 법정동코드 추출
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # 1. 좌표 추출
            lat, lon = None, None
            point = root.find('.//point')
            if point is not None:
                x = point.find('x')
                y = point.find('y')
                if x is not None and y is not None and x.text and y.text:
                    try:
                        lon = float(x.text)
                        lat = float(y.text)
                        logger.info(f"✅ 좌표 추출 성공: lat={lat}, lon={lon}")
                    except ValueError as e:
                        logger.error(f"❌ 좌표 변환 실패 (값 변환 오류): {e}")
            
            # 2. refined structure에서 주소명 추출
            address_nm = None
            structure = root.find('.//structure')
            if structure is not None:
                level1 = structure.find('level1')
                level2 = structure.find('level2')
                level3 = structure.find('level3')
                
                if level1 is not None and level2 is not None and level3 is not None:
                    if level1.text and level2.text and level3.text:
                        address_nm = f"{level1.text} {level2.text} {level3.text}"
                        logger.info(f"✅ 주소명 추출 성공: {address_nm}")
            
            # 3. 법정동코드 추출
            address_id = None
            if address_nm and self.bcode_data:
                # 법정동코드 딕셔너리에서 검색
                address_id = self.bcode_data.get(address_nm)
                if address_id:
                    logger.info(f"✅ 법정동코드 추출 성공: {address_id}")
                else:
                    logger.warning(f"⚠️ 법정동코드를 찾을 수 없음: {address_nm}")
            
            # 성공 여부 판단
            success = lat is not None and lon is not None
            
            result = {
                'address_raw': address,
                'address_nm': address_nm,
                'address_id': address_id,
                'lat': lat,
                'lon': lon,
                'normalization_success': success
            }
            
            logger.info(f"🎯 최종 정규화 결과:")
            logger.info(f"   - address_raw: {result['address_raw']}")
            logger.info(f"   - address_nm: {result['address_nm']}")
            logger.info(f"   - address_id: {result['address_id']}")
            logger.info(f"   - lat: {result['lat']}")
            logger.info(f"   - lon: {result['lon']}")
            logger.info(f"   - normalization_success: {result['normalization_success']}")
            
            return result
            
        except Exception as e:
            logger.error(f"주소 정규화 실패: {address} - {e}")
            logger.error(f"요청 URL: {self.base_url}")
            logger.error(f"요청 파라미터: {params}")
            return {
                'address_raw': address,
                'address_nm': None,
                'address_id': None,
                'lat': None,
                'lon': None,
                'normalization_success': False
            }

def detect_address_type(address: str) -> str:
    """주소가 도로명주소인지 지번주소인지 감지"""
    if not address:
        return "unknown"
    
    # 지번주소 패턴: ~동 + 숫자 (우선순위 높음)
    jibun_pattern = r'[가-힣]+동\s+\d+[-\d]*'
    if re.search(jibun_pattern, address):
        return "jibun"
    
    # 도로명주소 패턴: ~로/길/대로/가 + 숫자 (동명 제외)
    # 동명에 "길"이 포함된 경우(예: 신길동)는 지번주소로 처리
    road_pattern = r'[가-힣]+(?:로|길|대로|가)\d*[가-힣]*\s+\d+[-\d]*'
    if re.search(road_pattern, address):
        return "road"
    
    # '지하'가 포함된 도로명주소 패턴
    if re.search(r'[가-힣]+로\s+지하\d+', address) or re.search(r'[가-힣]+길\s+지하\d+', address):
        return "road"
    else:
        return "jibun"

def detect_file_encoding(file_path: Path) -> str:
    """파일의 인코딩을 자동으로 감지"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding_result = chardet.detect(raw_data)
            detected_encoding = encoding_result['encoding']
            confidence = encoding_result['confidence']
            
        logger.info(f"🔍 파일 인코딩 감지: {file_path.name} -> {detected_encoding} (신뢰도: {confidence:.2f})")
        
        # 신뢰도가 낮거나 None인 경우 UTF-8로 폴백
        if not detected_encoding or confidence < 0.7:
            logger.warning(f"⚠️ 인코딩 감지 신뢰도 낮음, UTF-8로 폴백: {file_path.name}")
            return 'utf-8'
            
        return detected_encoding
    except Exception as e:
        logger.error(f"❌ 인코딩 감지 실패: {file_path.name} - {e}")
        return 'utf-8'

def read_csv_with_auto_encoding(file_path: Path, **kwargs) -> pd.DataFrame:
    """인코딩을 자동으로 감지하여 CSV 파일을 읽기"""
    detected_encoding = detect_file_encoding(file_path)
    
    try:
        # 감지된 인코딩으로 파일 읽기
        df = pd.read_csv(file_path, encoding=detected_encoding, **kwargs)
        logger.info(f"✅ CSV 파일 읽기 성공: {file_path.name} (인코딩: {detected_encoding})")
        return df
    except UnicodeDecodeError:
        # 감지된 인코딩으로 실패하면 UTF-8로 재시도
        logger.warning(f"⚠️ {detected_encoding} 인코딩 실패, UTF-8로 재시도: {file_path.name}")
        df = pd.read_csv(file_path, encoding='utf-8', **kwargs)
        return df
    except Exception as e:
        logger.error(f"❌ CSV 파일 읽기 실패: {file_path.name} - {e}")
        raise

def preprocess_subway_address(addr_raw: str) -> str:
    """지하철역 주소 전처리 - 지하철역 특화 전처리"""
    if not addr_raw:
        return addr_raw
    
    import re
    
    # 지하철역 관련 전처리
    # 역명과 괄호 제거 (예: "신설동역(2호선)" → "")
    addr_raw = re.sub(r'\s+[가-힣]+역\([^)]*\)', '', addr_raw).strip()
    
    # 남은 괄호 제거 (예: "(2호선)" → "")
    addr_raw = re.sub(r'\s*\([^)]*\)', '', addr_raw).strip()
    
    return addr_raw

def preprocess_park_address(addr_raw: str) -> str:
    """공원 주소 전처리 - 공원 특화 전처리"""
    if not addr_raw:
        return addr_raw
    
    import re
    
    # 공원 특화 전처리
    # 괄호 안의 동 정보 제거 (예: "(예장동)" → "")
    addr_raw = re.sub(r'\s*\([^)]*동[^)]*\)', '', addr_raw).strip()
    
    # 공원명 제거 (예: "길동생태공원" → "")
    addr_raw = re.sub(r'\s+[가-힣]*공원[가-힣]*', '', addr_raw).strip()
    
    # 불필요한 공백 정리
    addr_raw = re.sub(r'\s+', ' ', addr_raw).strip()
    
    return addr_raw

def detect_address_type_enhanced(address: str) -> str:
    """주소 타입을 더 정확하게 감지"""
    if not address:
        return "unknown"
    
    import re
    
    # 지번주소 패턴: ~동 + 숫자 (우선순위 높음)
    jibun_pattern = r'[가-힣]+동\s+\d+[-\d]*'
    if re.search(jibun_pattern, address):
        return "jibun"
    
    # 도로명주소 패턴: ~로/길/대로/가 + 숫자 (동명 제외)
    # 동명에 "길"이 포함된 경우(예: 신길동)는 지번주소로 처리
    road_pattern = r'[가-힣]+(?:로|길|대로|가)\d*[가-힣]*\s+\d+[-\d]*'
    if re.search(road_pattern, address):
        return "road"
    
    # 일반주소 패턴: 시/구/동만 있는 경우 (동 뒤에 숫자 없음)
    general_pattern = r'[가-힣]+\s+[가-힣]+\s+[가-힣]+동(?:\s|$)'
    if re.search(general_pattern, address):
        return "general"
    
    # 더 간단한 일반주소 패턴: 시 구 동 형태
    simple_general_pattern = r'[가-힣]+\s+[가-힣]+\s+[가-힣]+동$'
    if re.search(simple_general_pattern, address):
        return "general"
    
    return "unknown"

def preprocess_address(addr_raw: str) -> str:
    """개선된 주소 전처리 - 좌표 API 매칭률 향상을 위한 정리"""
    if not addr_raw:
        return addr_raw
    
    import re
    
    # 0. 중복 주소 제거 (가장 먼저 적용)
    # 예: "서울특별시 양천구 목동중앙본로20길33 (목동, 목동골든빌) 서울특별시 양천구 목동중앙본로20길33 (목동, 목동골든빌)" 
    # -> "서울특별시 양천구 목동중앙본로20길33 (목동, 목동골든빌)"
    # 더 정확한 중복 제거: 최소 5글자 이상의 의미있는 중복만 제거
    addr_raw = re.sub(r'(.{5,}?)\s+\1\s*.*$', r'\1', addr_raw)  # 공백 있는 중복 (5글자 이상)
    # 공백 없는 중복은 더 엄격하게: 최소 10글자 이상
    addr_raw = re.sub(r'(.{10,}?)\1.*$', r'\1', addr_raw)  # 공백 없는 중복 (10글자 이상)
    
    # 0-1. 중복 주소 제거 (더 간단하고 효과적인 방법)
    # 예: "서울특별시 양천구 목동중앙본로20길33 (목동, 목동골든빌) 서울특별시 양천구 목동중앙본로20길33 (목동, 목동골든빌)"
    # -> "서울특별시 양천구 목동중앙본로20길33 (목동, 목동골든빌)"
    
    # 서울특별시로 시작하는 주소의 중복 제거
    addr_raw = re.sub(r'(서울특별시\s+[^서울특별시]*?)\s+서울특별시\s+.*$', r'\1', addr_raw)
    
    # 서울로 시작하는 주소의 중복 제거
    addr_raw = re.sub(r'(서울\s+[^서울]*?)\s+서울\s+.*$', r'\1', addr_raw)
    
    # 1. 도로명주소 끝의 괄호 제거 (대학교 주소 등) - 건물명만 제거하고 번지는 보존
    # 예: "서울 중랑구 서일대학길 22(면목동 49-3) 서일대학교" -> "서울 중랑구 서일대학길 22"
    # ~로 + 숫자 + 괄호 패턴 (건물명이 포함된 괄호만 제거)
    addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*\s+\d+[-\d]*)\s*\([^)]*(?:대학교|빌딩|타워|센터|마트|몰|아파트|오피스)[^)]*\).*$', r'\1', addr_raw)
    # ~길 + 숫자 + 괄호 패턴 (건물명이 포함된 괄호만 제거)
    addr_raw = re.sub(r'([가-힣]+길\d*[가-힣]*\s+\d+[-\d]*)\s*\([^)]*(?:대학교|빌딩|타워|센터|마트|몰|아파트|오피스)[^)]*\).*$', r'\1', addr_raw)
    
    # 2. 건물번호가 비정상적으로 큰 경우 수정 (예: 217 912 -> 217)
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
    
    # 2-1. 구체적 건물명 패턴 제거 (층수 정보 제거 전에 적용) - 상세 번지는 보존
    # 도로명+번지 이후의 건물명만 제거 (상세 번지 정보는 보존)
    # 예: "한강로2가 112-3 용산파크자이" -> "한강로2가 112-3"
    # 한글+숫자+가 패턴과 상세 번지 이후의 건물명 제거 (부지번 보존)
    # 주의: 부지번이 있는 경우는 건물명만 제거하고 부지번은 보존
    # 이 패턴은 새로운 규칙에서 처리하므로 주석 처리
    # addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*가\s+\d+[-\d]*)\s+[가-힣A-Z]{3,}(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오).*$', r'\1', addr_raw)
    addr_raw = re.sub(r'([가-힣]+길\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오).*$', r'\1', addr_raw)
    addr_raw = re.sub(r'([가-힣]+로\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오).*$', r'\1', addr_raw)
    
    # 특정 건물명 패턴 제거
    addr_raw = re.sub(r'\s+[A-Z]+타워.*$', '', addr_raw)  # "KR타워" 등
    addr_raw = re.sub(r'\s+[가-힣]+주택.*$', '', addr_raw)  # "삼성주택" 등
    addr_raw = re.sub(r'\s+[가-힣]+빌딩.*$', '', addr_raw)  # "삼성빌딩" 등
    addr_raw = re.sub(r'\s+[가-힣]+센터.*$', '', addr_raw)  # "문화센터" 등
    
    # 영문+숫자 조합 건물명 제거
    addr_raw = re.sub(r'\s+[A-Z]+\d+.*$', '', addr_raw)  # "KR4", "AB123" 등
    
    # 3. 불필요한 층수 정보 제거
    addr_raw = re.sub(r'\s+\d+\s*층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+전층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+\d+\s*~\s*\d+\s*층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+\d+,\d+.*층.*$', '', addr_raw)  # 2,3,4,5층 패턴
    addr_raw = re.sub(r'\s+\d+[Ff].*$', '', addr_raw)  # 1F, 2f 패턴
    # 추가 층수 패턴들
    addr_raw = re.sub(r'\s+지상\d+\s*~\s*\d+\s*층.*$', '', addr_raw)  # 지상1층~3층
    addr_raw = re.sub(r'\s+지하\d+\s*~\s*\d+\s*층.*$', '', addr_raw)  # 지하1층~3층
    addr_raw = re.sub(r'\s+지상\d+\s*층.*$', '', addr_raw)  # 지상1층
    addr_raw = re.sub(r'\s+지하\d+\s*층.*$', '', addr_raw)  # 지하1층
    # 새로 추가: 더 강력한 층수 정보 제거
    addr_raw = re.sub(r'\s+지하\d*층.*$', '', addr_raw)  # 지하1층, 지하층 등
    addr_raw = re.sub(r'\s+지상\d*층.*$', '', addr_raw)  # 지상2층, 지상층 등
    addr_raw = re.sub(r'\s+B\d+.*$', '', addr_raw)  # B1, B2 등
    
    # 4. 건물명 제거 (괄호 안의 내용)
    addr_raw = re.sub(r'\s*\([^)]*\)\s*', ' ', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+생활.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+빌.*$', '', addr_raw)
    # 추가 건물명 패턴들
    addr_raw = re.sub(r'\s+애스트리\d+.*$', '', addr_raw)  # 애스트리23
    addr_raw = re.sub(r'\s+사는자리.*$', '', addr_raw)  # 사는자리
    addr_raw = re.sub(r'\s+써드플레이스.*$', '', addr_raw)  # 써드플레이스 홍은7
    addr_raw = re.sub(r'\s+코이노니아.*$', '', addr_raw)  # 코이노니아스테이
    addr_raw = re.sub(r'\s+맑은구름집.*$', '', addr_raw)  # 맑은구름집
    addr_raw = re.sub(r'\s+너나들이.*$', '', addr_raw)  # 너나들이
    addr_raw = re.sub(r'\s+화곡동.*$', '', addr_raw)  # 화곡동 공동체주택
    # 추가 건물명 패턴들 (sohouse 실패 케이스)
    addr_raw = re.sub(r'\s+녹색친구들.*$', '', addr_raw)  # 녹색친구들 대조, 녹색친구들 창천
    addr_raw = re.sub(r'\s+함께주택.*$', '', addr_raw)  # 함께주택6호, 함께주택5호
    addr_raw = re.sub(r'\s+주상복합건물.*$', '', addr_raw)  # 주상복합건물
    
    
    # 5. 동/호수 제거 강화
    addr_raw = re.sub(r'\s+\d+동(\s+\d+호)?.*$', '', addr_raw)  # "101동", "101동 102호" 등
    addr_raw = re.sub(r'\s+\d+호.*$', '', addr_raw)  # "102호" 등
    addr_raw = re.sub(r'\s+[A-Z]\d+호.*$', '', addr_raw)  # "A101호", "B205호" 등
    # 추가: 모든 동/호수 패턴 제거 (나호, 다호 등 포함)
    addr_raw = re.sub(r'\s+[가-힣]+호.*$', '', addr_raw)  # "나호", "다호" 등 모든 호수
    
    # 6. 지번주소 정리 (~동 숫자 또는 ~동 숫자-숫자 뒤의 모든 문자 제거)
    # 예: "서울 종로구 동숭동 192-6 1" -> "서울 종로구 동숭동 192-6"
    # 예: "서울 광진구 능동 25 선화예술중고등학교" -> "서울 광진구 능동 25"
    # 주의: 부지번이 있는 경우는 제외 (예: 성수동1가 685-20)
    # 이 패턴은 새로운 규칙에서 처리하므로 주석 처리
    # addr_raw = re.sub(r'([가-힣]+동\s+\d+)\s+[가-힣].*$', r'\1', addr_raw)  # 부지번 없는 경우만
    
    # 새로 추가: 도로명+번지 이후의 건물명 제거 강화
    # 도로명길+숫자 이후 모든 한글 제거
    addr_raw = re.sub(r'([가-힣]+길\s+\d+[-\d]*)\s+[가-힣]+.*$', r'\1', addr_raw)
    # 도로명로+숫자 이후 모든 한글 제거 (길이 없는 경우)
    if '길' not in addr_raw:
        addr_raw = re.sub(r'([가-힣]+로\s+\d+[-\d]*)\s+[가-힣]+.*$', r'\1', addr_raw)
    
    # 숫자-숫자 패턴 이후 모든 것 제거 (단, 지번주소는 보존)
    # 예: "385-16 삼성주택" → "385-16"
    # 도로명이 아닌 경우에만 적용 (지번주소 보존)
    if not re.search(r'[가-힣]+로\s+\d+[-\d]*', addr_raw) and not re.search(r'[가-힣]+길\s+\d+[-\d]*', addr_raw):
        addr_raw = re.sub(r'(\d+-\d+)\s+[가-힣A-Z].*$', r'\1', addr_raw)
    
    # 6. 도로명+건물번호 분리 (일반화된 패턴) - 상세 번지 보존
    # 6-1. *로*길+숫자 -> *로*길 숫자 (예: 북악산로3길44 -> 북악산로3길 44)
    # 더 정확한 패턴으로 수정: ~로로 끝나고 ~길로 끝나는 패턴 (상세 번지 보존)
    # 주의: 이미 공백이 있는 경우는 제외
    addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*길)(\d+[-\d]*)', r'\1 \2', addr_raw)
    
    # 6-2. *로+숫자 -> *로 숫자 (길이 없는 경우만) - 상세 번지 보존
    # 단, ~길이 포함된 경우는 제외 (연희로18길 -> 연희로18길 유지)
    # 상세 번지(예: 112-3, 581, 685-20) 보존
    # 주의: 이미 공백이 있는 경우는 제외
    if '길' not in addr_raw:
        addr_raw = re.sub(r'([가-힣]+로)(\d+[-\d]*)', r'\1 \2', addr_raw)
    
    # 7. 도로명주소 정리 - 건물명만 제거하고 상세 번지는 보존
    # 예: "서울 서대문구 연희로18길 36 애스트리23" -> "서울 서대문구 연희로18길 36"
    # 주의: "다길", "나길" 등은 실제 도로명이므로 건물번호를 제거하면 안됨
    # ~길숫자(-숫자) 패턴 뒤의 건물명만 제거 (상세 번지는 보존)
    if not re.search(r'[다나]길', addr_raw):
        # 건물명 패턴만 제거 (상세 번지 정보는 보존)
        addr_raw = re.sub(r'([가-힣]+길\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오|생활|관리|키즈).*$', r'\1', addr_raw)
    # ~길 숫자(-숫자) 패턴 뒤의 건물명만 제거
    if not re.search(r'[다나]길', addr_raw):
        addr_raw = re.sub(r'([가-힣]+길\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오|생활|관리|키즈).*$', r'\1', addr_raw)
    # ~로 숫자(-숫자) 패턴 뒤의 건물명만 제거 (길이 없는 경우)
    addr_raw = re.sub(r'([가-힣]+로\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오|생활|관리|키즈).*$', r'\1', addr_raw)
    
    # 8. ~로 주소에서 ~로 제거 (길이 없는 경우)
    # 예: "서울특별시 마포구 와우산로 상수동 321-6" -> "서울특별시 마포구 상수동 321-6"
    # ~길이 없는 주소에서만 ~로 제거
    if '길' not in addr_raw and '로' in addr_raw:
        addr_raw = re.sub(r'([가-힣]+구)\s+([가-힣]+로)\s+([가-힣]+동)', r'\1 \3', addr_raw)
    
    # 9. 지번 주소 뒤 추가 정보 제거 (증산동 202-25 등)
    # 예: "증산로9길 26-21 증산동 202-25" -> "증산로9길 26-21"
    addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*길\s+\d+[-\d]*)\s+[가-힣]+동\s+\d+[-\d]*.*$', r'\1', addr_raw)
    # 추가 지번 주소 제거 (서울시 금천구 독산동 964-42 등)
    addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*길\s+\d+[-\d]*)\s+서울[시특별시]*\s+[가-힣]+구\s+[가-힣]+동\s+\d+[-\d]*.*$', r'\1', addr_raw)
    
    # 10. 마침표 및 불필요한 문자 제거
    addr_raw = re.sub(r'\.+$', '', addr_raw)  # 끝의 마침표 제거
    addr_raw = re.sub(r'\s+$', '', addr_raw)  # 끝의 공백 제거
    
    # 12. 아파트/건물 내부 정보 제거 (infra 실패 케이스 대응)
    # 동/호수 정보 제거 (예: 101동 102호, 13동 204호)
    addr_raw = re.sub(r'\s+\d+동\s+\d+호.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+\d+동\s+\d+,\s*\d+호.*$', '', addr_raw)
    # 층수 정보 제거 (예: 4층, 3층, 1층)
    addr_raw = re.sub(r'\s+\d+층.*$', '', addr_raw)
    # 단지/아파트 내부 정보 제거
    addr_raw = re.sub(r'\s+단지\s*내.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+관리동.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+관리실.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+키즈센터\d+층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+키즈클럽.*$', '', addr_raw)
    # 상세 위치 정보 제거 (예: B113호, 101-2호, 206-2호)
    addr_raw = re.sub(r'\s+[A-Z]\d+호.*$', '', addr_raw)  # B113호, A101호 등
    addr_raw = re.sub(r'\s+\d+-\d+호.*$', '', addr_raw)  # 101-2호, 206-2호 등
    addr_raw = re.sub(r'\s+\d+,\d+호.*$', '', addr_raw)  # 105,106호 등
    # 지하/지상 정보 제거
    addr_raw = re.sub(r'\s+지하\d+.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+지상\s*\d+.*$', '', addr_raw)
    # B1층, B2층 등 제거
    addr_raw = re.sub(r'\s+B\d+층.*$', '', addr_raw)
    # 상가/빌딩 내부 정보 제거
    addr_raw = re.sub(r'\s+상가동.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+빌딩.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+타워.*$', '', addr_raw)
    # 주민공동시설, 종합상가 등 제거
    addr_raw = re.sub(r'\s+주민공동시설.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+종합상가.*$', '', addr_raw)
    # 센터/관련 정보 제거
    addr_raw = re.sub(r'\s+고객센터\d+층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+근로복지관\d+층.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+교육관.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+문화건강센터.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+열린문화센터.*$', '', addr_raw)
    
    # 13. 복잡한 건물명 패턴 제거 (infra 특화)
    # 아파트 단지명 제거
    addr_raw = re.sub(r'\s+[가-힣]+아파트.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+타운.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+시티.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+파크.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+힐스.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+위브.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+자이.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+푸르지오.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+프레스티지.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+타운.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+타워.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+브이원.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+에코.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+리버.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+더프레티움.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+스위첸.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+리첸시아.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+플레이스.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+센트럴.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+그라시움.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+아이파크.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+아카데미.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+브이원.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+엔지니어링.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+메디컬.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+홈캐스트.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+스위트.*$', '', addr_raw)
    
    # 14. 괄호 안의 상세 정보 제거 (예: (망우본동), (정릉동))
    addr_raw = re.sub(r'\s*\([^)]*동[^)]*\)\s*', ' ', addr_raw)
    addr_raw = re.sub(r'\s*\([^)]*가[^)]*\)\s*', ' ', addr_raw)
    
    # 15. 대학교명 제거 (괄호 제거 후)
    # 예: "서울 구로구 항동 성공회대학교" → "서울 구로구 항동"
    # 동 뒤에 대학교명이 있는 경우만 제거
    addr_raw = re.sub(r'(.*동)\s+.*(?:대학교|대학|학교).*$', r'\1', addr_raw)
    
    # 16. 공백 정리
    addr_raw = re.sub(r'\s+', ' ', addr_raw).strip()

    # --- 🔥 [추가: 주택 정규화 전용 규칙] ---
    # 1. 쉼표(,) 뒤 상세정보 제거 → "서울 성북구 동소문로 305, 지층" → "서울 성북구 동소문로 305"
    addr_raw = re.sub(r',\s*[^,]+$', '', addr_raw)

    # 2. '지상', '지하', '층', '호' 등 세부위치 제거
    addr_raw = re.sub(r'\s*지[상하]\d*층?', '', addr_raw)
    addr_raw = re.sub(r'\s*\d+층', '', addr_raw)
    addr_raw = re.sub(r'\s*\d+호', '', addr_raw)
    addr_raw = re.sub(r'\s*\d+동', '', addr_raw)

    # 3. 괄호 안에 있는 동/가/건물명 제거
    addr_raw = re.sub(r'\([^)]*(동|가|아파트|빌라|단지|상가|타워)[^)]*\)', '', addr_raw)

    # 4. "앞", "내", "관리동", "관리실" 등 불필요한 단어 제거
    addr_raw = re.sub(r'\s*(앞|내|관리동|관리실|주민센터|키즈센터\d*층?|문화센터).*$', '', addr_raw)

    # 5. 주소 끝 불필요한 문자 제거
    addr_raw = re.sub(r'[-,\s]+$', '', addr_raw)

    # 6. 도로명 + 도로명주소부번까지만 인식하고 그 뒤는 모두 제거 - 건물명만 제거
    # ~길 + 숫자 패턴 (도로명주소부번까지) - 건물명만 제거, 상세 번지는 보존
    addr_raw = re.sub(r'([가-힣]+길\d*[가-힣]*\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오|생활|관리|키즈).*$', r'\1', addr_raw)
    # ~로 + 숫자 패턴 (도로명주소부번까지) - 길이 없는 경우만, 건물명만 제거
    if '길' not in addr_raw:
        addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오|생활|관리|키즈).*$', r'\1', addr_raw)
    
    # 6-1. 특수 케이스: 도로명이 너무 구체적인 경우 더 간단하게
    # 주의: "8길", "9길" 등은 실제 도로명이므로 제거하면 안됨
    # 광평로34길 -> 광평로로 단순화 (단, 일반적인 숫자길은 제외)
    # addr_raw = re.sub(r'([가-힣]+로)\d+길', r'\1', addr_raw)  # 주석 처리
    # 도로명 + 숫자 뒤의 건물명만 제거 (길이 없는 경우만) - 상세 번지는 보존
    if '길' not in addr_raw:
        addr_raw = re.sub(r'([가-힣]+로\s+\d+[-\d]*)\s+[가-힣A-Z]+(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오|생활|관리|키즈).*$', r'\1', addr_raw)
    
    # 7. 어린이집/유치원 등 시설명 제거 (더 구체적인 패턴)
    # ~길/로 + 숫자 + 시설명 패턴
    addr_raw = re.sub(r'([가-힣]+길\d*[가-힣]*\s+\d+)\s+[가-힣]*(어린이집|유치원|학교|병원|약국|마트|편의점|공원|체육관|문화센터|주민센터|센터|관리동|관리실|키즈센터|키즈클럽).*$', r'\1', addr_raw)
    addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*\s+\d+)\s+[가-힣]*(어린이집|유치원|학교|병원|약국|마트|편의점|공원|체육관|문화센터|주민센터|센터|관리동|관리실|키즈센터|키즈클럽).*$', r'\1', addr_raw)
    
    # 일반적인 시설명 제거 (길/로 패턴이 없는 경우)
    addr_raw = re.sub(r'\s+[가-힣]*(어린이집|유치원|학교|병원|약국|마트|편의점|공원|체육관|문화센터|주민센터|센터|관리동|관리실|키즈센터|키즈클럽).*$', '', addr_raw)
    
    # 7. 공백 정리
    addr_raw = re.sub(r'\s+', ' ', addr_raw).strip()

    # 8. 추가 주소정규화 규칙 (산 표기, 동/호수, 단지명 제거 등)
    # 8-1. '산' 뒤 숫자 공백 삽입 (예: 산19 -> 산 19)
    addr_raw = re.sub(r"(산)(\d+)", r"\1 \2", addr_raw)

    # 8-2. 세부 동·호수 제거 (예: 106-101, 101-102)
    # 주의: 건물번호는 제거하면 안됨 (예: 22-5는 건물번호)
    # 큰 번호의 세부 동·호수만 제거 (예: 106-101, 101-102)
    addr_raw = re.sub(r"\d{3,}-\d+$", "", addr_raw)

    # 8-3. 층/호/상세 위치 제거
    addr_raw = re.sub(r"\d+층", "", addr_raw)      # 3층, 2층
    addr_raw = re.sub(r"\d+호", "", addr_raw)      # 101호, 201호
    addr_raw = re.sub(r"B\d+", "", addr_raw)       # B113호 같은 패턴
    addr_raw = re.sub(r"(상가|본관|관리동).*", "", addr_raw)  # 관리동, 상가 2층 등

    # 8-4. 단지명/아파트명 제거 (공통 아파트 브랜드명)
    apt_keywords = [
        "자이", "푸르지오", "힐스테이트", "래미안",
        "아이파크", "리첸시아", "롯데캐슬", "e편한세상",
        "센트레빌", "위브", "더샵", "SK뷰", "엠벨리"
    ]
    for kw in apt_keywords:
        addr_raw = re.sub(rf"\s*{kw}\S*", "", addr_raw)

    # 8-5. 괄호/쉼표 안의 부가설명 제거
    addr_raw = re.sub(r"\(.*?\)", "", addr_raw)
    addr_raw = re.sub(r",.*", "", addr_raw)

    # 8-6. 건물명/시설명 제거 (E3, A동, B동 등)
    addr_raw = re.sub(r"\s+[A-Z]\d*$", "", addr_raw)  # E3, A1, B2 등
    addr_raw = re.sub(r"\s+[가-힣]*동$", "", addr_raw)  # A동, B동 등
    
    # 8-7. 불필요한 공백 정리
    addr_raw = re.sub(r"\s+", " ", addr_raw).strip()

    # ✅ 최종 정리 (상세 번지 정보 보존)
    # -------------------
    # 1. 괄호 제거 (건물명이 포함된 괄호만)
    addr = re.sub(r'\([^)]*(?:빌|타워|센터|마트|몰|아파트|오피스|자이|파크|힐스|위브|푸르지오)[^)]*\)', '', addr_raw)

    # 2. 쉼표 뒤 상세정보 제거 (층수, 호수 정보만)
    addr = re.sub(r',\s*(?:층|호|동|지하|지상).*$', '', addr)

    # 3. "층", "호", "동" 같은 세부 위치 제거 (상세 번지는 보존)
    # 주의: 건물번호는 제거하지 않음 (예: 112-3, 581, 21-31 등)
    addr = re.sub(r'\s*\d+층.*$', '', addr)
    addr = re.sub(r'\s*\d+호.*$', '', addr)
    addr = re.sub(r'\s*\d+동.*$', '', addr)
    addr = re.sub(r'\s*지하\d*층?', '', addr)
    addr = re.sub(r'\s*지상\d*층?', '', addr)

    # 4. 공백 정리
    addr = re.sub(r'\s+', ' ', addr).strip()

    # 5. 새로운 전처리 규칙들 추가
    
    # 5-1. '*로n가' 패턴에서 띄어쓰기 제거 (동이름이므로 띄어쓰면 안됨)
    # 예: "을지로 6가" -> "을지로6가"
    addr = re.sub(r'([가-힣]+로)\s+(\d+가)', r'\1\2', addr)
    
    # 5-2. 지번주소에서 지번-부지번 뒤의 모든 한글 제거
    # 예: "성수동1가 685-20 서울숲 관리사무소" -> "성수동1가 685-20"
    # 예: "가양동 56-2번지 강서오토플랙스 자동차매매센터 102호" -> "가양동 56-2"
    # 예: "하왕십리동 998번지 왕십리KCC스위첸" -> "하왕십리동 998"
    # 예: "북아현동 136-21번지 이편한세상신촌 119호" -> "북아현동 136-21"
    # 예: "신사동 162-16번지 .17" -> "신사동 162-16"
    
    # 지번-부지번 패턴 뒤의 모든 한글 제거 (번지 포함)
    # 주의: 부지번이 있는 경우는 제외 (예: 성수동1가 685-20)
    # 이 패턴은 새로운 규칙에서 처리하므로 주석 처리
    # addr = re.sub(r'([가-힣]+동\s+\d+[-\d]*)\s*번지.*$', r'\1', addr)
    
    # 지번-부지번 패턴 뒤의 모든 한글 제거 (번지 없이, 2글자 이상의 한글만)
    # 주의: 부지번이 있는 경우는 제외 (예: 성수동1가 685-20)
    # 이 패턴은 새로운 규칙에서 처리하므로 주석 처리
    # addr = re.sub(r'([가-힣]+동\s+\d+[-\d]*)\s+[가-힣]{2,}.*$', r'\1', addr)
    
    # 5-3. 동이름 뒤의 숫자(지번)는 보존하고 그 뒤의 한글만 제거
    # 예: "한강로1가 64 대우 월드마크 용산" -> "한강로1가 64"
    # 예: "한강로3가 40-999 용산역" -> "한강로3가 40-999"
    # 한글+로+숫자+가 패턴에서 지번 뒤의 한글 제거
    # 주의: 부지번이 있는 경우는 제외 (예: 한강로2가 112-3)
    # 이 패턴은 새로운 규칙에서 처리하므로 주석 처리
    # addr = re.sub(r'([가-힣]+로\d+가\s+\d+[-\d]*)\s+[가-힣]{2,}.*$', r'\1', addr)
    
    # 5-4. 마침표와 점 제거
    # 예: "신사동 162-16번지 .17" -> "신사동 162-16"
    addr = re.sub(r'\.\d+.*$', '', addr)
    addr = re.sub(r'\s*\.\s*.*$', '', addr)
    
    # 5-5. 최종 공백 정리
    addr = re.sub(r'\s+', ' ', addr).strip()

    return addr

class InfraNormalizer:
    """인프라 데이터 정규화 클래스"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.normalized_facilities: List[Dict] = []
        self.normalized_subway_stations: List[Dict] = []
        self.normalized_bus_stops: List[Dict] = []  # 버스정류소 데이터
        self.failed_addresses: List[Dict] = []  # 실패한 주소 정규화 데이터
        self.failed_output_dir: Optional[Path] = None  # 실패 데이터 저장 경로
        self.output_dir: Optional[Path] = None  # 출력 디렉토리
        self.realtime_mode: bool = False  # 실시간 저장 모드
        
        # API 클라이언트 초기화
        coordinate_api_key = os.getenv("TOLOLA_API_KEY")
        
        if not coordinate_api_key:
            raise ValueError("TOLOLA_API_KEY 환경변수가 설정되지 않았습니다.")
            
        self.coordinate_api = CoordinateAPI(coordinate_api_key)

        
        # facility_id 생성용 카테고리별 접두사 매핑
        self.facility_id_prefix_map = {
            'childSchool': 'chsch',    # 유치원
            'childCare': 'child',     # 어린이집
            'school': 'sch',            # 초중고
            'college': 'col',           # 대학
            'pharmacy': 'pha',          # 약국
            'hospital': 'hos',          # 병원
            'mart': 'mt',               # 마트
            'convenience': 'con',       # 편의점
            'gym': 'gym',               # 공공체육시설
            'park': 'park',             # 공원
            'subway': 'sub',            # 지하철역
            'busstop': 'bus',           # 버스정류소
            'bus': 'bus'                # 버스정류소 (새로운 형식)
        }
        
        # 카테고리별 카운터 (facility_id 생성용)
        self.facility_counters = {prefix: 0 for prefix in self.facility_id_prefix_map.values()}
        
        # JUSO API 대신 좌표 API 사용
        
        # 필요한 카테고리 확인 및 추가
        self._ensure_categories_exist()

    def _ensure_categories_exist(self):
        """필요한 카테고리가 DB에 존재하는지 확인하고 없으면 추가"""
        try:
            from backend.db.db_utils_pg import get_engine
            from sqlalchemy import text
            
            engine = get_engine()
            with engine.connect() as conn:
                # ID 11 (childSchool - 유치원) 확인
                result = conn.execute(text("""
                    SELECT id FROM infra.facility_categories 
                    WHERE id = 11 AND code = 'childSchool'
                """)).fetchone()
                
                if not result:
                    # ID 11 유치원 카테고리 추가
                    conn.execute(text("""
                        INSERT INTO infra.facility_categories (id, code, name, description, created_at) 
                        VALUES (11, 'childSchool', '유치원', '교육시설', NOW())
                    """))
                    conn.commit()
                    logger.info("✅ 유치원 카테고리(ID: 11) 추가 완료")
                else:
                    logger.info("✅ 유치원 카테고리(ID: 11) 이미 존재")
                    
        except Exception as e:
            logger.warning(f"⚠️ 카테고리 확인/추가 중 오류: {e}")

    def _get_category_id(self, code: str) -> Optional[int]:
        """시설 카테고리 코드를 기반으로 ID를 조회"""
        return self.category_map.get(code)
    
    def _generate_facility_id(self, facility_type: str) -> str:
        """시설 타입에 따라 고유한 facility_id 생성"""
        prefix = self.facility_id_prefix_map.get(facility_type, 'unk')
        
        # 카운터 증가
        self.facility_counters[prefix] += 1
        
        # 4자리 숫자로 포맷팅 (예: child0001, sch0001)
        return f"{prefix}{self.facility_counters[prefix]:04d}"
    
    def _get_facility_cd(self, facility_type: str) -> str:
        """시설 타입에 따라 cd (접두사) 반환"""
        return self.facility_id_prefix_map.get(facility_type, 'unk')

    def _generate_transport_id(self, transport_type: str) -> str:
        """교통 시설 ID 생성 (sub000001, bus000001 형태)"""
        if transport_type == 'subway':
            prefix = 'sub'
            digits = 6  # 지하철은 6자리 (최대 999,999개)
        elif transport_type == 'bus':
            prefix = 'bus'
            digits = 6  # 버스는 6자리 (최대 999,999개)
        else:
            prefix = 'trp'
            digits = 6  # 기타 교통시설도 6자리
        
        # 카운터 증가
        self.facility_counters[prefix] += 1
        
        # 6자리 숫자로 포맷팅 (예: sub000001, bus000001)
        return f"{prefix}{self.facility_counters[prefix]:0{digits}d}"

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


    def _save_failed_data_immediately(self, failed_data: Dict, output_dir: Path):
        """실패 데이터를 즉시 파일에 추가 저장 (중복 방지)"""
        failed_file = output_dir / "failed_addresses.jsonl"
        
        # 중복 체크를 위한 키 생성 (facility_name + address_raw + facility_type)
        check_key = f"{failed_data.get('facility_name', '')}_{failed_data.get('address_raw', '')}_{failed_data.get('facility_type', '')}"
        
        # 이미 저장된 실패 데이터인지 확인
        if hasattr(self, '_saved_failed_keys'):
            if check_key in self._saved_failed_keys:
                return  # 이미 저장된 데이터이므로 건너뛰기
        else:
            self._saved_failed_keys = set()
        
        # 실패 데이터 저장 (중복 제거를 위해 addresses_tried 필드 정리)
        clean_failed_data = failed_data.copy()
        if 'addresses_tried' in clean_failed_data:
            # 중복 제거
            clean_failed_data['addresses_tried'] = list(set(clean_failed_data['addresses_tried']))
        
        with open(failed_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(clean_failed_data, ensure_ascii=False) + '\n')
        
        # 저장된 키 기록
        self._saved_failed_keys.add(check_key)

    def _save_success_data_immediately(self, facility_data: Dict, output_dir: Path, facility_type: str):
        """성공 데이터를 즉시 파일에 추가 저장 (메모리 절약)"""
        # 시설 타입별 파일 분리
        if facility_type in ['subway', 'busstop', 'bus']:  # 교통 시설 통합
            success_file = output_dir / "transport_points.jsonl"
        else:
            # 데이터셋별 개별 파일 생성 (public_facilities_{prefix}.jsonl)
            prefix = self.facility_id_prefix_map.get(facility_type, 'unk')
            success_file = output_dir / f"public_facilities_{prefix}.jsonl"
        
        with open(success_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(facility_data, ensure_ascii=False) + '\n')

    def _save_progress_immediately(self, progress_data: Dict, output_dir: Path):
        """진행 상황을 즉시 파일에 저장"""
        progress_file = output_dir / "progress.jsonl"
        
        with open(progress_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(progress_data, ensure_ascii=False) + '\n')

    def _initialize_realtime_files(self, output_dir: Path):
        """실시간 모드용 JSONL 파일들 초기화 (기존 파일 유지)"""
        files_to_init = [
            "transport_points.jsonl",  # 교통 데이터 통합 파일
            "failed_addresses.jsonl",
            "progress.jsonl"
        ]
        
        # 기존 파일들 초기화
        for filename in files_to_init:
            file_path = output_dir / filename
            # 기존 파일이 없으면만 생성 (기존 파일 유지)
            if not file_path.exists():
                file_path.touch()  # 빈 파일 생성
        
        # 데이터셋별 개별 파일들 초기화
        for facility_type, prefix in self.facility_id_prefix_map.items():
            if facility_type not in ['subway', 'busstop', 'bus']:  # 지하철과 버스정류소는 제외
                filename = f"public_facilities_{prefix}.jsonl"
                file_path = output_dir / filename
                if not file_path.exists():
                    file_path.touch()  # 빈 파일 생성

    def get_last_progress(self, output_dir: Path) -> Optional[Dict]:
        """마지막 진행 상황 조회"""
        progress_file = output_dir / "progress.jsonl"
        
        if not progress_file.exists():
            return None
        
        last_progress = None
        with open(progress_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    last_progress = json.loads(line.strip())
        
        return last_progress

    def get_dataset_last_progress(self, output_dir: Path, facility_type: str) -> Optional[Dict]:
        """특정 데이터셋의 마지막 진행 상황 조회"""
        progress_file = output_dir / "progress.jsonl"
        
        if not progress_file.exists():
            return None
        
        last_progress = None
        with open(progress_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    progress_data = json.loads(line.strip())
                    if progress_data.get('facility_type') == facility_type:
                        last_progress = progress_data
        
        return last_progress

    def get_resume_point(self, output_dir: Path, facility_type: str) -> int:
        """중단된 지점부터 재개할 라인 번호 반환 (자동 감지)"""
        progress_file = output_dir / "progress.jsonl"
        
        if not progress_file.exists():
            return 0  # 처음부터 시작
        
        # 해당 facility_type의 모든 progress 항목을 수집
        progress_entries = []
        with open(progress_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    progress_data = json.loads(line.strip())
                    if progress_data.get('facility_type') == facility_type:
                        progress_entries.append(progress_data)
        
        if not progress_entries:
            return 0  # 처음부터 시작
        
        # 가장 큰 row_index를 찾아서 +1 반환
        max_row_index = max(entry.get('row_index', 0) for entry in progress_entries)
        resume_point = max_row_index + 1
        
        logger.info(f"📊 {facility_type} 재개 지점 자동 감지: {resume_point}행 (마지막 처리: {max_row_index}행)")
        
        return resume_point

    def find_latest_csv_file(self, directory: Path, pattern: str) -> Optional[Path]:
        """디렉토리에서 패턴에 맞는 가장 최신 CSV 파일 찾기"""
        if not directory.exists():
            return None
        
        # 패턴에 맞는 모든 CSV 파일 찾기
        matching_files = []
        for file_path in directory.glob("*.csv"):
            if pattern in file_path.name:
                matching_files.append(file_path)
        
        if not matching_files:
            return None
        
        # 파일명에서 날짜 추출하여 정렬
        def extract_date(file_path: Path) -> str:
            # 파일명에서 날짜 패턴 추출 (예: 20250928)
            import re
            date_match = re.search(r'(\d{8})', file_path.name)
            return date_match.group(1) if date_match else "00000000"
        
        # 날짜 기준으로 정렬하여 가장 최신 파일 반환
        latest_file = max(matching_files, key=extract_date)
        logger.info(f"📁 최신 파일 자동 감지: {latest_file.name}")
        
        return latest_file

    def resume_from_progress(self, output_dir: Path) -> bool:
        """진행 상황에서 재시작"""
        last_progress = self.get_last_progress(output_dir)
        
        if not last_progress:
            logger.info("재시작할 진행 상황이 없습니다. 처음부터 시작합니다.")
            return False
        
        logger.info(f"마지막 진행 상황 발견:")
        logger.info(f"  - 파일: {last_progress['file']}")
        logger.info(f"  - 행 번호: {last_progress['row_index']}")
        logger.info(f"  - 시설 타입: {last_progress['facility_type']}")
        logger.info(f"  - 처리된 개수: {last_progress['processed_count']}")
        
        return True

    def _load_existing_facility_ids(self, output_dir: Path) -> Dict[str, int]:
        """각 데이터셋별 JSONL 파일에서 마지막 facility_id를 확인하여 카운터 초기화"""
        counters = {prefix: 0 for prefix in self.facility_id_prefix_map.values()}
        
        # 각 데이터셋별 파일 확인
        for facility_type, prefix in self.facility_id_prefix_map.items():
            if facility_type in ['subway', 'busstop', 'bus']:
                # 지하철과 버스정류소는 transport_points.jsonl에서 확인
                file_path = output_dir / "transport_points.jsonl"
            else:
                # 나머지는 public_facilities_{prefix}.jsonl 형식
                file_path = output_dir / f"public_facilities_{prefix}.jsonl"
            
            if file_path.exists():
                try:
                    max_id = 0
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line.strip())
                                facility_id = data.get('facility_id', '')
                                if facility_id and facility_id.startswith(prefix):
                                    # 숫자 부분 추출
                                    number_part = facility_id[len(prefix):]
                                    try:
                                        number = int(number_part)
                                        if number > max_id:
                                            max_id = number
                                    except ValueError:
                                        continue
                    
                    counters[prefix] = max_id
                    if max_id > 0:
                        logger.info(f"📊 {prefix} 카운터 초기화: {max_id} (파일: {file_path.name})")
                    
                except Exception as e:
                    logger.warning(f"⚠️ {file_path.name} 로드 실패: {e}")
            else:
                logger.info(f"📁 {file_path.name} 파일이 없습니다. {prefix} 카운터를 0부터 시작합니다.")
        
        loaded_count = sum(1 for count in counters.values() if count > 0)
        logger.info(f"✅ 기존 facility_id 로드 완료: {loaded_count}개 접두사")
        
        return counters

    def convert_jsonl_to_json(self, output_dir: Path):
        """JSONL 파일들을 JSON 파일로 변환 (최종 결과 생성)"""
        logger.info("JSONL 파일들을 JSON 파일로 변환 중...")
        
        # 1. 모든 public_facilities_{prefix}.jsonl 파일들을 통합하여 public_facilities.json 생성
        all_public_facilities = []
        
        # 데이터셋별 개별 파일들 통합
        for facility_type, prefix in self.facility_id_prefix_map.items():
            if facility_type not in ['subway', 'busstop']:  # 지하철과 버스정류소는 제외
                file_path = output_dir / f"public_facilities_{prefix}.jsonl"
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    data = json.loads(line.strip())
                                    all_public_facilities.append(data)
                        logger.info(f"📁 {file_path.name}: {len([l for l in open(file_path, 'r', encoding='utf-8') if l.strip()])}개 데이터 로드")
                    except Exception as e:
                        logger.warning(f"⚠️ {file_path.name} 로드 실패: {e}")
        
        # 통합된 public_facilities.json 생성 (비활성화)
        if all_public_facilities:
            logger.info(f"public_facilities.json 생성 건너뛰기: {len(all_public_facilities)}개 데이터 (JSONL 파일만 사용)")
        else:
            logger.info("통합할 public_facilities 데이터가 없습니다.")
        
        # 2. subway_stations.jsonl → subway_stations.json (데이터가 있을 때만)
        subway_file = output_dir / "subway_stations.jsonl"
        if subway_file.exists():
            stations = []
            with open(subway_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        stations.append(json.loads(line.strip()))
            
            # 데이터가 있을 때만 JSON 파일 생성
            if stations:
                stations_data = {
                    "subway_stations": stations,
                    "metadata": {
                        "normalized_at": datetime.now().isoformat(),
                        "subway_stations_count": len(stations)
                    }
                }
                
                output_file = output_dir / "subway_stations.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(stations_data, f, ensure_ascii=False, indent=2)
                logger.info(f"subway_stations.json 생성: {len(stations)}개")
            else:
                logger.info("subway_stations.jsonl이 비어있어서 JSON 파일을 생성하지 않습니다.")
        
        # 3. bus_stops.jsonl → bus_stops.json (데이터가 있을 때만)
        bus_stops_file = output_dir / "bus_stops.jsonl"
        if bus_stops_file.exists():
            bus_stops = []
            with open(bus_stops_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        bus_stops.append(json.loads(line.strip()))
            
            # 데이터가 있을 때만 JSON 파일 생성
            if bus_stops:
                bus_stops_data = {
                    "bus_stops": bus_stops,
                    "metadata": {
                        "normalized_at": datetime.now().isoformat(),
                        "bus_stops_count": len(bus_stops)
                    }
                }
                
                output_file = output_dir / "bus_stops.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(bus_stops_data, f, ensure_ascii=False, indent=2)
                logger.info(f"bus_stops.json 생성: {len(bus_stops)}개")
            else:
                logger.info("bus_stops.jsonl이 비어있어서 JSON 파일을 생성하지 않습니다.")
        
        # 4. failed_addresses.jsonl → failed_addresses.json (비활성화)
        # JSONL 파일만 사용하므로 JSON 파일 생성하지 않음
        # failed_file = output_dir / "failed_addresses.jsonl"
        # if failed_file.exists():
        #     failed_addresses = []
        #     with open(failed_file, 'r', encoding='utf-8') as f:
        #         for line in f:
        #             if line.strip():
        #                 failed_addresses.append(json.loads(line.strip()))
        #     
        #     failed_data = {
        #         "failed_addresses": failed_addresses,
        #         "metadata": {
        #             "normalized_at": datetime.now().isoformat(),
        #             "failed_addresses_count": len(failed_addresses)
        #         }
        #     }
        #     
        #     output_file = output_dir / "failed_addresses.json"
        #     with open(output_file, 'w', encoding='utf-8') as f:
        #         json.dump(failed_data, f, ensure_ascii=False, indent=2)
        #     logger.info(f"failed_addresses.json 생성: {len(failed_addresses)}개")
        
        logger.info("JSONL → JSON 변환 완료!")

    def _normalize_address(self, address_raw: str, facility_name: str = "", facility_type: str = "", original_file: str = "", original_row_index: int = -1) -> Dict[str, Any]:
        """주소 정규화 - 좌표 API만 사용"""
        # 실패 데이터 저장 플래그 초기화
        self._already_saved_failed = False
        
        if not address_raw or address_raw.strip() == '':
            return {
                'address_raw': address_raw,
                'address_nm': None,
                'address_id': None,
                'lat': None,
                'lon': None,
                'normalization_success': False
            }
        
        logger.info(f"🏠 주소 정규화 시작")
        logger.info(f"📍 원본 주소: {address_raw}")
        logger.info(f"🏢 시설명: {facility_name}")
        logger.info(f"🏷️ 시설타입: {facility_type}")
        
        # 공원 주소의 경우 미리 체크
        is_park = facility_name and '공원' in facility_name
        
        # 주소 전처리 (시설 타입별 전용 전처리 함수 사용)
        if facility_type == 'subway':
            addr_processed = preprocess_subway_address(address_raw)
            logger.info(f"🚇 지하철 전용 전처리 적용")
        elif is_park:
            addr_processed = preprocess_park_address(address_raw)
            logger.info(f"🌳 공원 전용 전처리 적용")
        else:
            addr_processed = preprocess_address(address_raw)
            logger.info(f"🔧 일반 전처리 적용")
        logger.info(f"✨ 전처리된 주소: {addr_processed}")
        
        # 좌표 API를 통한 주소 정규화 - 여러 버전 시도
        addresses_to_try = []
        
        # 1. 전처리된 주소
        if addr_processed and addr_processed.strip():
            addresses_to_try.append(addr_processed)
        
        # 2. 원본 주소
        if address_raw != addr_processed:
            addresses_to_try.append(address_raw)
        
        # 3. 전처리된 주소에서 번지 정보 제거한 버전 (도로명주소인 경우)
        if addr_processed and detect_address_type(addr_processed) == "road":
            # 도로명 + 번지 패턴에서 번지 제거
            road_without_number = re.sub(r'(\d+[-\d]*)', '', addr_processed)
            road_without_number = re.sub(r'\s+', ' ', road_without_number).strip()
            if road_without_number != addr_processed and road_without_number not in addresses_to_try:
                addresses_to_try.append(road_without_number)
        
        # 4. 원본 주소에서 번지 정보 제거한 버전 (지번주소인 경우)
        if detect_address_type(address_raw) == "jibun":
            jibun_without_number = re.sub(r'(\d+[-\d]*)', '', address_raw)
            jibun_without_number = re.sub(r'\s+', ' ', jibun_without_number).strip()
            if jibun_without_number != address_raw and jibun_without_number not in addresses_to_try:
                addresses_to_try.append(jibun_without_number)
        
        # 여러 버전의 주소로 시도
        result = None
        for i, addr_to_try in enumerate(addresses_to_try):
            address_type = detect_address_type(addr_to_try)
            type_param = "ROAD" if address_type == "road" else "PARCEL"
            
            logger.info(f"🎯 좌표 API 시도 {i+1}/{len(addresses_to_try)}: {addr_to_try} (타입: {type_param})")
            
            # 좌표 API 호출
            result = self.coordinate_api.normalize_address(addr_to_try, type_param)
            
            if result['normalization_success']:
                logger.info(f"✅ 좌표 API 성공: {addr_to_try}")
                break
            else:
                logger.warning(f"❌ 좌표 API 실패: {addr_to_try}")
        
        # 마지막 결과가 None인 경우 빈 결과 생성
        if result is None:
            result = {
                'address_raw': address_raw,
                'address_nm': None,
                'address_id': None,
                'lat': None,
                'lon': None,
                'normalization_success': False
            }
        
        # 성공한 경우
        if result['normalization_success']:
            logger.info(f"✅ 주소 정규화 성공!")
            logger.info(f"📝 address_nm: {result['address_nm']}")
            logger.info(f"✅ address_id: {result['address_id']}")
            logger.info(f"📍 좌표: lat={result['lat']}, lon={result['lon']}")
            
            # 실패 데이터 저장 플래그 초기화
            self._already_saved_failed = False
            
            return result
        else:
            # 모든 API 실패 시 실패 데이터 저장
            failed_data = {
                "facility_type": facility_type,
                "facility_name": facility_name,
                "address_raw": address_raw,
                "address_processed": addr_processed,
                "addresses_tried": addresses_to_try,
                "error_reason": "좌표 변환 실패 (주소API 성공, 좌표API 실패)",
                "timestamp": pd.Timestamp.now().isoformat(),
                "original_file": original_file,
                "original_row_index": original_row_index
            }
            # 즉시 파일에 저장 (메모리 절약)
            if hasattr(self, 'failed_output_dir') and self.failed_output_dir:
                self._save_failed_data_immediately(failed_data, self.failed_output_dir)
            
            logger.warning(f"❌ 주소 정규화 실패: {address_raw}")
            return {
                'address_raw': address_raw,
                'address_nm': None,
                'address_id': None,
                'lat': None,
                'lon': None,
                'normalization_success': False
            }

    # JUSO API 대신 좌표 API만 사용하므로 파싱 함수들은 제거

    def _normalize_childcare_centers(self, file_path: Path, start_row: int = 0):
        """어린이집 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"어린이집 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"어린이집 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"어린이집 데이터 정규화 시작: {len(df)}개")

        for idx, row in df.iterrows():
            address_raw = str(row.get('CRADDR', ''))
            facility_name = str(row.get('CRNAME', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'childcare', str(file_path), idx)
            
            # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
            if not address_info.get('normalization_success', False):
                continue
            
            facility_data = {
                'facility_id': self._generate_facility_id('childCare'),
                'cd': self._get_facility_cd('childCare'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'] or self._safe_float(row.get('LA')),
                'lon': address_info['lon'] or self._safe_float(row.get('LO')),
                'phone': str(row.get('CRTELNO', '')),
                'website': str(row.get('CRHOME', '')),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': self._safe_int(row.get('CRCAPAT')),
                'grade_level': None,
                'facility_extra': {
                    'childcare_type': str(row.get('CRTYPENAME', ''))
                },
                'data_source': 'openseoul'
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'childCare')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": idx,
                    "facility_type": "childCare",
                    "facility_name": facility_name,
                    "processed_count": idx + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_facilities.append(facility_data)
        logger.info(f"어린이집 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_schools(self, file_path: Path, start_row: int = 0):
        """학교 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"학교 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"학교 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"학교 데이터 정규화 시작: {len(df)}개")

        for idx, row in df.iterrows():
            address_raw = str(row.get('ORG_RDNMA', ''))
            facility_name = str(row.get('SCHUL_NM', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'school', str(file_path), idx)
            
            # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
            if not address_info.get('normalization_success', False):
                continue
            
            facility_data = {
                'facility_id': self._generate_facility_id('school'),
                'cd': self._get_facility_cd('school'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'] or self._safe_float(row.get('LAT')),
                'lon': address_info['lon'] or self._safe_float(row.get('LON')),
                'phone': str(row.get('ORG_TELNO', '')),
                'website': str(row.get('HMPG_ADRES', '')),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': str(row.get('SCHUL_CRSE_SC_NM', '')),
                'facility_extra': {
                    'foundation_type': str(row.get('FOND_SC_NM', '')),
                    'special_class_exist': str(row.get('INDST_SPECL_CCCCL_EXST_YN', '')),
                    'high_school_type': str(row.get('HS_GNRL_BUSNS_SC_NM', '')),
                    'special_purpose': str(row.get('SPCLY_PURPS_HS_ORD_NM', ''))
                },
                'data_source': 'openseoul'
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'school')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": idx,
                    "facility_type": "school",
                    "facility_name": facility_name,
                    "processed_count": idx + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_facilities.append(facility_data)
        logger.info(f"학교 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_parks(self, file_path: Path, start_row: int = 0):
        """공원 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"공원 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"공원 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"공원 데이터 정규화 시작: {len(df)}개")

        for idx, row in df.iterrows():
            address_raw = str(row.get('P_ADDR', ''))
            facility_name = str(row.get('P_PARK', ''))
            original_file = str(file_path)
            address_info = self._normalize_address(address_raw, facility_name, 'park', original_file, idx)
            
            # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
            if not address_info.get('normalization_success', False):
                continue
            
            facility_data = {
                'facility_id': self._generate_facility_id('park'),
                'cd': self._get_facility_cd('park'),
                'name': facility_name,
                'address_raw': address_info.get('address_raw', address_raw),
                'address_nm': address_info.get('address_nm'),
                'address_id': address_info.get('address_id'),
                'lat': address_info.get('lat') or self._safe_float(row.get('LATITUDE')),
                'lon': address_info.get('lon') or self._safe_float(row.get('LONGITUDE')),
                'phone': str(row.get('P_ADMINTEL', '')),
                'website': str(row.get('TEMPLATE_URL', '')),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'description': str(row.get('P_LIST_CONTENT', '')),
                    'area': self._safe_float(row.get('AREA')),
                    'open_date': str(row.get('OPEN_DT', '')),
                    'main_equipment': str(row.get('MAIN_EQUIP', '')),
                    'main_plants': str(row.get('MAIN_PLANTS', '')),
                    'guidance': str(row.get('GUIDANCE', '')),
                    'visit_road': str(row.get('VISIT_ROAD', '')),
                    'use_refer': str(row.get('USE_REFER', ''))
                },
                'data_source': 'openseoul'
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'park')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": idx,
                    "facility_type": "park",
                    "facility_name": facility_name,
                    "processed_count": idx + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_facilities.append(facility_data)
        logger.info(f"공원 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_subway_stations(self, file_path: Path):
        """지하철역 데이터 정규화 - subwayStationMaster CSV에서 직접 추출"""
        if not file_path.exists():
            logger.warning(f"지하철역 파일이 존재하지 않습니다: {file_path}")
            return

        # 지하철역 정보 파일 로드
        df_stn = read_csv_with_auto_encoding(file_path, dtype=str)
        logger.info(f"지하철역 데이터 로드: {len(df_stn)}개")

        # 역명별로 노선 정보를 수집하여 환승역 처리
        station_lines_map = {}
        
        # 1단계: 역명별로 노선 정보 수집
        for _, row in df_stn.iterrows():
            station_name = str(row.get("BLDN_NM", "")).strip()
            line_name = str(row.get("ROUTE", "")).strip()
            
            if station_name and line_name:
                if station_name not in station_lines_map:
                    station_lines_map[station_name] = []
                if line_name not in station_lines_map[station_name]:
                    station_lines_map[station_name].append(line_name)

        # 2단계: 역 데이터 생성 (환승역 정보 포함)
        for _, row in df_stn.iterrows():
            station_name = str(row.get("BLDN_NM", "")).strip()
            line_name = str(row.get("ROUTE", "")).strip()
            
            logger.info(f"처리 중: {station_name} - {line_name}")
            
            if not station_name or not line_name:
                logger.warning(f"빈 값 건너뛰기: station_name='{station_name}', line_name='{line_name}'")
                continue

            # 해당 역의 모든 노선 정보 가져오기
            all_lines = station_lines_map.get(station_name, [line_name])
            is_transfer = len(all_lines) > 1

            # 최종 데이터 구성 (DB 스키마에 맞게)
            station_data = {
                "id": self._generate_transport_id('subway'),  # sub001, sub002, ...
                "transport_type": "subway",
                "name": station_name,
                "official_code": str(row.get("BLDN_ID", "")),  # 건물 ID를 공식 코드로 사용
                "line_name": line_name,
                "stop_type": None,  # 지하철은 stop_type 없음
                "is_transfer": is_transfer,  # 환승역 여부
                "lat": self._safe_float(row.get("LAT")),  # 위도
                "lon": self._safe_float(row.get("LOT")),  # 경도 (LOT 컬럼명)
                "extra_info": {
                    "all_lines": all_lines  # 해당 역의 모든 노선 정보
                }
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(station_data, self.output_dir, 'subway')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": 0,
                    "facility_type": "subway",
                    "facility_name": station_name,
                    "processed_count": len(self.normalized_subway_stations) + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_subway_stations.append(station_data)

        logger.info(f"지하철역 데이터 정규화 완료: {len(self.normalized_subway_stations)}개")

    def _normalize_pharmacies(self, file_path: Path, start_row: int = 0):
        """약국 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"약국 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"약국 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"약국 데이터 정규화 시작: {len(df)}개")

        for idx, row in df.iterrows():
            address_raw = str(row.get('DUTYADDR', ''))
            facility_name = str(row.get('DUTYNAME', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'pharmacy', str(file_path), idx)
            
            # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
            if not address_info.get('normalization_success', False):
                continue
            
            facility_data = {
                'facility_id': self._generate_facility_id('pharmacy'),
                'cd': self._get_facility_cd('pharmacy'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'] or self._safe_float(row.get('WGS84LAT')),
                'lon': address_info['lon'] or self._safe_float(row.get('WGS84LON')),
                'phone': str(row.get('DUTYTEL1', '')),
                'website': None,
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'pharmacy_id': str(row.get('HOSID', '')),
                    'district': str(row.get('SIGUN_NM', ''))
                },
                'data_source': 'openseoul'
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'pharmacy')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": idx,
                    "facility_type": "pharmacy",
                    "facility_name": facility_name,
                    "processed_count": idx + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_facilities.append(facility_data)
        logger.info(f"약국 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_kindergartens(self, file_path: Path, start_row: int = 0):
        """유치원 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"유치원 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"유치원 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"유치원 데이터 정규화 시작: {len(df)}개")

        for idx, row in df.iterrows():
            address_raw = str(row.get('ADDR', ''))
            facility_name = str(row.get('KDGT_NM', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'childSchool', str(file_path), idx)
            
            # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
            if not address_info.get('normalization_success', False):
                continue
            
            facility_data = {
                'facility_id': self._generate_facility_id('childSchool'),
                'cd': self._get_facility_cd('childSchool'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': str(row.get('TELNO', '')),
                'website': str(row.get('HMPG', '')),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': self._safe_int(row.get('MIX_TDL_CNT')),
                'grade_level': None,
                'facility_extra': {
                    'foundation_type': str(row.get('FNDN_TYPE', ''))
                },
                'data_source': 'openseoul'
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'childSchool')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": idx,
                    "facility_type": "childSchool",
                    "facility_name": facility_name,
                    "processed_count": idx + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_facilities.append(facility_data)
        logger.info(f"유치원 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_colleges(self, file_path: Path, start_row: int = 0):
        """대학 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"대학 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"대학 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"대학 데이터 정규화 시작: {len(df)}개")

        for idx, row in df.iterrows():
            address_raw = str(row.get('ADD_KOR', ''))
            facility_name = str(row.get('NAME_KOR', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'college', str(file_path), idx)
            
            # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
            if not address_info.get('normalization_success', False):
                continue
            
            facility_data = {
                'facility_id': self._generate_facility_id('college'),
                'cd': self._get_facility_cd('college'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': str(row.get('TEL', '')),
                'website': str(row.get('HP', '')),
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
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'college')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": idx,
                    "facility_type": "college",
                    "facility_name": facility_name,
                    "processed_count": idx + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_facilities.append(facility_data)
        logger.info(f"대학 데이터 정규화 완료: {len(self.normalized_facilities)}개")


    def _normalize_bus_stops(self, file_path: Path):
        """버스정류소 데이터 정규화 - 경도,위도 형식으로 address_raw 저장"""
        if not file_path.exists():
            logger.warning(f"버스정류소 파일이 존재하지 않습니다: {file_path}")
            return

        df = read_csv_with_auto_encoding(file_path)
        logger.info(f"버스정류소 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            # 경도(XCRD), 위도(YCRD)를 '경도,위도' 형식으로 address_raw에 저장
            x_coord = self._safe_float(row.get('XCRD'))
            y_coord = self._safe_float(row.get('YCRD'))
            
            if x_coord is not None and y_coord is not None:
                address_raw = f"{x_coord},{y_coord}"
            else:
                address_raw = ""
            
            # 버스정류소 데이터를 DB 스키마에 맞게 구성
            facility_data = {
                'id': self._generate_transport_id('bus'),  # bus001, bus002, ...
                'transport_type': 'bus',
                'name': str(row.get('STOPS_NM', '')),  # 정류소명
                'official_code': str(row.get('STOPS_NO', '')),  # 정류소 번호를 공식 코드로 사용
                'line_name': None,  # 버스는 노선 정보 없음
                'stop_type': str(row.get('STOPS_TYPE', '')),  # 정류소 유형
                'lat': y_coord,  # 위도
                'lon': x_coord,  # 경도
                'extra_info': {
                    'node_id': str(row.get('NODE_ID', '')),
                    'x_coord': x_coord,
                    'y_coord': y_coord
                }
            }
            
            # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
            if self.realtime_mode and self.output_dir:
                self._save_success_data_immediately(facility_data, self.output_dir, 'bus')
                # 진행 상황 저장
                progress_data = {
                    "file": str(file_path),
                    "row_index": 0,  # 버스정류소는 인덱스가 복잡하므로 0으로 설정
                    "facility_type": "bus",
                    "facility_name": str(row.get('STOPS_NM', '')),
                    "processed_count": len(self.normalized_bus_stops) + 1,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                self._save_progress_immediately(progress_data, self.output_dir)
            else:
                self.normalized_bus_stops.append(facility_data)
        logger.info(f"버스정류소 데이터 정규화 완료: {len(self.normalized_bus_stops)}개")

    def normalize_openseoul_data(self, output_dir: Path = None, realtime_mode: bool = False) -> Dict[str, List[Dict]]:
        """OpenSeoul CSV 파일들을 정규화"""
        # 출력 디렉토리 및 실시간 모드 설정
        if output_dir:
            self.output_dir = output_dir
            self.failed_output_dir = output_dir
            self.realtime_mode = realtime_mode
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 실시간 모드일 때 기존 JSONL 파일들 초기화
            if realtime_mode:
                self._initialize_realtime_files(output_dir)
            
            # 기존 facility_id 로드하여 카운터 초기화
            self.facility_counters = self._load_existing_facility_ids(output_dir)
        else:
            # 출력 디렉토리가 없으면 카운터를 0부터 시작
            self.facility_counters = {prefix: 0 for prefix in self.facility_id_prefix_map.values()}
        
        openseoul_dir = self.data_dir  # backend/data/public-api/openseoul

        # 어린이집 데이터 - 진행 상황 확인 후 재개
        childcare_file = openseoul_dir / "seoul_ChildCareInfo_20250928.csv"
        childcare_start_row = self.get_resume_point(output_dir, 'childCare') if output_dir else 0
        if childcare_start_row > 0:
            logger.info(f"어린이집 데이터 재개: {childcare_start_row}행부터 시작")
        self._normalize_childcare_centers(childcare_file, childcare_start_row)
        
        # 유치원 데이터 - 진행 상황 확인 후 재개
        kindergarten_file = openseoul_dir / "seoul_childSchoolInfo_20250919.csv"
        kindergarten_start_row = self.get_resume_point(output_dir, 'childSchool') if output_dir else 0
        if kindergarten_start_row > 0:
            logger.info(f"유치원 데이터 재개: {kindergarten_start_row}행부터 시작")
        self._normalize_kindergartens(kindergarten_file, kindergarten_start_row)
        
        # 학교 데이터 (초중고) - 진행 상황 확인 후 재개
        school_file = openseoul_dir / "seoul_neisSchoolInfo_20250928.csv"
        school_start_row = self.get_resume_point(output_dir, 'school') if output_dir else 0
        if school_start_row > 0:
            logger.info(f"학교 데이터 재개: {school_start_row}행부터 시작")
        self._normalize_schools(school_file, school_start_row)
        
        # # 대학 데이터 - 진행 상황 확인 후 재개
        college_file = openseoul_dir / "seoul_SebcCollegeInfoKor_20250919.csv"
        college_start_row = self.get_resume_point(output_dir, 'college') if output_dir else 0
        if college_start_row > 0:
            logger.info(f"대학 데이터 재개: {college_start_row}행부터 시작")
        self._normalize_colleges(college_file, college_start_row)
        
        # 공원 데이터 - 진행 상황 확인 후 재개
        park_file = openseoul_dir / "seoul_SearchParkInfoService_20250919.csv"
        park_start_row = self.get_resume_point(output_dir, 'park') if output_dir else 0
        if park_start_row > 0:
            logger.info(f"공원 데이터 재개: {park_start_row}행부터 시작")
        self._normalize_parks(park_file, park_start_row)
        
        # 약국 데이터 - 진행 상황 확인 후 재개
        pharmacy_file = self.find_latest_csv_file(openseoul_dir, "seoul_TbPharmacyOperateInfo")
        if pharmacy_file:
            pharmacy_start_row = self.get_resume_point(output_dir, 'pharmacy') if output_dir else 0
            if pharmacy_start_row > 0:
                logger.info(f"약국 데이터 재개: {pharmacy_start_row}행부터 시작")
            self._normalize_pharmacies(pharmacy_file, pharmacy_start_row)
        else:
            logger.warning("약국 CSV 파일을 찾을 수 없습니다.")

        # 지하철역과 버스정류소는 좌표 기반이므로 제외
        subway_file = openseoul_dir / "seoul_subwayStationMaster_20250928.csv"
        self._normalize_subway_stations(subway_file)
        bus_stop_file = openseoul_dir / "seoul_busStopLocationXyInfo_20250928.csv"
        self._normalize_bus_stops(bus_stop_file)

        # localdata 폴더 데이터 처리
        localdata_dir = self.data_dir.parent / "localdata"
        logger.info(f"localdata 디렉토리: {localdata_dir}")
        logger.info(f"localdata 디렉토리 존재: {localdata_dir.exists()}")
        
        # 공공체육시설 데이터 - 진행 상황 확인 후 재개
        sports_file = localdata_dir / "utf8_서울시 공공체육시설 정보.csv"
        logger.info(f"체육시설 파일: {sports_file}")
        logger.info(f"체육시설 파일 존재: {sports_file.exists()}")
        if sports_file.exists():
            sports_start_row = self.get_resume_point(output_dir, 'gym') if output_dir else 0
            if sports_start_row > 0:
                logger.info(f"공공체육시설 데이터 재개: {sports_start_row}행부터 시작")
            self._normalize_sports_facilities(sports_file, sports_start_row)
        
        # 마트 데이터 - 진행 상황 확인 후 재개
        mart_file = localdata_dir / "utf8_서울시 마트.csv"
        if mart_file.exists():
            mart_start_row = self.get_resume_point(output_dir, 'mt') if output_dir else 0
            if mart_start_row > 0:
                logger.info(f"마트 데이터 재개: {mart_start_row}행부터 시작")
            self._normalize_marts(mart_file, mart_start_row)
        
        # 병원 데이터 - 진행 상황 확인 후 재개
        hospital_file = localdata_dir / "utf8_서울시병원_내과소아과응급의학과.csv"
        if hospital_file.exists():
            hospital_start_row = self.get_resume_point(output_dir, 'hos') if output_dir else 0
            if hospital_start_row > 0:
                logger.info(f"병원 데이터 재개: {hospital_start_row}행부터 시작")
            self._normalize_hospitals(hospital_file, hospital_start_row)
        
        # 편의점 데이터 - 진행 상황 확인 후 재개
        convenience_file = self.find_latest_csv_file(localdata_dir, "utf8_서울시 편의점")
        if convenience_file:
            convenience_start_row = self.get_resume_point(output_dir, 'convenience') if output_dir else 0
            if convenience_start_row > 0:
                logger.info(f"편의점 데이터 재개: {convenience_start_row}행부터 시작")
            self._normalize_convenience_stores(convenience_file, convenience_start_row)
        else:
            logger.warning("편의점 CSV 파일을 찾을 수 없습니다.")

        logger.info(f"총 {len(self.normalized_facilities)}개의 시설 데이터와 {len(self.normalized_subway_stations)}개의 지하철역 데이터 정규화 완료.")
        
        # 카운터 상태 로깅
        logger.info("생성된 facility_id 카운터 상태:")
        for prefix, count in self.facility_counters.items():
            if count > 0:
                logger.info(f"  {prefix}: {count}개")
        
        return {
            "public_facilities": self.normalized_facilities,
            "subway_stations": self.normalized_subway_stations,
            "failed_addresses": self.failed_addresses
        }
    


    def _normalize_sports_facilities(self, file_path: Path, start_row: int = 0):
        """공공체육시설 정보 정규화"""
        logger.info(f"공공체육시설 정보 정규화 시작: {file_path}")
        
        df = read_csv_with_auto_encoding(file_path, dtype=str)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"공공체육시설 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"공공체육시설 데이터 로드: {len(df)}개")
        
        for idx, row in df.iterrows():
            try:
                # 주소 정규화
                original_file = str(file_path)
                address_info = self._normalize_address(
                    address_raw=row.get('시설주소', ''),
                    facility_name=row.get('시설명', ''),
                    facility_type='gym',
                    original_file=original_file,
                    original_row_index=idx
                )
                
                # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
                if not address_info.get('normalization_success', False):
                    continue
                
                # 시설 정보 구성
                facility = {
                    'facility_id': self._generate_facility_id('gym'),
                    'cd': self._get_facility_cd('gym'),
                    'name': row.get('시설명', ''),
                    'address_raw': address_info['address_raw'],
                    'address_nm': address_info['address_nm'],
                    'address_id': address_info['address_id'],
                    'lat': address_info['lat'],
                    'lon': address_info['lon'],
                    'phone': row.get('연락처', ''),
                    'website': row.get('홈페이지', ''),
                    'operating_hours': f"평일: {row.get('운영시간_평일', '')}, 주말: {row.get('운영시간_주말', '')}, 공휴일: {row.get('운영시간_공휴일', '')}",
                    'capacity': self._safe_int(row.get('시설규모', '')),
                    'facility_extra': {
                        '시설유형': row.get('시설유형', ''),
                        '운영기관': row.get('운영기관', ''),
                        '시설대관여부': row.get('시설대관여부', ''),
                        '시설사용료': row.get('시설사용료', ''),
                        '주차정보': row.get('주차정보', ''),
                        '시설종류': row.get('시설종류', ''),
                        '시설운영상태': row.get('시설운영상태', ''),
                        '시설편의시설': row.get('시설편의시설', ''),
                        '비고': row.get('비고', '')
                    },
                    'data_source': 'localdata'
                }
                
                # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
                if self.realtime_mode and self.output_dir:
                    self._save_success_data_immediately(facility, self.output_dir, 'gym')
                    # 진행 상황 저장
                    progress_data = {
                        "file": str(file_path),
                        "row_index": idx,
                        "facility_type": "gym",
                        "facility_name": row.get('시설명', ''),
                        "processed_count": idx + 1,
                        "timestamp": pd.Timestamp.now().isoformat()
                    }
                    self._save_progress_immediately(progress_data, self.output_dir)
                else:
                    self.normalized_facilities.append(facility)
                
            except Exception as e:
                logger.error(f"공공체육시설 정규화 오류: {row.get('시설명', '')} - {e}")
        
        logger.info(f"공공체육시설 정규화 완료: {len(df)}개")

    def _normalize_marts(self, file_path: Path, start_row: int = 0):
        """마트 정보 정규화"""
        logger.info(f"마트 정보 정규화 시작: {file_path}")
        
        df = read_csv_with_auto_encoding(file_path, dtype=str)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"마트 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"마트 데이터 로드: {len(df)}개")
        
        for idx, row in df.iterrows():
            try:
                # 주소 정규화 (도로명전체주소 우선, 없으면 소재지전체주소 사용)
                original_file = str(file_path)
                road_addr = str(row.get('도로명전체주소', '') or '').strip()
                jibun_addr = str(row.get('소재지전체주소', '') or '').strip()
                addr_for_norm = road_addr if road_addr else jibun_addr
                
                address_info = self._normalize_address(
                    address_raw=addr_for_norm,
                    facility_name=row.get('사업장명', ''),
                    facility_type='mart',
                    original_file=original_file,
                    original_row_index=idx
                )
                
                # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
                if not address_info.get('normalization_success', False):
                    continue
                
                # 시설 정보 구성
                facility = {
                    'facility_id': self._generate_facility_id('mart'),
                    'cd': self._get_facility_cd('mart'),
                    'name': row.get('사업장명', ''),
                    'address_raw': address_info['address_raw'],
                    'address_nm': address_info['address_nm'],
                    'address_id': address_info['address_id'],
                    'lat': address_info['lat'],
                    'lon': address_info['lon'],
                    'phone': row.get('소재지전화', ''),
                    'website': None,  # 홈페이지 정보 없음
                    'operating_hours': None,  # 운영시간 정보 없음
                    'is_24h': False,  # 24시간 정보 없음
                    'is_emergency': False,
                    'capacity': None,
                    'grade_level': None,
                    'facility_extra': {
                        '업태구분명': row.get('업태구분명', ''),
                        '점포구분명': row.get('점포구분명', '')
                        
                    },
                    'data_source': 'localdata'
                }
                
                # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
                if self.realtime_mode and self.output_dir:
                    self._save_success_data_immediately(facility, self.output_dir, 'mart')
                    # 진행 상황 저장
                    progress_data = {
                        "file": str(file_path),
                        "row_index": idx,
                        "facility_type": "mart",
                        "facility_name": row.get('사업장명', ''),
                        "processed_count": idx + 1,
                        "timestamp": pd.Timestamp.now().isoformat()
                    }
                    self._save_progress_immediately(progress_data, self.output_dir)
                else:
                    self.normalized_facilities.append(facility)
                
            except Exception as e:
                logger.error(f"마트 정규화 오류: {row.get('사업장명', '')} - {e}")
        
        logger.info(f"마트 정규화 완료: {len(df)}개")

    def _normalize_convenience_stores(self, file_path: Path, start_row: int = 0):
        """편의점 정보 정규화"""
        logger.info(f"편의점 정보 정규화 시작: {file_path}")
        
        df = read_csv_with_auto_encoding(file_path, dtype=str)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"편의점 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"편의점 데이터 로드: {len(df)}개")
        
        for idx, row in df.iterrows():
            try:
                # 주소 정규화 (도로명전체주소 우선, 없으면 소재지전체주소 사용)
                original_file = str(file_path)
                road_addr = str(row.get('도로명전체주소', '') or '').strip()
                jibun_addr = str(row.get('소재지전체주소', '') or '').strip()
                addr_for_norm = road_addr if road_addr else jibun_addr
                
                address_info = self._normalize_address(
                    address_raw=addr_for_norm,
                    facility_name=row.get('사업장명', ''),
                    facility_type='convenience',
                    original_file=original_file,
                    original_row_index=idx
                )
                
                # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
                if not address_info.get('normalization_success', False):
                    continue
                
                # 좌표는 API에서 추출된 값 사용
                lat = address_info['lat']
                lon = address_info['lon']
                
                # 시설 정보 구성
                facility = {
                    'facility_id': self._generate_facility_id('convenience'),
                    'cd': self._get_facility_cd('convenience'),
                    'name': row.get('사업장명', ''),
                    'address_raw': address_info['address_raw'],
                    'address_nm': address_info['address_nm'],
                    'address_id': address_info['address_id'],
                    'lat': lat,
                    'lon': lon,
                    'phone': row.get('소재지전화', ''),
                    'website': row.get('홈페이지', ''),
                    'operating_hours': None,  # 운영시간 정보 없음
                    'is_24h': False,  # 24시간 정보 없음
                    'is_emergency': False,
                    'capacity': None,
                    'grade_level': None,
                    'facility_extra': {
                        '소재지면적': row.get('소재지면적', ''),
                        '도로명전체주소': row.get('도로명전체주소', '')
                    },
                    'data_source': 'localdata'
                }
                
                # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
                if self.realtime_mode and self.output_dir:
                    self._save_success_data_immediately(facility, self.output_dir, 'convenience')
                    # 진행 상황 저장
                    progress_data = {
                        "file": str(file_path),
                        "row_index": idx,
                        "facility_type": "convenience",
                        "facility_name": row.get('사업장명', ''),
                        "processed_count": idx + 1,
                        "timestamp": pd.Timestamp.now().isoformat()
                    }
                    self._save_progress_immediately(progress_data, self.output_dir)
                else:
                    self.normalized_facilities.append(facility)
                
            except Exception as e:
                logger.error(f"편의점 정규화 오류: {row.get('사업장명', '')} - {e}")
        
        logger.info(f"편의점 정규화 완료: {len(df)}개")

    def _normalize_hospitals(self, file_path: Path, start_row: int = 0):
        """병원 정보 정규화"""
        logger.info(f"병원 정보 정규화 시작: {file_path}")
        
        df = read_csv_with_auto_encoding(file_path, dtype=str)
        
        # 시작 행 설정
        if start_row > 0:
            logger.info(f"병원 데이터 정규화 재개: {start_row}행부터 시작, 총 {len(df)}개 중 {len(df) - start_row}개 남음")
            df = df.iloc[start_row:]
        else:
            logger.info(f"병원 데이터 로드: {len(df)}개")
        
        for idx, row in df.iterrows():
            try:
                # 주소 정규화
                original_file = str(file_path)
                # 도로명주소 우선, 없으면 소재지전체주소 사용
                road_addr = str(row.get('도로명전체주소', '') or '').strip()
                jibun_addr = str(row.get('소재지전체주소', '') or '').strip()
                addr_for_norm = road_addr if road_addr else jibun_addr
                address_info = self._normalize_address(
                    address_raw=addr_for_norm,
                    facility_name=row.get('사업장명', ''),
                    facility_type='hospital',
                    original_file=original_file,
                    original_row_index=idx
                )
                
                # 주소 정규화 실패 시 건너뛰기 (이미 failed_addresses.jsonl에 저장됨)
                if not address_info.get('normalization_success', False):
                    continue
                
                # 시설 정보 구성
                facility = {
                    'facility_id': self._generate_facility_id('hospital'),
                    'cd': self._get_facility_cd('hospital'),
                    'name': row.get('사업장명', ''),
                    'address_raw': address_info['address_raw'],
                    'address_nm': address_info['address_nm'],
                    'address_id': address_info['address_id'],
                    'lat': address_info['lat'],
                    'lon': address_info['lon'],
                    'phone': row.get('소재지전화', ''),
                    'website': row.get('홈페이지', ''),
                    'operating_hours': None,  # 운영시간 정보 없음
                    'is_24h': False,  # 24시간 정보 없음
                    'is_emergency': '응급' in str(row.get('진료과목내용명', '')),
                    'facility_extra': {
                        '진료과목': row.get('진료과목내용명', ''),
                        '의료기관종별': row.get('의료기관종별명', ''),
                        '병상수': row.get('병상수', ''),
                        '의료인수': row.get('의료인수', '')
                    },
                    'data_source': 'localdata'
                }
                
                # 실시간 모드일 때 즉시 저장, 아니면 메모리에 누적
                if self.realtime_mode and self.output_dir:
                    self._save_success_data_immediately(facility, self.output_dir, 'hospital')
                    # 진행 상황 저장
                    progress_data = {
                        "file": str(file_path),
                        "row_index": idx,
                        "facility_type": "hospital",
                        "facility_name": row.get('사업장명', ''),
                        "processed_count": idx + 1,
                        "timestamp": pd.Timestamp.now().isoformat()
                    }
                    self._save_progress_immediately(progress_data, self.output_dir)
                else:
                    self.normalized_facilities.append(facility)
                
            except Exception as e:
                logger.error(f"병원 정규화 오류: {row.get('사업장명', '')} - {e}")
        
        logger.info(f"병원 정규화 완료: {len(df)}개")

# 예시 사용법 (CLI에서 호출될 때)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 프로젝트 루트에서 실행한다고 가정
    project_root = Path(__file__).resolve().parents[5]
    openseoul_data_path = project_root / "backend" / "data" / "raw" / "api"
    
    normalizer = InfraNormalizer(data_dir=openseoul_data_path)
    output_dir = project_root / "backend" / "data" / "normalized" / "infra"
    
    # 실시간 모드로 실행 (기존 데이터 유지하면서 누적)
    normalized_data = normalizer.normalize_openseoul_data(output_dir, realtime_mode=True)
    
    # JSONL 파일들을 JSON 파일로 변환
    normalizer.convert_jsonl_to_json(output_dir)
    
    print("\n--- 정규화된 공공시설 데이터 (일부) ---")
    for i, facility in enumerate(normalized_data["public_facilities"][:5]):
        print(f"{i+1}. {facility['name']} (Category ID: {facility.get('category_id', 'N/A')})")

    print("\n--- 정규화된 지하철역 데이터 (일부) ---")
    for i, station in enumerate(normalized_data["subway_stations"][:5]):
        print(f"{i+1}. {station['station_name']} (Line: {station['line_name']})")
