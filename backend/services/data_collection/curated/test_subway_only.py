#!/usr/bin/env python3
"""
지하철역만 정규화하는 테스트 파일 - InfraNormalizer 함수 직접 사용
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.curated.infra_normalizer import InfraNormalizer

def test_subway_only():
    """지하철역 데이터만 정규화 테스트"""
    import logging
    logging.basicConfig(level=logging.INFO)

    print("🚇 지하철역 정규화 테스트 시작")
    
    # 데이터 디렉토리 설정
    data_dir = Path("backend/data/public-api/openseoul")
    
    # InfraNormalizer 인스턴스 생성
    normalizer = InfraNormalizer(data_dir)
    
    # 지하철역 데이터 파일 경로
    subway_file = data_dir / "seoul_SearchSTNBySubwayLineInfo_20250919.csv"
    
    if not subway_file.exists():
        print(f"❌ 지하철역 파일이 존재하지 않습니다: {subway_file}")
        return
    
    print(f"📁 지하철역 파일 로드: {subway_file}")
    
    # InfraNormalizer의 _normalize_subway_stations 함수 직접 호출
    print("\n🔄 지하철역 데이터 정규화 시작...")
    normalizer._normalize_subway_stations(subway_file)
    
    # 결과 출력
    stations = normalizer.normalized_subway_stations
    print(f"\n📊 정규화 결과:")
    print(f"   - 성공: {len(stations)}개")
    
    # 처음 10개만 테스트용으로 사용
    test_stations = stations
    print(f"🧪 테스트용 지하철역 데이터: {len(test_stations)}개")
    
    # JSON 파일로 저장
    output_dir = Path("backend/data/normalized/test_subway")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # subway_stations.json 저장
    stations_file = output_dir / "subway_stations.json"
    
    # 메타데이터와 함께 저장
    stations_data = {
        "subway_stations": test_stations,
        "metadata": {
            "normalized_at": datetime.now().isoformat(),
            "stations_count": len(test_stations),
            "data_source": "seoul_subway"
        }
    }
    
    with open(stations_file, 'w', encoding='utf-8') as f:
        json.dump(stations_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 지하철역 데이터 저장: {stations_file}")
    
    # 메타데이터 저장
    metadata = {
        "total_stations": len(test_stations),
        "normalization_date": datetime.now().isoformat(),
        "data_source": "seoul_subway",
        "facility_type": "지하철역"
    }
    
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"📋 메타데이터 저장: {metadata_file}")
    
    # 성공한 데이터 샘플 출력
    if test_stations:
        print(f"\n🎯 성공한 데이터 샘플 (첫 번째):")
        sample = test_stations[0]
        print(f"   - 역명: {sample['station_name']}")
        print(f"   - 노선: {sample['line_name']}")
        print(f"   - 주소: {sample['address_raw']}")
        print(f"   - 환승여부: {sample['is_transfer']}")
        if sample['is_transfer']:
            print(f"   - 환승노선: {sample['transfer_lines']}")
        print(f"   - 역코드: {sample['station_code']}")
        print(f"   - 영문명: {sample['station_extra']['station_name_eng']}")
    
    # 환승역 통계
    transfer_count = sum(1 for station in test_stations if station['is_transfer'])
    print(f"\n📈 환승역 통계:")
    print(f"   - 일반역: {len(test_stations) - transfer_count}개")
    print(f"   - 환승역: {transfer_count}개")
    
    print(f"\n✅ 지하철역 테스트 완료! 결과는 {output_dir}에 저장되었습니다.")

if __name__ == "__main__":
    test_subway_only()
