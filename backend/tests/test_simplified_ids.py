#!/usr/bin/env python3
"""
단순화된 ID 시스템 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.data_collection.crawlers.base import generate_crawler_id, generate_space_id

def test_simplified_ids():
    """단순화된 ID 시스템 테스트"""
    
    print("=== 단순화된 ID 시스템 테스트 ===")
    
    # 테스트 데이터
    platform = "cohouse"
    platform_key = "detail_0000"
    address = "서울 도봉구 도봉로191길 80 (도봉동 351-2)"
    house_name = "오늘공동체주택"
    
    print(f"플랫폼: {platform}")
    print(f"플랫폼 키: {platform_key}")
    print(f"주소: {address}")
    print(f"건물명: {house_name}")
    print()
    
    # 1. 크롤러 ID 테스트
    print("1. 크롤러 ID 테스트:")
    notice_id = generate_crawler_id(platform, platform_key, "notice", 0)
    unit_id_0 = generate_crawler_id(platform, platform_key, "unit", 0)
    unit_id_1 = generate_crawler_id(platform, platform_key, "unit", 1)
    
    print(f"   Notice ID: {notice_id}")
    print(f"   Unit 0 ID: {unit_id_0}")
    print(f"   Unit 1 ID: {unit_id_1}")
    print()
    
    # 2. 물리적 공간 ID 테스트
    print("2. 물리적 공간 ID 테스트:")
    space_ids = []
    test_rooms = [
        ("1", "1", "101호"),
        ("2", "1", "201호"),
        ("2", "2", "202호"),
        ("3", "1", "301호"),
        ("1", "1", "근생"),  # 근생도 유효한 데이터
    ]
    
    for floor, room_num, room_name in test_rooms:
        space_id = generate_space_id(address, floor, room_num, house_name)
        space_ids.append(space_id)
        print(f"   {room_name} (층:{floor}, 호:{room_num}) -> {space_id}")
    
    print()
    
    # 3. ID 일관성 테스트
    print("3. ID 일관성 테스트:")
    
    # 같은 입력에 대해 동일한 ID 생성 확인
    id1 = generate_crawler_id(platform, platform_key, "notice", 0)
    id2 = generate_crawler_id(platform, platform_key, "notice", 0)
    print(f"   Notice ID 1: {id1}")
    print(f"   Notice ID 2: {id2}")
    print(f"   일관성: {'✅ PASS' if id1 == id2 else '❌ FAIL'}")
    
    # space_id 일관성 확인
    space1 = generate_space_id(address, "1", "1", house_name)
    space2 = generate_space_id(address, "1", "1", house_name)
    print(f"   Space ID 1: {space1}")
    print(f"   Space ID 2: {space2}")
    print(f"   일관성: {'✅ PASS' if space1 == space2 else '❌ FAIL'}")
    print()
    
    # 4. ID 개수 비교
    print("4. ID 개수 비교:")
    print("   기존 시스템: 8개 ID")
    print("   - record_id, occupancy_id, notice_id, item_id, unit_id, image_id, attachment_id, table_id")
    print("   개선된 시스템: 4개 ID")
    print("   - crawler_id, space_id, platform_key, DB_id")
    print("   ✅ 50% 감소!")
    print()
    
    # 5. ID 역할 명확화
    print("5. ID 역할 명확화:")
    print("   - crawler_id: 크롤러 식별자 (공고/유닛/첨부파일 구분)")
    print("   - space_id: 물리적 공간 식별자 (중복 제거용)")
    print("   - platform_key: 플랫폼 내 고유키 (중복 방지용)")
    print("   - DB_id: 데이터베이스 PK (내부 참조용)")

if __name__ == "__main__":
    test_simplified_ids()
