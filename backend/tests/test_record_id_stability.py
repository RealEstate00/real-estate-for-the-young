#!/usr/bin/env python3
"""
record_id 안정성 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.data_collection.crawlers.base import generate_stable_record_id

def test_record_id_stability():
    """record_id 안정성 테스트"""
    
    print("=== record_id 안정성 테스트 ===")
    
    # 테스트 데이터
    platform = "cohouse"
    platform_id = "12345"
    house_name = "오늘공동체주택"
    unit_index = 0
    
    # 같은 공고, 다른 URL (세션 파라미터만 다름)
    list_url_1 = "https://cohouse.seoul.go.kr/list?page=1&session=abc123&timestamp=1234567890"
    list_url_2 = "https://cohouse.seoul.go.kr/list?page=1&session=def456&timestamp=9876543210"
    
    detail_url_1 = "https://cohouse.seoul.go.kr/detail?homeCode=12345&session=abc123&timestamp=1234567890"
    detail_url_2 = "https://cohouse.seoul.go.kr/detail?homeCode=12345&session=def456&timestamp=9876543210"
    
    print("1. 같은 공고, 다른 세션 파라미터:")
    print(f"   List URL 1: {list_url_1}")
    print(f"   List URL 2: {list_url_2}")
    print(f"   Detail URL 1: {detail_url_1}")
    print(f"   Detail URL 2: {detail_url_2}")
    
    id_1 = generate_stable_record_id(platform, platform_id, list_url_1, detail_url_1, house_name, unit_index)
    id_2 = generate_stable_record_id(platform, platform_id, list_url_2, detail_url_2, house_name, unit_index)
    
    print(f"   Record ID 1: {id_1}")
    print(f"   Record ID 2: {id_2}")
    print(f"   안정성 확인: {'✅ PASS' if id_1 == id_2 else '❌ FAIL'}")
    print()
    
    # 다른 공고 (다른 homeCode)
    detail_url_3 = "https://cohouse.seoul.go.kr/detail?homeCode=67890&session=abc123"
    id_3 = generate_stable_record_id(platform, "67890", list_url_1, detail_url_3, house_name, unit_index)
    
    print("2. 다른 공고 (다른 homeCode):")
    print(f"   Detail URL 3: {detail_url_3}")
    print(f"   Record ID 3: {id_3}")
    print(f"   다른 공고 구분: {'✅ PASS' if id_1 != id_3 else '❌ FAIL'}")
    print()
    
    # 다른 unit_index
    id_4 = generate_stable_record_id(platform, platform_id, list_url_1, detail_url_1, house_name, 1)
    
    print("3. 같은 공고, 다른 unit:")
    print(f"   Unit 0 ID: {id_1}")
    print(f"   Unit 1 ID: {id_4}")
    print(f"   다른 Unit 구분: {'✅ PASS' if id_1 != id_4 else '❌ FAIL'}")
    print()
    
    # URL 파싱 테스트
    print("4. URL 파싱 테스트:")
    test_urls = [
        "https://cohouse.seoul.go.kr/detail?homeCode=12345&session=abc&timestamp=123",
        "https://sohouse.seoul.go.kr/view.do?homeCode=67890&boardId=1&session=def",
        "https://youth.seoul.go.kr/detail?id=999&seq=1&session=ghi",
        "https://example.com/path/12345?other=value&session=xyz"
    ]
    
    for url in test_urls:
        stable = generate_stable_record_id("test", "123", url, url, "test", 0)
        print(f"   {url}")
        print(f"   -> {stable}")

if __name__ == "__main__":
    test_record_id_stability()
