#!/usr/bin/env python3
"""
record_id와 notice_id 관계 분석
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.data_collection.crawlers.base import generate_stable_record_id, generate_notice_id

def test_id_relationship():
    """record_id와 notice_id 관계 테스트"""
    
    print("=== record_id와 notice_id 관계 분석 ===")
    
    # 테스트 데이터
    platform = "cohouse"
    platform_id = "12345"
    list_url = "https://cohouse.seoul.go.kr/list?page=1"
    detail_url = "https://cohouse.seoul.go.kr/detail?homeCode=12345"
    house_name = "오늘공동체주택"
    address = "서울 도봉구 도봉로191길 80"
    
    print(f"플랫폼: {platform}")
    print(f"공고 ID: {platform_id}")
    print(f"건물명: {house_name}")
    print(f"주소: {address}")
    print()
    
    # 1. 같은 공고의 다른 unit들
    print("1. 같은 공고의 다른 unit들:")
    for unit_index in range(3):
        record_id = generate_stable_record_id(platform, platform_id, list_url, detail_url, house_name, unit_index)
        print(f"   Unit {unit_index}: {record_id}")
    
    print()
    
    # 2. notice_id (공고별 동일)
    notice_id = generate_notice_id(platform, platform_id, house_name, address)
    print(f"2. Notice ID (공고별 동일): {notice_id}")
    print()
    
    # 3. record_id에서 unit_index 제거한 버전
    print("3. record_id에서 unit_index 제거한 버전:")
    for unit_index in range(3):
        # unit_index를 0으로 고정해서 생성
        record_id_no_unit = generate_stable_record_id(platform, platform_id, list_url, detail_url, house_name, 0)
        print(f"   Unit {unit_index} (unit_index=0): {record_id_no_unit}")
    
    print()
    
    # 4. notice_id와 record_id(unit_index=0) 비교
    record_id_unit_0 = generate_stable_record_id(platform, platform_id, list_url, detail_url, house_name, 0)
    print(f"4. 비교:")
    print(f"   Notice ID:           {notice_id}")
    print(f"   Record ID (unit=0):  {record_id_unit_0}")
    print(f"   동일한가?: {'✅ YES' if notice_id == record_id_unit_0 else '❌ NO'}")
    print()
    
    # 5. 다른 공고 테스트
    print("5. 다른 공고 테스트:")
    notice_id_2 = generate_notice_id(platform, "67890", house_name, address)
    record_id_2 = generate_stable_record_id(platform, "67890", list_url, detail_url, house_name, 0)
    print(f"   Notice ID (공고2):   {notice_id_2}")
    print(f"   Record ID (공고2):   {record_id_2}")
    print(f"   동일한가?: {'✅ YES' if notice_id_2 == record_id_2 else '❌ NO'}")

if __name__ == "__main__":
    test_id_relationship()
