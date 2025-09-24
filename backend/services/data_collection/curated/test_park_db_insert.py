#!/usr/bin/env python3
"""
공원 데이터만 DB에 적재하는 테스트 파일
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import logging

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.curated.infra_normalizer import InfraNormalizer
from backend.db.db_utils_pg import get_engine
from sqlalchemy import text

def test_park_db_insert():
    """공원 데이터만 DB에 적재 테스트"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    print("🌳 공원 데이터 DB 적재 테스트 시작")

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

    if not parks:
        print("❌ 정규화된 공원 데이터가 없습니다.")
        return

    # DB 연결 및 적재
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            
            try:
                # 1. 기존 공원 데이터 삭제 (테스트용)
                print("\n🗑️ 기존 공원 데이터 삭제 중...")
                delete_result = conn.execute(text("""
                    DELETE FROM infra.facilities 
                    WHERE category_id = 4 AND data_source = 'openseoul'
                """))
                print(f"   - 삭제된 레코드: {delete_result.rowcount}개")
                
                # 2. 공원 데이터 삽입
                print("\n💾 공원 데이터 DB 적재 시작...")
                inserted_count = 0
                
                for i, park in enumerate(parks):
                    try:
                        # 시설 데이터 삽입
                        insert_facility = text("""
                            INSERT INTO infra.facilities (
                                category_id, name, address_raw, address_norm,
                                si_do, si_gun_gu, si_gun_gu_dong,
                                road_full, jibun_full,
                                lat, lon, phone, website,
                                operating_hours, is_24h, is_emergency,
                                capacity, grade_level, facility_extra,
                                data_source, geo_extra, created_at, updated_at
                            ) VALUES (
                                :category_id, :name, :address_raw, :address_norm,
                                :si_do, :si_gun_gu, :si_gun_gu_dong,
                                :road_full, :jibun_full,
                                :lat, :lon, :phone, :website,
                                :operating_hours, :is_24h, :is_emergency,
                                :capacity, :grade_level, :facility_extra,
                                :data_source, :geo_extra, NOW(), NOW()
                            )
                        """)
                        
                        conn.execute(insert_facility, {
                            'category_id': park['category_id'],
                            'name': park['name'],
                            'address_raw': park['address_raw'],
                            'address_norm': park['address_norm'],
                            'si_do': park['si_do'],
                            'si_gun_gu': park['si_gun_gu'],
                            'si_gun_gu_dong': park['si_gun_gu_dong'],
                            'road_full': park.get('road_full'),
                            'jibun_full': park.get('jibun_full'),
                            'lat': park['lat'],
                            'lon': park['lon'],
                            'phone': park['phone'],
                            'website': park['website'],
                            'operating_hours': park['operating_hours'],
                            'is_24h': park['is_24h'],
                            'is_emergency': park['is_emergency'],
                            'capacity': park['capacity'],
                            'grade_level': park['grade_level'],
                            'facility_extra': json.dumps(park['facility_extra'], ensure_ascii=False) if park['facility_extra'] else None,
                            'data_source': park['data_source'],
                            'geo_extra': json.dumps(park['geo_extra'], ensure_ascii=False) if park['geo_extra'] else None
                        })
                        
                        inserted_count += 1
                        
                        if (i + 1) % 10 == 0:
                            print(f"   - 진행률: {i + 1}/{len(parks)} ({((i + 1) / len(parks) * 100):.1f}%)")
                            
                    except Exception as e:
                        logger.error(f"공원 데이터 삽입 실패 [{i+1}]: {park['name']} - {e}")
                        continue
                
                # 트랜잭션 커밋
                trans.commit()
                print(f"\n✅ 공원 데이터 DB 적재 완료: {inserted_count}개")
                
                # 3. 삽입된 데이터 검증
                print("\n🔍 삽입된 데이터 검증 중...")
                verify_result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN road_full IS NOT NULL THEN 1 END) as road_full_count,
                        COUNT(CASE WHEN jibun_full IS NOT NULL THEN 1 END) as jibun_full_count,
                        COUNT(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 END) as geo_count
                    FROM infra.facilities 
                    WHERE category_id = 4 AND data_source = 'openseoul'
                """)).fetchone()
                
                print(f"   - 총 공원 수: {verify_result.total_count}개")
                print(f"   - 도로명주소 있는 공원: {verify_result.road_full_count}개")
                print(f"   - 지번주소 있는 공원: {verify_result.jibun_full_count}개")
                print(f"   - 좌표 있는 공원: {verify_result.geo_count}개")
                
                # 4. 샘플 데이터 조회
                print("\n📋 샘플 데이터 조회:")
                sample_result = conn.execute(text("""
                    SELECT name, address_raw, address_norm, si_do, si_gun_gu, si_gun_gu_dong,
                           road_full, jibun_full, lat, lon
                    FROM infra.facilities 
                    WHERE category_id = 4 AND data_source = 'openseoul'
                    LIMIT 3
                """)).fetchall()
                
                for i, row in enumerate(sample_result, 1):
                    print(f"\n   {i}. {row.name}")
                    print(f"      - 원본주소: {row.address_raw}")
                    print(f"      - 정규화주소: {row.address_norm}")
                    print(f"      - 시도: {row.si_do}")
                    print(f"      - 구: {row.si_gun_gu}")
                    print(f"      - 동: {row.si_gun_gu_dong}")
                    print(f"      - 도로명주소: {row.road_full}")
                    print(f"      - 지번주소: {row.jibun_full}")
                    print(f"      - 좌표: ({row.lat}, {row.lon})")
                
            except Exception as e:
                # 트랜잭션 롤백
                trans.rollback()
                logger.error(f"DB 적재 중 오류 발생: {e}")
                raise
                
    except Exception as e:
        logger.error(f"DB 연결 또는 적재 실패: {e}")
        return

    print(f"\n✅ 공원 데이터 DB 적재 테스트 완료!")

if __name__ == "__main__":
    test_park_db_insert()
