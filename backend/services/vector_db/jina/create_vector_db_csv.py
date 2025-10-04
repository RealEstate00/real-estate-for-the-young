import json
import pandas as pd
import re
from pathlib import Path
from collections import defaultdict

def remove_number_chunks(text):
    """숫자가 포함된 덩어리를 제거 (주소 제외)"""
    if pd.isna(text) or text == "":
        return text
    
    # 공백, 쉼표, 줄바꿈으로 구분된 단위에서 숫자가 포함되면 전체 제거
    words = re.split(r'[\s,\n]+', str(text))
    cleaned_words = [word for word in words if not re.search(r'\d', word)]
    
    return ' '.join(cleaned_words).strip()

def load_housing_data(data_dir):
    """하나의 주택 디렉토리에서 데이터 로드"""
    notices_path = data_dir / "notices.json"
    addresses_path = data_dir / "addresses.json"
    tags_path = data_dir / "notice_tags.json"
    
    # 파일이 존재하는지 확인
    if not all([notices_path.exists(), addresses_path.exists(), tags_path.exists()]):
        print(f"⚠️  {data_dir.name}: 필수 파일이 없습니다. 스킵합니다.")
        return None, None, None
    
    with open(notices_path, 'r', encoding='utf-8') as f:
        notices = json.load(f)
    
    with open(addresses_path, 'r', encoding='utf-8') as f:
        addresses = json.load(f)
    
    with open(tags_path, 'r', encoding='utf-8') as f:
        tags = json.load(f)
    
    print(f"✓ {data_dir.name}: 공고 {len(notices)}개, 주소 {len(addresses)}개, 태그 {len(tags)}개")
    
    return notices, addresses, tags

def process_housing_data(housing_dirs, output_path):
    """여러 주택 데이터를 처리하여 벡터DB용 CSV 생성"""
    
    all_notices = []
    all_addresses = []
    all_tags = []
    
    # 각 디렉토리에서 데이터 로드
    print("파일 로딩 중...")
    for data_dir in housing_dirs:
        notices, addresses, tags = load_housing_data(data_dir)
        if notices is not None:
            all_notices.extend(notices)
            all_addresses.extend(addresses)
            all_tags.extend(tags)
    
    print(f"\n통합 완료: 공고 {len(all_notices)}개, 주소 {len(all_addresses)}개, 태그 {len(all_tags)}개")
    
    # 주소 정보를 딕셔너리로 변환
    address_dict = {addr['id']: addr for addr in all_addresses}
    
    # 태그를 notice_id별로 그룹화
    tags_by_notice = defaultdict(dict)
    excluded_tags = {'버스'}  # 제외할 태그
    
    for tag in all_tags:
        notice_id = tag['notice_id']
        tag_type = tag['tag']
        description = tag['description']
        
        # 버스 정보는 제외
        if tag_type in excluded_tags:
            continue
        
        # 숫자가 포함된 덩어리 제거
        clean_desc = remove_number_chunks(description)
        
        if clean_desc and clean_desc.strip():
            tags_by_notice[notice_id][tag_type] = clean_desc
    
    # 모든 태그 타입 수집 (버스 제외)
    all_tag_types = set()
    for notice_tags in tags_by_notice.values():
        for tag_type in notice_tags.keys():
            if tag_type not in excluded_tags:
                all_tag_types.add(tag_type)
    
    print(f"태그 전처리 완료 (제외: {', '.join(excluded_tags)})")
    print(f"포함된 태그: {', '.join(sorted(all_tag_types))}")
    
    # 최종 데이터 리스트
    result_data = []
    
    for notice in all_notices:
        notice_id = notice['notice_id']
        address_id = notice['address_id']
        
        # 주소 정보 가져오기
        addr_info = address_dict.get(address_id, {})
        
        # 주소가 비어있으면 raw 주소 사용
        jibun_addr = addr_info.get('jibun_name_full', '')
        road_addr = addr_info.get('road_name_full', '')
        
        if not jibun_addr and not road_addr:
            jibun_addr = notice.get('address_raw', '')
            road_addr = notice.get('address_raw', '')
        
        # 태그 정보를 간단한 문자열로 변환 (key:value 형태)
        notice_tags = tags_by_notice.get(notice_id, {})
        if notice_tags:
            tags_str = ', '.join([f'{k}:{v}' for k, v in notice_tags.items()])
        else:
            tags_str = ''
        
        row = {
            '주택명': notice['title'],
            '지번주소': jibun_addr,
            '도로명주소': road_addr,
            '시군구': addr_info.get('sgg_nm', ''),
            '동명': addr_info.get('emd_nm', ''),
            '태그': tags_str
        }
        
        result_data.append(row)
    
    # DataFrame 생성
    df = pd.DataFrame(result_data)
    
    # CSV 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ CSV 파일 생성 완료: {output_path}")
    print(f"📊 총 {len(df)}개의 레코드")
    print(f"📋 컬럼: 주택명, 지번주소, 도로명주소, 시군구, 동명, 태그(JSON)")
    print(f"📋 태그 종류: {', '.join(sorted(all_tag_types))}")
    
    return df

if __name__ == "__main__":
    # 파일 경로 설정
    base_path = Path(__file__).parent.parent.parent.parent
    data_date = "2025-09-29"  # 날짜 폴더명
    
    # 처리할 주택 데이터 디렉토리들
    housing_base = base_path / "data" / "normalized" / "housing" / data_date
    housing_dirs = [
        housing_base / "cohouse",
        housing_base / "sohouse",
        # 추가하고 싶은 다른 디렉토리가 있으면 여기에 추가
    ]
    
    # 출력 파일 경로
    output_path = base_path / "data" / "vector_db" / "housing_vector_data.csv"
    
    # 데이터 처리 및 CSV 생성
    df = process_housing_data(housing_dirs, output_path)
    
    # 결과 미리보기
    print("\n📝 생성된 데이터 샘플 (첫 2행):")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(df.head(2).to_string())