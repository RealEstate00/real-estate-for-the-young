#!/usr/bin/env python3
"""
ID 생성 시스템 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.data_collection.crawlers.base import generate_stable_occupancy_id, generate_notice_id

def test_id_generation():
    """ID 생성 함수들 테스트"""
    
    # 테스트 데이터
    address = "서울 도봉구 도봉로191길 80 (도봉동 351-2)"
    house_name = "오늘공동체주택"
    platform = "cohouse"
    platform_id = "test_platform_id"
    
    print("=== ID 생성 시스템 테스트 ===")
    print(f"주소: {address}")
    print(f"건물명: {house_name}")
    print()
    
    # notice_id 생성 테스트
    notice_id = generate_notice_id(platform, platform_id, house_name, address)
    print(f"Notice ID: {notice_id}")
    print()
    
    # occupancy_id 생성 테스트 (다양한 호수)
    test_cases = [
        ("1", "1", "101호"),
        ("2", "1", "201호"), 
        ("2", "2", "202호"),
        ("3", "1", "301호"),
        ("3", "2", "302호"),
        ("1", "1", "근생"),  # 근생도 유효한 데이터로 처리
    ]
    
    print("Occupancy ID 테스트:")
    for floor, room_num, room_name in test_cases:
        occupancy_id = generate_stable_occupancy_id(address, floor, room_num, house_name)
        print(f"  {room_name} (층:{floor}, 호:{room_num}) -> {occupancy_id}")
    
    print()
    print("=== 동일한 입력에 대한 일관성 테스트 ===")
    
    # 동일한 입력에 대해 동일한 ID가 생성되는지 테스트
    id1 = generate_stable_occupancy_id(address, "1", "1", house_name)
    id2 = generate_stable_occupancy_id(address, "1", "1", house_name)
    print(f"첫 번째 생성: {id1}")
    print(f"두 번째 생성: {id2}")
    print(f"일관성 확인: {'✅ PASS' if id1 == id2 else '❌ FAIL'}")
    
    print()
    print("=== 주소 정규화 테스트 ===")
    
    # 주소 정규화 테스트
    address_with_jibun = "서울 도봉구 도봉로191길 80 (도봉동 351-2)"
    address_normalized = "서울 도봉구 도봉로191길 80"
    
    id_with_jibun = generate_stable_occupancy_id(address_with_jibun, "1", "1", house_name)
    id_normalized = generate_stable_occupancy_id(address_normalized, "1", "1", house_name)
    
    print(f"지번 포함 주소: {address_with_jibun}")
    print(f"정규화된 주소: {address_normalized}")
    print(f"지번 포함 ID: {id_with_jibun}")
    print(f"정규화 ID: {id_normalized}")
    print(f"정규화 확인: {'✅ PASS' if id_with_jibun == id_normalized else '❌ FAIL'}")

if __name__ == "__main__":
    test_id_generation()
