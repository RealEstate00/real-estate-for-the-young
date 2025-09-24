#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
주소 정규화 디버깅 - 실제 JUSO API 호출 확인
"""

import logging
from backend.services.data_collection.curated.address_api import normalize_address, AddressNormalizerError

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_address_normalization():
    """주소 정규화 디버깅"""
    
    # 테스트할 주소들
    test_addresses = [
        "서울특별시 강남구 광평로34길 55",
        "서울특별시 강남구 광평로 34길 55",
        "서울특별시 강남구 광평로34길",
        "서울특별시 강남구 광평로",
        "서울특별시 강남구",
        "서울특별시 강남구 광평로34길 55 강남데시앙포레 아파트 키즈센터1층"
    ]
    
    print("=== 주소 정규화 디버깅 ===\n")
    
    for i, addr in enumerate(test_addresses, 1):
        print(f"--- 테스트 {i}: {addr} ---")
        
        try:
            result = normalize_address(addr)
            print(f"✅ 성공!")
            print(f"  sido: {result.get('sido')}")
            print(f"  sigungu: {result.get('sigungu')}")
            print(f"  road_full: {result.get('road_full')}")
            print(f"  jibun_full: {result.get('jibun_full')}")
            print(f"  x: {result.get('x')}")
            print(f"  y: {result.get('y')}")
        except AddressNormalizerError as e:
            print(f"❌ 실패: {e}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        print()

if __name__ == "__main__":
    debug_address_normalization()


