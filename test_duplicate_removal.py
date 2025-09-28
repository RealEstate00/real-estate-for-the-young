#!/usr/bin/env python3
"""
중복 제거 로직 테스트
"""

import json
from pathlib import Path

def extract_unique_addresses(failed_jsonl_path: Path) -> dict:
    """JSONL 파일에서 중복 제거하여 고유한 주소만 추출"""
    unique_addresses = {}
    
    with open(failed_jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    failed_data = json.loads(line.strip())
                    # 고유 키: facility_type + facility_name + address_raw
                    unique_key = f"{failed_data['facility_type']}|{failed_data['facility_name']}|{failed_data['address_raw']}"
                    
                    if unique_key not in unique_addresses:
                        unique_addresses[unique_key] = failed_data
                except json.JSONDecodeError:
                    continue
    
    return unique_addresses

def count_lines(file_path: Path) -> int:
    """파일의 총 라인 수 계산"""
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1
    return count

def get_duplicate_count(failed_jsonl_path: Path, facility_key: str) -> int:
    """특정 facility_key의 중복 개수 계산"""
    count = 0
    facility_type, facility_name, address_raw = facility_key.split('|', 2)
    
    with open(failed_jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    failed_data = json.loads(line.strip())
                    if (failed_data['facility_type'] == facility_type and 
                        failed_data['facility_name'] == facility_name and 
                        failed_data['address_raw'] == address_raw):
                        count += 1
                except json.JSONDecodeError:
                    continue
    
    return count

if __name__ == "__main__":
    failed_jsonl_path = Path("data/normalized/infra/failed_addresses.jsonl")
    
    if not failed_jsonl_path.exists():
        print(f"파일이 존재하지 않습니다: {failed_jsonl_path}")
        exit(1)
    
    print("🔍 중복 제거 테스트 시작...")
    
    # 전체 라인 수
    total_lines = count_lines(failed_jsonl_path)
    print(f"📊 전체 라인 수: {total_lines}")
    
    # 고유한 주소 추출
    unique_addresses = extract_unique_addresses(failed_jsonl_path)
    unique_count = len(unique_addresses)
    print(f"📊 고유한 주소 수: {unique_count}")
    print(f"📊 중복 제거율: {((total_lines - unique_count) / total_lines * 100):.1f}%")
    
    # 상위 10개 중복 데이터 확인
    print("\n🔍 상위 10개 중복 데이터:")
    duplicate_counts = []
    for facility_key in unique_addresses.keys():
        dup_count = get_duplicate_count(failed_jsonl_path, facility_key)
        if dup_count > 1:
            duplicate_counts.append((facility_key, dup_count))
    
    # 중복 개수 순으로 정렬
    duplicate_counts.sort(key=lambda x: x[1], reverse=True)
    
    for i, (facility_key, dup_count) in enumerate(duplicate_counts[:10], 1):
        facility_type, facility_name, address_raw = facility_key.split('|', 2)
        print(f"{i:2d}. {facility_name} ({facility_type}) - {dup_count}회 중복")
        print(f"    주소: {address_raw}")
    
    print(f"\n✅ 테스트 완료: {len(duplicate_counts)}개 주소가 중복됨")
