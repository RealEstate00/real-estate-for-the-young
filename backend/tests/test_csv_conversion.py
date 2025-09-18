#!/usr/bin/env python3
"""
CSV 변환 테스트 - 기존 CSV를 새로운 ID 구조로 변환
"""

import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.data_collection.crawlers.base import generate_stable_occupancy_id, generate_notice_id

def convert_existing_csv():
    """기존 CSV를 새로운 ID 구조로 변환"""
    
    # 기존 CSV 파일 경로
    csv_path = "/Users/jina/Documents/GitHub/SeoulHousingAssistBot/backend/data/raw/cohouse/2025-09-18__20250918T111243/tables/detail_0000_unit_00_occupancy.csv"
    
    print("=== 기존 CSV를 새로운 ID 구조로 변환 ===")
    
    # 기존 CSV 읽기
    df = pd.read_csv(csv_path)
    print(f"기존 CSV 구조: {list(df.columns)}")
    print(f"총 {len(df)} 행")
    print()
    
    # 새로운 컬럼 추가
    address = "서울 도봉구 도봉로191길 80 (도봉동 351-2)"
    house_name = "오늘공동체주택"
    platform = "cohouse"
    platform_id = "detail_0000_unit_00"
    
    # notice_id 생성 (공고별 고유 ID)
    notice_id = generate_notice_id(platform, platform_id, house_name, address)
    
    # 새로운 컬럼들 추가
    df['occupancy_id'] = ''
    df['notice_id'] = notice_id
    
    # 각 행에 대해 occupancy_id 생성
    for idx, row in df.iterrows():
        if idx == 0:  # 헤더 행 스킵
            continue
            
        floor = str(row.get('층', '')).strip()
        room_number = str(row.get('호', '')).strip()
        
        occupancy_id = generate_stable_occupancy_id(address, floor, room_number, house_name)
        df.at[idx, 'occupancy_id'] = occupancy_id
    
    # 컬럼 순서 재정렬
    new_columns = ['record_id', 'occupancy_id', 'notice_id'] + [col for col in df.columns if col not in ['record_id', 'occupancy_id', 'notice_id']]
    df = df[new_columns]
    
    print("새로운 CSV 구조:")
    print(df.head())
    print()
    
    # 새로운 CSV 저장
    output_path = "/Users/jina/Documents/GitHub/SeoulHousingAssistBot/test_converted_occupancy.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"변환된 CSV 저장: {output_path}")
    
    print()
    print("=== ID 일관성 확인 ===")
    print("동일한 층/호수에 대해 동일한 ID가 생성되는지 확인:")
    
    # 101호 (층:1, 호:1) 테스트
    test_id_1 = generate_stable_occupancy_id(address, "1", "1", house_name)
    test_id_2 = generate_stable_occupancy_id(address, "1", "1", house_name)
    print(f"101호 ID 1: {test_id_1}")
    print(f"101호 ID 2: {test_id_2}")
    print(f"일관성: {'✅ PASS' if test_id_1 == test_id_2 else '❌ FAIL'}")

if __name__ == "__main__":
    convert_existing_csv()
