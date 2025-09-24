#!/usr/bin/env python3
"""
대학 데이터 노말라이징 테스트 (상위 15개)
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

def test_college_normalize_15():
    """대학 데이터 노말라이징 테스트 (상위 15개)"""
    
    print("🎓 대학 데이터 노말라이징 테스트 시작 (상위 15개)")
    
    # 데이터 디렉토리 설정
    data_dir = Path("backend/data/public-api/openseoul")
    
    # InfraNormalizer 인스턴스 생성
    normalizer = InfraNormalizer(data_dir)
    
    # 대학 데이터 파일 확인
    college_file = data_dir / "seoul_SebcCollegeInfoKor_20250919.csv"
    
    if not college_file.exists():
        print(f"❌ 대학 데이터 파일이 존재하지 않습니다: {college_file}")
        return
    
    print(f"📁 대학 데이터 파일: {college_file}")
    
    try:
        # 대학 데이터 읽기
        df = read_csv_with_auto_encoding(college_file)
        print(f"📊 전체 대학 데이터: {len(df)}개")
        
        # 상위 15개만 처리
        limited_df = df.head(15)
        print(f"🎯 처리할 대학 데이터: {len(limited_df)}개")
        
        # 기존 normalized_facilities 초기화
        normalizer.normalized_facilities = []
        
        # 대학 데이터 정규화
        for _, row in limited_df.iterrows():
            address_raw = str(row.get('ADD_KOR', ''))
            facility_name = str(row.get('NAME_KOR', ''))
            
            print(f"\n🏢 처리 중: {facility_name}")
            print(f"📍 주소: {address_raw}")
            
            # InfraNormalizer의 _normalize_address 함수 사용
            address_info = normalizer._normalize_address(address_raw, facility_name, 'college')
            
            # 대학 데이터 구조 생성
            facility_data = {
                'facility_id': normalizer._generate_facility_id('college'),
                'cd': normalizer._get_facility_cd('college'),
                'name': facility_name,
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': str(row.get('TEL', '')),
                'website': str(row.get('HP', '')),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'college_id': str(row.get('MAIN_KEY', '')),
                    'college_type': str(row.get('CATE1_NAME', '')),
                    'district': str(row.get('H_KOR_GU', '')),
                    'branch': str(row.get('BRANCH', '')),
                    'state': str(row.get('STATE', '')),
                    'type': str(row.get('TYPE', ''))
                },
                'data_source': 'openseoul'
            }
            normalizer.normalized_facilities.append(facility_data)
        
        print(f"\n✅ 대학 데이터 정규화 완료: {len(normalizer.normalized_facilities)}개")
        
        # 결과를 JSON 파일로 저장
        output_data = {
            "colleges": normalizer.normalized_facilities,
            "metadata": {
                "normalized_at": datetime.now().isoformat(),
                "total_colleges": len(normalizer.normalized_facilities),
                "source_file": str(college_file),
                "description": "대학 데이터 노말라이징 테스트 결과 (상위 15개)",
                "data_source": "openseoul"
            }
        }
        
        # 출력 파일 경로 (test 디렉토리 내)
        output_file = Path("backend/services/data_collection/curated/test/college_normalize_15.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # JSON 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 결과 저장 완료: {output_file}")
        
        # 통계 출력
        with_coords = sum(1 for c in normalizer.normalized_facilities if c.get('lat') is not None and c.get('lon') is not None)
        without_coords = len(normalizer.normalized_facilities) - with_coords
        
        print(f"\n📊 대학 데이터 통계:")
        print(f"   - 전체 대학 수: {len(normalizer.normalized_facilities)}")
        print(f"   - 좌표 있는 대학: {with_coords}")
        print(f"   - 좌표 없는 대학: {without_coords}")
        print(f"   - 좌표 정확도: {(with_coords/len(normalizer.normalized_facilities)*100):.1f}%")
        
        # 좌표가 있는 대학들의 예시 출력
        if with_coords > 0:
            print(f"\n✅ 좌표가 있는 대학 예시:")
            for college in normalizer.normalized_facilities[:5]:  # 상위 5개만 출력
                if college.get('lat') is not None and college.get('lon') is not None:
                    print(f"   - {college['name']}: lat={college['lat']}, lon={college['lon']}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 대학 데이터 정규화 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result_file = test_college_normalize_15()
    if result_file:
        print(f"\n🎉 테스트 완료! 결과 파일: {result_file}")
    else:
        print(f"\n❌ 테스트 실패!")
