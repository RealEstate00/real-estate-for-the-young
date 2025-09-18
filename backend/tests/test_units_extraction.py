#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Units 추출 테스트 스크립트
"""

import json
from pathlib import Path
from backend.services.data_collection.parsers.parsers import extract_units_from_notice

def test_units_extraction():
    """Units 추출 테스트"""
    
    # 실제 데이터 경로
    data_dir = Path("/Users/jina/Documents/GitHub/SeoulHousingAssistBot/backend/data/raw/cohouse/2025-09-15__20250915T132322")
    
    # 테스트용 JSON 데이터 (실제 cohouse 데이터)
    test_json = {
        "cohouse_text_extracted_info": {
            "extracted_patterns": {
                "areas": [
                    "655.42",
                    "237.24", 
                    "28.49",
                    "80.02",
                    "24.03",
                    "80.36",
                    "35.41",
                    "31.83",
                    "45.87"
                ],
                "prices": [
                    "50,000,000",
                    "320,000",
                    "1,230,000",
                    "1,260,000",
                    "490,000",
                    "570,000"
                ]
            }
        }
    }
    
    print("=== 1. JSON 데이터만 사용한 Units 추출 테스트 ===")
    units = extract_units_from_notice(None, "", test_json)
    print(f"추출된 Units 수: {len(units)}")
    
    for i, unit in enumerate(units):
        print(f"\nUnit {i}:")
        print(f"  - 면적: {unit.get('area_m2')}㎡")
        print(f"  - 보증금: {unit.get('deposit')}원")
        print(f"  - 월임대료: {unit.get('rent')}원")
        print(f"  - 관리비: {unit.get('maintenance_fee')}원")
        print(f"  - 호수: {unit.get('room_number')}")
        print(f"  - Unit Index: {unit.get('unit_extra', {}).get('unit_index')}")
        print(f"  - 데이터 소스: {unit.get('unit_extra', {}).get('data_source')}")
    
    print("\n=== 2. Occupancy 테이블을 사용한 Units 추출 테스트 ===")
    
    # 실제 occupancy 테이블들 테스트
    table_files = list((data_dir / "tables").glob("detail_*_occupancy.csv"))
    
    for table_file in table_files[:3]:  # 처음 3개 파일만 테스트
        print(f"\n--- {table_file.name} ---")
        
        # JSON 데이터도 함께 로드
        json_file = data_dir / "kv" / table_file.name.replace("_occupancy.csv", ".json")
        json_data = None
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        
        # Units 추출
        units = extract_units_from_notice(None, "", json_data, str(table_file))
        
        print(f"추출된 Units 수: {len(units)}")
        
        for i, unit in enumerate(units):
            print(f"  Unit {i}:")
            print(f"    - 방이름: {unit.get('unit_extra', {}).get('room_name', 'N/A')}")
            print(f"    - 면적: {unit.get('area_m2')}㎡")
            print(f"    - 보증금: {unit.get('deposit')}원")
            print(f"    - 월임대료: {unit.get('rent')}원")
            print(f"    - 관리비: {unit.get('maintenance_fee')}원")
            print(f"    - 층: {unit.get('floor')}층")
            print(f"    - 호수: {unit.get('room_number')}호")
            print(f"    - 인원: {unit.get('occupancy')}명")
            print(f"    - 데이터 소스: {unit.get('unit_extra', {}).get('data_source')}")

if __name__ == "__main__":
    test_units_extraction()
