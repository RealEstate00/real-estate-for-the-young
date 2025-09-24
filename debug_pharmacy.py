import sys
from pathlib import Path
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
project_root = Path('.').resolve()
sys.path.insert(0, str(project_root))

from backend.services.data_collection.curated.infra_normalizer import InfraNormalizer

def debug_pharmacy_duplication():
    print("=== 약국 데이터 중복 디버깅 ===")
    
    # 테스트용 normalizer 생성
    data_dir = Path('backend/data/public-api/openseoul')
    normalizer = InfraNormalizer(data_dir)
    
    # 약국 파일 직접 처리
    pharmacy_file = data_dir / 'seoul_TbPharmacyOperateInfo_20250919.csv'
    df = pd.read_csv(pharmacy_file, encoding='utf-8')
    df_limited = df.head(10)
    
    print(f"처리할 데이터 수: {len(df_limited)}")
    
    # normalizer의 normalized_facilities 초기화
    normalizer.normalized_facilities = []
    
    # 개별 행 처리
    facilities = []
    for idx, row in df_limited.iterrows():
        if row['DUTYNAME'] == '1층엔약국':
            print(f"1층엔약국 처리 중: 행 {idx}")
        
        address_raw = str(row.get('DUTYADDR', ''))
        facility_name = str(row.get('DUTYNAME', ''))
        facility_type = 'pharmacy'
        
        # 주소 정규화 (로그 출력 최소화)
        address_info = normalizer._normalize_address(address_raw, facility_name, facility_type)
        
        # 시설 데이터 구성
        facility_data = {
            'facility_id': normalizer._generate_facility_id(facility_type),
            'cd': normalizer._get_facility_cd(facility_type),
            'name': facility_name,
            'address_raw': address_info.get('address_raw', address_raw),
            'address_nm': address_info.get('address_nm'),
            'address_id': address_info.get('address_id'),
            'lat': address_info.get('lat') or normalizer._safe_float(row.get('WGS84LAT')),
            'lon': normalizer._safe_float(row.get('WGS84LON')),
        }
        
        facilities.append(facility_data)
    
    print(f"\n=== 결과 ===")
    print(f"처리된 시설 수: {len(facilities)}")
    print(f"1층엔약국 개수: {len([f for f in facilities if f['name'] == '1층엔약국'])}")
    print(f"normalized_facilities 개수: {len(normalizer.normalized_facilities)}")
    
    # 1층엔약국의 facility_id들 확인
    pharmacy_entries = [f for f in facilities if f['name'] == '1층엔약국']
    if pharmacy_entries:
        print("1층엔약국의 facility_id들:")
        for i, entry in enumerate(pharmacy_entries[:5]):
            print(f"  {i+1}: {entry['facility_id']}")
    
    # 모든 약국의 facility_id 확인
    all_pharmacy_ids = [f['facility_id'] for f in facilities if f['name']]
    print(f"\n모든 약국 facility_id들:")
    for i, fid in enumerate(all_pharmacy_ids):
        print(f"  {i+1}: {fid}")

if __name__ == "__main__":
    debug_pharmacy_duplication()

