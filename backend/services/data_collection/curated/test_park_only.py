#!/usr/bin/env python3
"""
공원 데이터만 정규화하는 테스트 파일 - InfraNormalizer 함수 직접 사용
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.curated.infra_normalizer import InfraNormalizer

def test_park_only():
    """공원 데이터만 정규화 테스트"""

    print("🌳 공원 정규화 테스트 시작")

    # 데이터 디렉토리 설정
    data_dir = Path("backend/data/public-api/openseoul")

    # InfraNormalizer 인스턴스 생성
    normalizer = InfraNormalizer(data_dir)

    # 공원 데이터 파일 경로
    park_file = data_dir / "seoul_SearchParkInfoService_20250919.csv"

    if not park_file.exists():
        print(f"❌ 공원 파일이 존재하지 않습니다: {park_file}")
        return

    print(f"📁 공원 파일 로드: {park_file}")

    # normalized_facilities 리스트 초기화 (다른 데이터와 섞이지 않도록)
    normalizer.normalized_facilities = []

    # InfraNormalizer의 _normalize_parks 함수 직접 호출
    print("\n🔄 공원 데이터 정규화 시작...")
    normalizer._normalize_parks(park_file)

    # 결과 출력
    parks = normalizer.normalized_facilities
    print(f"\n📊 정규화 결과:")
    print(f"   - 성공: {len(parks)}개")

    # 처음 10개만 테스트용으로 사용
    test_parks = parks
    print(f"🧪 테스트용 공원 데이터: {len(test_parks)}개")

    # JSON 파일로 저장
    output_dir = Path("backend/data/normalized/test_park")
    output_dir.mkdir(parents=True, exist_ok=True)

    # parks.json 저장
    parks_file = output_dir / "parks.json"

    # 메타데이터와 함께 저장
    parks_data = {
        "parks": test_parks,
        "metadata": {
            "normalized_at": datetime.now().isoformat(),
            "parks_count": len(test_parks),
            "data_source": "seoul_park"
        }
    }

    with open(parks_file, 'w', encoding='utf-8') as f:
        json.dump(parks_data, f, ensure_ascii=False, indent=2)

    print(f"💾 공원 데이터 저장: {parks_file}")

    # 메타데이터 저장
    metadata = {
        "total_parks": len(test_parks),
        "normalization_date": datetime.now().isoformat(),
        "data_source": "seoul_park",
        "facility_type": "공원"
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"📋 메타데이터 저장: {metadata_file}")

    # 성공한 데이터 샘플 출력
    if test_parks:
        print(f"\n🎯 성공한 데이터 샘플 (첫 번째):")
        sample = test_parks[0]
        print(f"   - 공원명: {sample['name']}")
        print(f"   - 주소: {sample['address_raw']}")
        print(f"   - 정규화 주소: {sample['address_norm']}")
        print(f"   - 시도: {sample['si_do']}")
        print(f"   - 구: {sample['si_gun_gu']}")
        print(f"   - 동: {sample['si_gun_gu_dong']}")
        print(f"   - 모든 동: {sample['facility_extra'].get('all_dongs', [])}")
        print(f"   - 위도: {sample['lat']}")
        print(f"   - 경도: {sample['lon']}")
        print(f"   - 면적: {sample['facility_extra'].get('area', 'N/A')}")

    # 주소 정규화 통계
    success_address = sum(1 for park in test_parks if park['address_norm'])
    print(f"\n📈 주소 정규화 통계:")
    print(f"   - 정규화 성공: {success_address}개")
    print(f"   - 정규화 실패: {len(test_parks) - success_address}개")

    # 시도별 통계
    sido_stats = {}
    for park in test_parks:
        sido = park.get('si_do', 'Unknown')
        if sido is None:
            sido = 'Unknown'
        sido_stats[sido] = sido_stats.get(sido, 0) + 1
    
    print(f"\n🏛️ 시도별 통계:")
    for sido, count in sorted(sido_stats.items()):
        print(f"   - {sido}: {count}개")

    # 여러 동이 있는 공원 통계
    multi_dong_parks = []
    for park in test_parks:
        all_dongs = park['facility_extra'].get('all_dongs', [])
        if len(all_dongs) > 1:
            multi_dong_parks.append({
                'name': park['name'],
                'address_raw': park['address_raw'],
                'dongs': all_dongs
            })
    
    print(f"\n🏘️ 여러 동이 있는 공원 ({len(multi_dong_parks)}개):")
    for park in multi_dong_parks[:5]:  # 처음 5개만 표시
        print(f"   - {park['name']}: {park['dongs']}")
        print(f"     주소: {park['address_raw']}")
    
    if len(multi_dong_parks) > 5:
        print(f"   ... 외 {len(multi_dong_parks) - 5}개")

    print(f"\n✅ 공원 테스트 완료! 결과는 {output_dir}에 저장되었습니다.")

if __name__ == "__main__":
    test_park_only()
