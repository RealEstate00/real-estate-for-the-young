#!/usr/bin/env python3
"""
공원 데이터 노말라이징 테스트 (상위 15개)
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import logging

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 특정 모듈들의 로깅 레벨을 INFO로 설정
logging.getLogger('backend.services.data_collection.curated.infra_normalizer').setLevel(logging.INFO)
logging.getLogger('backend.services.data_collection.curated.address_api').setLevel(logging.INFO)

from backend.services.data_collection.curated.infra_normalizer import InfraNormalizer, read_csv_with_auto_encoding

def test_park_normalize_15():
    """공원 데이터 노말라이징 테스트 (상위 15개)"""
    
    print("🌳 공원 데이터 노말라이징 테스트 시작 (상위 15개)")
    
    # 데이터 디렉토리 설정
    data_dir = Path("backend/data/public-api/openseoul")
    
    # InfraNormalizer 인스턴스 생성
    normalizer = InfraNormalizer(data_dir)
    
    # 공원 데이터 파일 확인
    park_file = data_dir / "seoul_SearchParkInfoService_20250919.csv"
    
    if not park_file.exists():
        print(f"❌ 공원 데이터 파일이 존재하지 않습니다: {park_file}")
        return
    
    print(f"📁 공원 데이터 파일: {park_file}")
    
    try:
        # 공원 데이터 읽기
        df = read_csv_with_auto_encoding(park_file)
        print(f"📊 전체 공원 데이터: {len(df)}개")
        
        # 상위 15개만 처리
        limited_df = df.head(15)
        print(f"🎯 처리할 공원 데이터: {len(limited_df)}개")
        
        # 기존 normalized_facilities 초기화
        normalizer.normalized_facilities = []
        
        # 공원 데이터 정규화
        for _, row in limited_df.iterrows():
            address_raw = str(row.get('P_ADDR', ''))
            facility_name = str(row.get('P_PARK', ''))
            
            print(f"\n🌳 처리 중: {facility_name}")
            print(f"📍 주소: {address_raw}")
            
            # InfraNormalizer의 _normalize_address 함수 사용
            address_info = normalizer._normalize_address(address_raw, facility_name, 'park')
            
            # 원본 좌표도 확인 (기존 로직과 동일)
            original_lat = normalizer._safe_float(row.get('LATITUDE'))
            original_lon = normalizer._safe_float(row.get('LONGITUDE'))
            
            # 좌표 우선순위: 변환된 좌표 > 원본 좌표
            final_lat = address_info.get('lat') or original_lat
            final_lon = address_info.get('lon') or original_lon
            
            # 공원 데이터 구조 생성
            facility_data = {
                'facility_id': normalizer._generate_facility_id('park'),
                'cd': normalizer._get_facility_cd('park'),
                'name': facility_name,
                'address_raw': address_info.get('address_raw', address_raw),
                'address_nm': address_info.get('address_nm', address_raw),
                'address_id': address_info.get('address_id'),
                'lat': final_lat,
                'lon': final_lon,
                'phone': str(row.get('P_ADMINTEL', '')) if str(row.get('P_ADMINTEL', '')).strip() else None,
                'website': None,
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'park_id': str(row.get('P_IDX', '')),
                    'park_type': str(row.get('P_PARK', '')),
                    'district': str(row.get('P_ZONE', '')),
                    'area': str(row.get('AREA', '')),
                    'open_date': str(row.get('OPEN_DT', '')),
                    'main_equip': str(row.get('MAIN_EQUIP', '')),
                    'main_plants': str(row.get('MAIN_PLANTS', '')),
                    'original_lat': original_lat,
                    'original_lon': original_lon
                },
                'data_source': 'openseoul'
            }
            normalizer.normalized_facilities.append(facility_data)
        
        print(f"\n✅ 공원 데이터 정규화 완료: {len(normalizer.normalized_facilities)}개")
        
        # 결과를 JSON 파일로 저장
        output_data = {
            "parks": normalizer.normalized_facilities,
            "metadata": {
                "normalized_at": datetime.now().isoformat(),
                "total_parks": len(normalizer.normalized_facilities),
                "source_file": str(park_file),
                "description": "공원 데이터 노말라이징 테스트 결과 (상위 15개)",
                "data_source": "openseoul"
            }
        }
        
        # 출력 파일 경로 (test 디렉토리 내)
        output_file = Path("backend/services/data_collection/curated/test/park_normalize_15.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # JSON 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 결과 저장 완료: {output_file}")
        
        # 통계 출력
        with_coords = sum(1 for p in normalizer.normalized_facilities if p.get('lat') is not None and p.get('lon') is not None)
        without_coords = len(normalizer.normalized_facilities) - with_coords
        
        print(f"\n📊 공원 데이터 통계:")
        print(f"   - 전체 공원 수: {len(normalizer.normalized_facilities)}")
        print(f"   - 좌표 있는 공원: {with_coords}")
        print(f"   - 좌표 없는 공원: {without_coords}")
        print(f"   - 좌표 정확도: {(with_coords/len(normalizer.normalized_facilities)*100):.1f}%")
        
        # 좌표가 있는 공원들의 예시 출력
        if with_coords > 0:
            print(f"\n✅ 좌표가 있는 공원 예시:")
            for park in normalizer.normalized_facilities[:5]:  # 상위 5개만 출력
                if park.get('lat') is not None and park.get('lon') is not None:
                    coord_source = "변환된 좌표" if park['facility_extra'].get('original_lat') != park['lat'] else "원본 좌표"
                    print(f"   - {park['name']}: lat={park['lat']}, lon={park['lon']} ({coord_source})")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 공원 데이터 정규화 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result_file = test_park_normalize_15()
    if result_file:
        print(f"\n🎉 테스트 완료! 결과 파일: {result_file}")
    else:
        print(f"\n❌ 테스트 실패!")
