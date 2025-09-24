#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
인프라 데이터 정규화 모듈
서울 열린데이터광장 API 데이터를 infra 스키마에 맞게 정규화
"""

import pandas as pd
from pathlib import Path
import os
from typing import List, Dict, Optional, Any
import logging
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

from backend.services.data_collection.curated.address_api import normalize_address, AddressNormalizerError

logger = logging.getLogger(__name__)

def preprocess_address(addr_raw: str) -> str:
    """주소 전처리 - JUSO API 매칭률 향상을 위한 정리"""
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
    addr_raw = re.sub(r'\s+\d+,\d+.*층.*$', '', addr_raw)  # 2,3,4,5층 패턴
    addr_raw = re.sub(r'\s+\d+[Ff].*$', '', addr_raw)  # 1F, 2f 패턴
    # 추가 층수 패턴들
    addr_raw = re.sub(r'\s+지상\d+\s*~\s*\d+\s*층.*$', '', addr_raw)  # 지상1층~3층
    addr_raw = re.sub(r'\s+지하\d+\s*~\s*\d+\s*층.*$', '', addr_raw)  # 지하1층~3층
    addr_raw = re.sub(r'\s+지상\d+\s*층.*$', '', addr_raw)  # 지상1층
    addr_raw = re.sub(r'\s+지하\d+\s*층.*$', '', addr_raw)  # 지하1층
    
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
    
    # 5. 지번주소 정리 (~동 숫자-숫자 뒤의 모든 문자 제거)
    # 예: "서울 종로구 동숭동 192-6 1" -> "서울 종로구 동숭동 192-6"
    addr_raw = re.sub(r'([가-힣]+동\s+\d+-\d+)\s+.*$', r'\1', addr_raw)
    
    # 6. 도로명+건물번호 분리 (일반화된 패턴)
    # 6-1. *로*길+숫자 -> *로*길 숫자 (예: 북악산로3길44 -> 북악산로3길 44)
    # 더 정확한 패턴으로 수정: ~로로 끝나고 ~길로 끝나는 패턴
    addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*길)(\d+[-\d]*)', r'\1 \2', addr_raw)
    
    # 6-2. *로+숫자 -> *로 숫자 (길이 없는 경우만)
    # 단, ~길이 포함된 경우는 제외 (연희로18길 -> 연희로18길 유지)
    if '길' not in addr_raw:
        addr_raw = re.sub(r'([가-힣]+로)(\d+[-\d]*)', r'\1 \2', addr_raw)
    
    # 7. 도로명주소 정리 (~길숫자(-숫자) 또는 ~길 숫자(-숫자) 뒤의 모든 문자 제거)
    # 예: "서울 서대문구 연희로18길 36 애스트리23" -> "서울 서대문구 연희로18길 36"
    # ~길숫자(-숫자) 패턴 뒤의 모든 문자 제거
    addr_raw = re.sub(r'([가-힣]+길\d+[-\d]*)\s+.*$', r'\1', addr_raw)
    # ~길 숫자(-숫자) 패턴 뒤의 모든 문자 제거
    addr_raw = re.sub(r'([가-힣]+길\s+\d+[-\d]*)\s+.*$', r'\1', addr_raw)
    # ~로 숫자(-숫자) 패턴 뒤의 모든 문자 제거 (길이 없는 경우)
    addr_raw = re.sub(r'([가-힣]+로\s+\d+[-\d]*)\s+.*$', r'\1', addr_raw)
    
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
    addr_raw = re.sub(r'\s+[가-힣]+뉴타운.*$', '', addr_raw)
    addr_raw = re.sub(r'\s+[가-힣]+뉴타워.*$', '', addr_raw)
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
    
    # 15. 공백 정리
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

    # 6. 도로명 + 도로명주소부번까지만 인식하고 그 뒤는 모두 제거
    # ~길 + 숫자 패턴 (도로명주소부번까지) - 더 정확한 패턴
    addr_raw = re.sub(r'([가-힣]+길\d*[가-힣]*\s+\d+[-\d]*)\s+[가-힣].*$', r'\1', addr_raw)
    # ~로 + 숫자 패턴 (도로명주소부번까지) - 길이 없는 경우만
    if '길' not in addr_raw:
        addr_raw = re.sub(r'([가-힣]+로\d*[가-힣]*\s+\d+[-\d]*)\s+[가-힣].*$', r'\1', addr_raw)
    
    # 6-1. 특수 케이스: 도로명이 너무 구체적인 경우 더 간단하게
    # 광평로34길 -> 광평로로 단순화
    addr_raw = re.sub(r'([가-힣]+로)\d+길', r'\1', addr_raw)
    # 도로명 + 숫자 뒤의 모든 것 제거
    addr_raw = re.sub(r'([가-힣]+로\s+\d+[-\d]*)\s+[가-힣].*$', r'\1', addr_raw)
    
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
    addr_raw = re.sub(r"\d+-\d+$", "", addr_raw)

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

    # ✅ 주택 주소 전용 강제 정규화 (마지막 단계)
    # -------------------
    # 1. 괄호 제거
    addr = re.sub(r'\([^)]*\)', '', addr_raw)

    # 2. 쉼표 뒤 상세정보 제거
    addr = re.sub(r',.*$', '', addr)

    # 3. "층", "호", "동" 같은 세부 위치 제거
    addr = re.sub(r'\s*\d+층.*$', '', addr)
    addr = re.sub(r'\s*\d+호.*$', '', addr)
    addr = re.sub(r'\s*\d+동.*$', '', addr)
    addr = re.sub(r'\s*지하\d*층?', '', addr)
    addr = re.sub(r'\s*지상\d*층?', '', addr)

    # 4. 도로명+번지까지만 남기기
    # 예: "서울특별시 성북구 동소문로 305 지층" -> "서울특별시 성북구 동소문로 305"
    addr = re.sub(r'([가-힣]+로\s*\d+[-\d]*).*$', r'\1', addr)
    addr = re.sub(r'([가-힣]+길\s*\d+[-\d]*).*$', r'\1', addr)

    # 5. 공백 정리
    addr = re.sub(r'\s+', ' ', addr).strip()

    return addr

class InfraNormalizer:
    """인프라 데이터 정규화 클래스"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.normalized_facilities: List[Dict] = []
        self.normalized_subway_stations: List[Dict] = []
        self.failed_addresses: List[Dict] = []  # 실패한 주소 정규화 데이터
        
        # facility_categories 매핑 (DB에서 가져오거나 하드코딩)
        # 실제 운영 환경에서는 DB에서 동적으로 가져오는 것이 좋습니다.
        self.category_map = {
            'hospital': 1,
            'school': 2,           # 초중고 + 대학
            'kindergarten': 3,     # 어린이집 → childcare(ID 3)
            'childSchool': 11,     # 유치원 → childSchool (ID 11)
            'park': 4,
            'mart': 5,
            'convenience': 6,
            'pharmacy': 7,
            'subway': 8,
            'bus': 9,              # 버스정류소
            'gym': 10,             # 공공체육시설
            'college': 2,          # school로 통합
            'bus_stop': 9          # bus로 통합
        }
        
        # 주소 정규화 API 키 로드
        self.juso_api_key = os.getenv("JUSO_API_KEY")
        if not self.juso_api_key:
            logger.warning("JUSO_API_KEY 환경 변수가 설정되지 않았습니다. 주소 정규화 기능이 제한될 수 있습니다.")
        
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

    def _normalize_address(self, address_raw: str, facility_name: str = "", facility_type: str = "") -> Dict[str, Any]:
        """주소 정규화 - housing과 동일한 방식"""
        if not address_raw or address_raw.strip() == '':
            return {
                'address_raw': address_raw,
                'address_norm': None,
                'si_do': None,
                'si_gun_gu': None,
                'si_gun_gu_dong': None,
                'road_full': None,
                'jibun_full': None,
                'lat': None,
                'lon': None,
                'geo_extra': None
            }
        
        logger.info(f"원본 주소: {address_raw}")
        
        # 서울특별시 추출 (모든 주소에 공통 적용)
        si_do = None
        if '서울특별시' in address_raw:
            si_do = '서울특별시'
        elif '서울' in address_raw:
            si_do = '서울특별시'
        
        # 산이 포함된 주소의 경우 직접 파싱
        if '산' in address_raw:
            logger.info(f"산 포함 주소 직접 파싱: {address_raw}")
            result = self._parse_mountain_address(address_raw)
            result['si_do'] = si_do  # 서울특별시 정보 덮어쓰기
            return result
        
        # 공원 주소의 경우 미리 체크
        is_park = facility_name and '공원' in facility_name
        
        # 주소 전처리
        addr_processed = preprocess_address(address_raw)
        logger.info(f"전처리된 주소: {addr_processed}")
        
        # 여러 패턴으로 주소 정규화 시도
        success = False
        result = None  # result 변수 초기화
        dong = None    # dong 변수 초기화
        
        for attempt, addr_to_try in enumerate([addr_processed, address_raw]):
            if attempt > 0:
                logger.info(f"주소 정규화 재시도 ({attempt+1}): {addr_to_try}")
            else:
                logger.info(f"주소 정규화 시도: {addr_to_try}")
            
            try:
                result = normalize_address(addr_to_try)
                
                # 법정동 추출 (JUSO API에서 직접 가져오기)
                dong = result.get('eupmyeon_dong', '')  # JUSO API에서 직접 가져오기
                
                logger.info(f"주소 정규화 성공: {result}")
                success = True
                break
            except AddressNormalizerError as e:
                logger.warning(f"주소 정규화 실패 (시도 {attempt+1}): {addr_to_try} - {e}")
                if attempt == 1:  # 마지막 시도
                    logger.error(f"주소 정규화 최종 실패: {address_raw} - {e}")
                    
                    # 공원인 경우 직접 파싱 시도
                    if is_park:
                        logger.info(f"공원 주소 직접 파싱 시도: {address_raw}")
                        result = self._parse_park_address(address_raw)
                        result['si_do'] = si_do  # 서울특별시 정보 덮어쓰기
                        return result
                    
                    # 실패한 주소 정보 수집
                    failed_data = {
                        "facility_type": facility_type,
                        "facility_name": facility_name,
                        "address_raw": address_raw,
                        "address_processed": addr_processed,
                        "error_reason": str(e),
                        "timestamp": pd.Timestamp.now().isoformat()
                    }
                    self.failed_addresses.append(failed_data)
        
        if success and result:  # result가 존재할 때만
            # 현재 result에서 주소 정보 추출
            road_full = result.get("road_full", "")
            jibun_full = result.get("jibun_full", "")
            
            # 도로명주소가 있으면 지번주소 조회 시도
            if road_full:
                try:
                    jibun_result = normalize_address(road_full, reverse=True)
                    jibun_full = jibun_result.get("jibun_full", jibun_full)
                except:
                    pass  # 기존 jibun_full 유지
            
            # 지번주소가 있으면 도로명주소 조회 시도
            if jibun_full:
                try:
                    road_result = normalize_address(jibun_full)
                    road_full = road_result.get("road_full", road_full)
                except:
                    pass  # 기존 road_full 유지
            
            return {
                'address_raw': address_raw,
                'address_norm': road_full or jibun_full,
                'si_do': si_do or result.get('sido'),  # 서울특별시 우선 적용
                'si_gun_gu': result.get('sigungu'),
                'si_gun_gu_dong': dong,  # JUSO API에서 가져온 동 정보
                'road_full': road_full,  # 새로 추가
                'jibun_full': jibun_full,  # 새로 추가
                'lat': result.get('y'),  # API returns y(lat), x(lon)
                'lon': result.get('x'),
                'geo_extra': result.get('geo_extra')
            }
        else:
            # JUSO API 완전 실패 시 최소한 시도/구만이라도 파싱
            logger.info(f"JUSO API 완전 실패, 최소 파싱 시도: {address_raw}")
            result = self._parse_minimal_address(address_raw)
            result['si_do'] = si_do  # 서울특별시 정보 덮어쓰기
            return result

    def _parse_mountain_address(self, address_raw: str) -> Dict[str, Any]:
        """산이 포함된 주소 직접 파싱"""
        result = self._parse_common_address(address_raw, create_norm=False)
        result['address_norm'] = address_raw  # 산 주소는 원본 그대로 사용
        logger.info(f"산 주소 파싱 결과: si_do={result['si_do']}, si_gun_gu={result['si_gun_gu']}, si_gun_gu_dong={result['si_gun_gu_dong']}")
        return result

    def _parse_park_address(self, address_raw: str) -> Dict[str, Any]:
        """공원 주소 직접 파싱 (JUSO API 실패 시) - 여러 동 모두 추출"""
        result = self._parse_common_address(address_raw, create_norm=False, extract_all_dongs=True)
        result['address_norm'] = address_raw  # 공원 주소는 원본 그대로 사용
        logger.info(f"공원 주소 파싱 결과: si_do={result['si_do']}, si_gun_gu={result['si_gun_gu']}, si_gun_gu_dong={result['si_gun_gu_dong']}, all_dongs={result.get('si_gun_gu_dongs', [])}")
        return result

    def _parse_minimal_address(self, address_raw: str) -> Dict[str, Any]:
        """최소한의 주소 파싱 (JUSO API 완전 실패 시)"""
        result = self._parse_common_address(address_raw, create_norm=False)
        result['address_norm'] = address_raw  # 원본 그대로 사용
        result['si_gun_gu_dong'] = None  # 동 정보는 추출하지 않음
        logger.info(f"최소 파싱 결과: si_do={result['si_do']}, si_gun_gu={result['si_gun_gu']}")
        return result

    def _parse_common_address(self, address_raw: str, create_norm: bool = True, extract_all_dongs: bool = False) -> Dict[str, Any]:
        """공통 주소 파싱 함수 (모든 데이터셋에서 사용) - 서울특별시는 _normalize_address에서 처리"""
        import re
        
        # 구 추출
        si_gun_gu = None
        gu_pattern = r'([가-힣]+구)'
        gu_match = re.search(gu_pattern, address_raw)
        if gu_match:
            si_gun_gu = gu_match.group(1)
        
        # 동/가 추출 (산 번호 등은 제외)
        si_gun_gu_dong = None
        si_gun_gu_dongs = []  # 여러 동 저장용
        
        # ~동으로 끝나는 것만 추출 (산 번호, 건물 번호 등 제외)
        dong_pattern = r'([가-힣]+동+" ")'
        dong_matches = re.findall(dong_pattern, address_raw)
        
        if dong_matches:
            if extract_all_dongs:
                # 모든 동을 리스트로 저장
                si_gun_gu_dongs = dong_matches
                si_gun_gu_dong = dong_matches[0] if dong_matches else None  # 첫 번째 동을 기본값으로
            else:
                # 첫 번째 동만 저장 (기존 방식)
                si_gun_gu_dong = dong_matches[0]
        
        # address_norm 생성 (정규화된 주소)
        address_norm = address_raw
        if create_norm and si_gun_gu and si_gun_gu_dong:
            # "강남구 역삼동" 형태로 정규화 (서울특별시는 _normalize_address에서 추가)
            address_norm = f"{si_gun_gu} {si_gun_gu_dong}"
        elif create_norm and si_gun_gu:
            # "강남구" 형태로 정규화
            address_norm = si_gun_gu
        
        logger.info(f"공통 주소 파싱 결과: si_gun_gu={si_gun_gu}, si_gun_gu_dong={si_gun_gu_dong}, all_dongs={si_gun_gu_dongs if extract_all_dongs else None}")
        
        result = {
            'address_raw': address_raw,
            'address_norm': address_norm,
            'si_do': None,  # _normalize_address에서 처리
            'si_gun_gu': si_gun_gu,
            'si_gun_gu_dong': si_gun_gu_dong,
            'road_full': None,
            'jibun_full': None,
            'lat': None,
            'lon': None,
            'geo_extra': None
        }
        
        # 여러 동이 있는 경우 추가 정보로 저장
        if extract_all_dongs and si_gun_gu_dongs:
            result['si_gun_gu_dongs'] = si_gun_gu_dongs
        
        return result

    def _normalize_childcare_centers(self, file_path: Path):
        """어린이집 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"어린이집 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"어린이집 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            address_raw = str(row.get('CRADDR', ''))
            facility_name = str(row.get('CRNAME', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'childcare')
            
            facility_data = {
                'category_id': self._get_category_id('kindergarten'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_norm': address_info['address_norm'],
                'si_do': address_info['si_do'],
                'si_gun_gu': address_info['si_gun_gu'],
                'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                'road_full': address_info.get('road_full'),
                'jibun_full': address_info.get('jibun_full'),
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
                'data_source': 'openseoul',
                'geo_extra': address_info['geo_extra']
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"어린이집 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_schools(self, file_path: Path):
        """학교 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"학교 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"학교 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            address_raw = str(row.get('ORG_RDNMA', ''))
            facility_name = str(row.get('SCHUL_NM', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'school')
            
            facility_data = {
                'category_id': self._get_category_id('school'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_norm': address_info['address_norm'],
                'si_do': address_info['si_do'],
                'si_gun_gu': address_info['si_gun_gu'],
                'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                'road_full': address_info.get('road_full'),
                'jibun_full': address_info.get('jibun_full'),
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
                'data_source': 'seoul_school',
                'geo_extra': address_info['geo_extra']
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"학교 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_parks(self, file_path: Path):
        """공원 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"공원 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"공원 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            address_raw = str(row.get('P_ADDR', ''))
            facility_name = str(row.get('P_PARK', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'park')
            
            facility_data = {
                'category_id': self._get_category_id('park'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_norm': address_info['address_norm'],
                'si_do': address_info['si_do'],
                'si_gun_gu': address_info['si_gun_gu'],
                'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                'road_full': address_info.get('road_full'),
                'jibun_full': address_info.get('jibun_full'),
                'lat': address_info['lat'] or self._safe_float(row.get('LATITUDE')),
                'lon': address_info['lon'] or self._safe_float(row.get('LONGITUDE')),
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
                    'use_refer': str(row.get('USE_REFER', '')),
                    'all_dongs': address_info.get('si_gun_gu_dongs', [])  # 여러 동 정보 저장
                },
                'data_source': 'openseoul',
                'geo_extra': address_info['geo_extra']
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"공원 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_subway_stations(self, file_path: Path):
        """지하철역 데이터 정규화 (역정보 + 주소 CSV 매핑 + 주소 정규화)"""
        if not file_path.exists():
            logger.warning(f"지하철역 파일이 존재하지 않습니다: {file_path}")
            return

        # 1. 지하철역 정보 파일 로드
        df_stn = pd.read_csv(file_path, encoding="utf-8", dtype=str)
        logger.info(f"지하철역 데이터 로드: {len(df_stn)}개")

        # 2. 주소 정보 파일 로드 (StationAdresTelno)
        addr_file = self.data_dir / "seoul_StationAdresTelno_20250921.csv"
        addr_map = {}
        if addr_file.exists():
            df_addr = pd.read_csv(addr_file, encoding="utf-8", dtype=str)

            # 주소 컬럼 자동 탐색
            addr_col_candidates = ["OLD_ADDR", "OLD_ADDRESS", "ADDR", "ADDRESS"]
            addr_col = next((c for c in addr_col_candidates if c in df_addr.columns), None)

            if not addr_col:
                raise ValueError(f"주소 컬럼을 찾을 수 없습니다. df_addr.columns={df_addr.columns.tolist()}")

            if "SBWY_STNS_NM" not in df_addr.columns:
                raise ValueError(f"'SBWY_STNS_NM' 컬럼을 찾을 수 없습니다. df_addr.columns={df_addr.columns.tolist()}")

            # "역" 제거 및 괄호 내용 제거 후 매핑
            import re
            station_names_cleaned = df_addr["SBWY_STNS_NM"].astype(str).str.replace("역", "").str.strip()
            # 괄호 안의 내용 제거 (예: "충정로(경기대입구)" → "충정로")
            station_names_cleaned = station_names_cleaned.apply(lambda x: re.sub(r'\([^)]*\)', '', x).strip())
            
            addr_map = dict(
                zip(
                    station_names_cleaned,
                    df_addr[addr_col].astype(str).str.strip()
                )
            )
            logger.info(f"지하철역 주소 데이터 로드: {len(addr_map)}개")
        else:
            logger.warning(f"지하철역 주소 파일이 존재하지 않습니다: {addr_file}")

        # 3. 지하철역 데이터 순회
        for _, row in df_stn.iterrows():
            # (1) 역명
            station_name_raw = str(row.get("STATION_NM", "")).strip()

            # (2) 주소 매핑 (서울만 성공 → 서울 외 지역은 빈값)
            address_raw = addr_map.get(station_name_raw, "")
            
            # (2-1) 지하철역 주소 전처리
            if address_raw:
                # 오타 수정
                address_raw = address_raw.replace("서울툭별시", "서울특별시")
                # 역명 제거 (예: "봉천역(2호선)" → "봉천")
                import re
                address_raw = re.sub(r'[가-힣]+역\([^)]*\)', '', address_raw).strip()
                # 괄호 제거
                address_raw = re.sub(r'\([^)]*\)', '', address_raw).strip()
                # 공백 정리
                address_raw = re.sub(r'\s+', ' ', address_raw).strip()
            
            # (3) 주소 정규화 (지하철역은 간단한 파싱만 사용)
            if address_raw:
                address_info = self._parse_common_address(address_raw, create_norm=True)
                # 서울특별시 정보 추가
                if '서울특별시' in address_raw or '서울' in address_raw:
                    address_info['si_do'] = '서울특별시'
                    # address_norm에 서울특별시 추가
                    if address_info['address_norm'] and address_info['si_gun_gu']:
                        address_info['address_norm'] = f"서울특별시 {address_info['address_norm']}"
            else:
                address_info = {
                    'address_raw': address_raw,
                    'address_norm': None,
                    'si_do': None,
                    'si_gun_gu': None,
                    'si_gun_gu_dong': None,
                    'road_full': None,
                    'jibun_full': None,
                    'lat': None,
                    'lon': None,
                    'geo_extra': None
                }

            # (4) 호선 정보 (CSV 원본 그대로 반영)
            line_name = str(row.get("LINE_NUM", "")).strip()

            # (5) 환승 처리
            transfer_lines = []
            is_transfer = False
            if "," in line_name:
                transfer_lines = [ln.strip() for ln in line_name.split(",")]
                is_transfer = True

            # (6) 최종 데이터 구성 (주소 필드 순서 통일)
            station_data = {
                "station_name": station_name_raw,
                "line_name": line_name,  # ✅ CSV 원본 반영
                "station_code": str(row.get("FR_CODE", "")),
                "address_raw": address_info['address_raw'],
                "address_norm": address_info['address_norm'],
                "si_do": address_info['si_do'],
                "si_gun_gu": address_info['si_gun_gu'],
                "si_gun_gu_dong": address_info.get('si_gun_gu_dong'),
                "road_full": address_info.get('road_full'),
                "jibun_full": address_info.get('jibun_full'),
                "address_id": None,  # FK는 DB 적재 단계에서 처리
                "lat": address_info['lat'],
                "lon": address_info['lon'],
                "exit_count": None,
                "is_transfer": is_transfer,
                "transfer_lines": transfer_lines,
                "station_extra": {
                    "station_name_eng": str(row.get("STATION_NM_ENG", "")),
                    "station_name_chn": str(row.get("STATION_NM_CHN", "")),
                    "station_name_jpn": str(row.get("STATION_NM_JPN", "")),
                    "subway_code": str(row.get("SBWY_STNS_NM", "")),
                    "route_code": str(row.get("SBWY_ROUT_LN", "")),
                },
                "data_source": "seoul_subway",
                "geo_extra": address_info['geo_extra']
            }
            self.normalized_subway_stations.append(station_data)

        logger.info(f"지하철역 데이터 정규화 완료: {len(self.normalized_subway_stations)}개")

    def _normalize_pharmacies(self, file_path: Path):
        """약국 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"약국 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"약국 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            address_raw = str(row.get('DUTYADDR', ''))
            facility_name = str(row.get('DUTYNAME', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'pharmacy')
            
            facility_data = {
                'category_id': self._get_category_id('pharmacy'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_norm': address_info['address_norm'],
                'si_do': address_info['si_do'],
                'si_gun_gu': address_info['si_gun_gu'],
                'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                'road_full': address_info.get('road_full'),
                'jibun_full': address_info.get('jibun_full'),
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
                'data_source': 'openseoul',
                'geo_extra': address_info['geo_extra']
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"약국 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_kindergartens(self, file_path: Path):
        """유치원 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"유치원 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"유치원 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            address_raw = str(row.get('ADDR', ''))
            facility_name = str(row.get('KDGT_NM', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'kindergarten')
            
            facility_data = {
                'category_id': self._get_category_id('childSchool'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_norm': address_info['address_norm'],
                'si_do': address_info['si_do'],
                'si_gun_gu': address_info['si_gun_gu'],
                'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                'road_full': address_info.get('road_full'),
                'jibun_full': address_info.get('jibun_full'),
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
                'data_source': 'openseoul',
                'geo_extra': address_info['geo_extra']
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"유치원 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def _normalize_colleges(self, file_path: Path):
        """대학 데이터 정규화"""
        if not file_path.exists():
            logger.warning(f"대학 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"대학 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            address_raw = str(row.get('ADD_KOR_ROAD', ''))
            facility_name = str(row.get('NAME_KOR', ''))
            address_info = self._normalize_address(address_raw, facility_name, 'college')
            
            facility_data = {
                'category_id': self._get_category_id('college'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_norm': address_info['address_norm'],
                'si_do': address_info['si_do'],
                'si_gun_gu': address_info['si_gun_gu'],
                'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                'road_full': address_info.get('road_full'),
                'jibun_full': address_info.get('jibun_full'),
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
                'data_source': 'openseoul',
                'geo_extra': address_info['geo_extra']
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"대학 데이터 정규화 완료: {len(self.normalized_facilities)}개")


    def _normalize_bus_stops(self, file_path: Path):
        """버스정류소 데이터 정규화 - 경도,위도 형식으로 address_raw 저장"""
        if not file_path.exists():
            logger.warning(f"버스정류소 파일이 존재하지 않습니다: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"버스정류소 데이터 정규화 시작: {len(df)}개")

        for _, row in df.iterrows():
            # 경도(XCRD), 위도(YCRD)를 '경도,위도' 형식으로 address_raw에 저장
            x_coord = self._safe_float(row.get('XCRD'))
            y_coord = self._safe_float(row.get('YCRD'))
            
            if x_coord is not None and y_coord is not None:
                address_raw = f"{x_coord},{y_coord}"
            else:
                address_raw = ""
            
            facility_data = {
                'category_id': self._get_category_id('bus_stop'),
                'name': str(row.get('STOPS_NM', '')),  # 정류소명
                'address_raw': address_raw,
                'address_norm': None,  # 좌표 기반이므로 정규화 불가
                'si_do': None,
                'si_gun_gu': None,
                'si_gun_gu_dong': None,
                'road_full': None,
                'jibun_full': None,
                'lat': y_coord,  # 위도
                'lon': x_coord,  # 경도
                'phone': None,
                'website': None,
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'stops_no': str(row.get('STOPS_NO', '')),
                    'node_id': str(row.get('NODE_ID', '')),
                    'stops_type': str(row.get('STOPS_TYPE', '')),
                    'x_coord': x_coord,
                    'y_coord': y_coord
                },
                'data_source': 'seoul_bus_stop',
                'geo_extra': None
            }
            self.normalized_facilities.append(facility_data)
        logger.info(f"버스정류소 데이터 정규화 완료: {len(self.normalized_facilities)}개")

    def normalize_openseoul_data(self) -> Dict[str, List[Dict]]:
        """OpenSeoul CSV 파일들을 정규화"""
        openseoul_dir = self.data_dir  # backend/data/public-api/openseoul

        # 어린이집 데이터
        childcare_file = openseoul_dir / "seoul_ChildCareInfo_20250919.csv"
        self._normalize_childcare_centers(childcare_file)
        
        # 유치원 데이터
        kindergarten_file = openseoul_dir / "seoul_childSchoolInfo_20250919.csv"
        self._normalize_kindergartens(kindergarten_file)
        
        # 학교 데이터 (초중고)
        school_file = openseoul_dir / "seoul_neisSchoolInfo_20250919.csv"
        self._normalize_schools(school_file)
        
        # 대학 데이터
        college_file = openseoul_dir / "seoul_SebcCollegeInfoKor_20250919.csv"
        self._normalize_colleges(college_file)
        
        # 공원 데이터
        park_file = openseoul_dir / "seoul_SearchParkInfoService_20250919.csv"
        self._normalize_parks(park_file)
        
        # 지하철역 데이터
        subway_file = openseoul_dir / "seoul_SearchSTNBySubwayLineInfo_20250919.csv"
        self._normalize_subway_stations(subway_file)
        
        # 약국 데이터
        pharmacy_file = openseoul_dir / "seoul_TbPharmacyOperateInfo_20250919.csv"
        self._normalize_pharmacies(pharmacy_file)
        
        # 대학 데이터
        college_file = openseoul_dir / "seoul_SebcCollegeInfoKor_20250919.csv"
        self._normalize_colleges(college_file)


        # 버스정류소 데이터 (최근 수집된 파일)
        bus_stop_file = openseoul_dir / "seoul_busStopLocationXyInfo_20250921.csv"
        self._normalize_bus_stops(bus_stop_file)

        logger.info(f"총 {len(self.normalized_facilities)}개의 시설 데이터와 {len(self.normalized_subway_stations)}개의 지하철역 데이터 정규화 완료.")
        
        return {
            "public_facilities": self.normalized_facilities,
            "subway_stations": self.normalized_subway_stations,
            "failed_addresses": self.failed_addresses
        }
    
    def save_normalized_data(self, output_dir: Path) -> Path:
        """정규화된 데이터를 JSON 파일로 저장"""
        import json
        from datetime import datetime
        
        # 출력 디렉토리 생성
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 정규화된 데이터 구성
        # 정규화된 데이터 구조화
        public_facilities_data = {
            "public_facilities": self.normalized_facilities,
            "metadata": {
                "normalized_at": datetime.now().isoformat(),
                "facilities_count": len(self.normalized_facilities),
                "failed_addresses_count": len(self.failed_addresses)
            }
        }
        
        subway_stations_data = {
            "subway_stations": self.normalized_subway_stations,
            "metadata": {
                "normalized_at": datetime.now().isoformat(),
                "subway_stations_count": len(self.normalized_subway_stations)
            }
        }
        
        # JSON 파일로 저장 (별도 파일)
        public_facilities_file = output_dir / "public_facilities.json"
        with open(public_facilities_file, 'w', encoding='utf-8') as f:
            json.dump(public_facilities_data, f, ensure_ascii=False, indent=2)
        
        subway_stations_file = output_dir / "subway_stations.json"
        with open(subway_stations_file, 'w', encoding='utf-8') as f:
            json.dump(subway_stations_data, f, ensure_ascii=False, indent=2)
        
        # 실패한 주소 정규화 데이터 CSV로 저장
        if self.failed_addresses:
            failed_file = output_dir / "failed_addresses.csv"
            df_failed = pd.DataFrame(self.failed_addresses)
            df_failed.to_csv(failed_file, index=False, encoding='utf-8')
            logger.info(f"실패한 주소 정규화 데이터 저장: {failed_file}")
        
        # 메타데이터 파일 저장
        metadata_file = output_dir / "metadata.json"
        combined_metadata = {
            "normalized_at": datetime.now().isoformat(),
            "public_facilities_count": len(self.normalized_facilities),
            "subway_stations_count": len(self.normalized_subway_stations),
            "failed_addresses_count": len(self.failed_addresses)
        }
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(combined_metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"정규화된 데이터 저장 완료:")
        logger.info(f"  - public_facilities.json: {len(self.normalized_facilities)}개")
        logger.info(f"  - subway_stations.json: {len(self.normalized_subway_stations)}개")
        logger.info(f"  - metadata.json: 메타데이터")
        
        return public_facilities_file, subway_stations_file

    def retry_failed_addresses(self, failed_csv_path: Path) -> Dict[str, List[Dict]]:
        """실패한 주소들만 다시 정규화 시도"""
        logger.info(f"실패한 주소 재정규화 시작: {failed_csv_path}")
        
        # 실패한 주소 CSV 읽기
        df_failed = pd.read_csv(failed_csv_path, encoding='utf-8')
        logger.info(f"재정규화 대상: {len(df_failed)}개")
        
        # 재정규화된 데이터 저장용
        retry_facilities = []
        retry_failed_addresses = []
        
        for idx, row in df_failed.iterrows():
            facility_type = row['facility_type']
            facility_name = row['facility_name']
            address_raw = row['address_raw']
            
            logger.info(f"재정규화 시도 [{idx+1}/{len(df_failed)}]: {facility_name} - {address_raw}")
            
            # 주소 정규화 시도
            address_info = self._normalize_address(address_raw, facility_name, facility_type)
            
            if address_info['address_norm']:
                # 정규화 성공 - 시설 데이터 생성
                facility_data = {
                    'category_id': self._get_category_id(facility_type),
                    'name': facility_name,
                    'address_raw': address_info['address_raw'],
                    'address_norm': address_info['address_norm'],
                    'si_do': address_info['si_do'],
                    'si_gun_gu': address_info['si_gun_gu'],
                    'si_gun_gu_dong': address_info.get('si_gun_gu_dong'),
                    'road_full': address_info.get('road_full'),
                    'jibun_full': address_info.get('jibun_full'),
                    'lat': address_info['lat'],
                    'lon': address_info['lon'],
                    'phone': None,
                    'website': None,
                    'operating_hours': None,
                    'is_24h': False,
                    'is_emergency': False,
                    'capacity': None,
                    'grade_level': None,
                    'facility_extra': {
                        'retry_success': True,
                        'original_failed_reason': row['error_reason']
                    },
                    'data_source': f'seoul_{facility_type}',
                    'geo_extra': address_info['geo_extra']
                }
                retry_facilities.append(facility_data)
                logger.info(f"✅ 재정규화 성공: {facility_name}")
            else:
                # 여전히 실패
                failed_data = {
                    "facility_type": facility_type,
                    "facility_name": facility_name,
                    "address_raw": address_raw,
                    "address_processed": preprocess_address(address_raw),
                    "error_reason": "Retry failed - No match from Juso API",
                    "timestamp": pd.Timestamp.now().isoformat(),
                    "original_failed_reason": row['error_reason']
                }
                retry_failed_addresses.append(failed_data)
                logger.warning(f"❌ 재정규화 실패: {facility_name}")
        
        logger.info(f"재정규화 완료: 성공 {len(retry_facilities)}개, 실패 {len(retry_failed_addresses)}개")
        
        return {
            "retry_facilities": retry_facilities,
            "retry_failed_addresses": retry_failed_addresses
        }

# 예시 사용법 (CLI에서 호출될 때)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 프로젝트 루트에서 실행한다고 가정
    project_root = Path(__file__).resolve().parents[4]
    openseoul_data_path = project_root / "backend" / "data" / "public-api" / "openseoul"
    
    normalizer = InfraNormalizer(data_dir=openseoul_data_path)
    normalized_data = normalizer.normalize_openseoul_data()
    
    print("\n--- 정규화된 공공시설 데이터 (일부) ---")
    for i, facility in enumerate(normalized_data["public_facilities"][:5]):
        print(f"{i+1}. {facility['name']} (Category ID: {facility['category_id']})")

    print("\n--- 정규화된 지하철역 데이터 (일부) ---")
    for i, station in enumerate(normalized_data["subway_stations"][:5]):
        print(f"{i+1}. {station['station_name']} (Line: {station['line_name']})")
