#!/usr/bin/env python3
"""
record_id를 notice_id로 사용 가능한지 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.data_collection.crawlers.base import generate_stable_record_id, generate_notice_id

def test_record_as_notice():
    """record_id를 notice_id로 사용 가능한지 테스트"""
    
    print("=== record_id를 notice_id로 사용 가능한지 테스트 ===")
    
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
    print()
    
    # 1. 현재 notice_id
    current_notice_id = generate_notice_id(platform, platform_id, house_name, address)
    print(f"1. 현재 notice_id: {current_notice_id}")
    print()
    
    # 2. record_id (unit_index=0) - notice_id로 사용 가능한지?
    record_id_unit_0 = generate_stable_record_id(platform, platform_id, list_url, detail_url, house_name, 0)
    print(f"2. record_id (unit=0): {record_id_unit_0}")
    print(f"   notice_id와 동일한가?: {'✅ YES' if current_notice_id == record_id_unit_0 else '❌ NO'}")
    print()
    
    # 3. 같은 공고의 다른 unit들
    print("3. 같은 공고의 다른 unit들:")
    for unit_index in range(3):
        record_id = generate_stable_record_id(platform, platform_id, list_url, detail_url, house_name, unit_index)
        print(f"   Unit {unit_index}: {record_id}")
        print(f"   Unit {unit_index} == notice_id?: {'✅ YES' if current_notice_id == record_id else '❌ NO'}")
    print()
    
    # 4. 다른 공고 테스트
    print("4. 다른 공고 테스트:")
    notice_id_2 = generate_notice_id(platform, "67890", house_name, address)
    record_id_2 = generate_stable_record_id(platform, "67890", list_url, detail_url, house_name, 0)
    print(f"   Notice ID (공고2):   {notice_id_2}")
    print(f"   Record ID (공고2):   {record_id_2}")
    print(f"   동일한가?: {'✅ YES' if notice_id_2 == record_id_2 else '❌ NO'}")
    print()
    
    # 5. 결론
    print("5. 결론:")
    if current_notice_id == record_id_unit_0:
        print("   ✅ record_id (unit=0)를 notice_id로 사용 가능!")
        print("   ✅ 같은 공고의 모든 unit이 동일한 notice_id를 가짐")
    else:
        print("   ❌ record_id (unit=0)를 notice_id로 사용 불가")
        print("   ❌ 생성 로직이 다름")

if __name__ == "__main__":
    test_record_as_notice()
