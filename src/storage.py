"""
storage.py - 데이터 저장 및 관리 모듈

🎯 이 파일의 역할:
- 크롤링한 딕셔너리 리스트를 CSV 파일로 저장
- 중복 데이터 제거 및 병합
- 데이터 검증 및 정리

💡 왜 딕셔너리 리스트를 사용하나요?
1. pandas가 바로 인식 가능
2. 컬럼명(키)과 데이터(값)가 명확히 구분
3. 누락된 필드 자동 처리
4. 코드 가독성과 유지보수성 향상
"""

import pandas as pd
import os
from typing import List, Dict, Any
from datetime import datetime


def save_to_csv(data: List[Dict[str, Any]], filename: str, data_dir: str = "data/raw") -> bool:
    """
    🚀 딕셔너리 리스트를 CSV 파일로 저장하는 함수
    
    📋 처리 과정:
    1. 딕셔너리 리스트 → pandas DataFrame 변환
    2. 데이터 검증 및 정리
    3. CSV 파일로 저장
    4. 성공/실패 여부 반환
    
    📖 사용 예시:
    data = [
        {"주택명": "오늘공동체주택", "지역": "도봉구", "가격": "1000만원"},
        {"주택명": "청년주택ABC", "지역": "강남구", "가격": "1500만원"}
    ]
    save_to_csv(data, "housing_list.csv")
    
    💾 저장되는 CSV 형태:
    주택명,지역,가격
    오늘공동체주택,도봉구,1000만원
    청년주택ABC,강남구,1500만원
    """
    
    try:
        print(f"💾 '{filename}' 파일로 저장 시작...")
        
        # 1. 데이터 검증
        if not data:
            print("❌ 저장할 데이터가 없습니다.")
            return False
        
        if not isinstance(data, list):
            print("❌ 데이터가 리스트 형태가 아닙니다.")
            return False
            
        if not all(isinstance(item, dict) for item in data):
            print("❌ 데이터가 딕셔너리 리스트 형태가 아닙니다.")
            return False
        
        print(f"✅ {len(data)}개의 레코드 검증 완료")
        
        # 2. 딕셔너리 리스트 → pandas DataFrame 변환
        # 🎯 핵심: 이 한 줄로 딕셔너리 리스트가 표 형태로 변환됨!
        df = pd.DataFrame(data)
        
        print(f"📊 DataFrame 생성 완료: {df.shape[0]}행 × {df.shape[1]}열")
        print(f"📋 컬럼: {list(df.columns)}")
        
        # 3. 데이터 정리
        # 빈 문자열을 NaN으로 변경 후 다시 빈 문자열로 (pandas 처리 일관성)
        df = df.fillna("")
        
        # 4. 저장 디렉토리 생성
        os.makedirs(data_dir, exist_ok=True)
        filepath = os.path.join(data_dir, filename)
        
        # 5. CSV 파일로 저장
        # encoding='utf-8-sig': 한글 깨짐 방지 (Excel에서도 정상 표시)
        # index=False: 행 번호 제외하고 저장
        df.to_csv(filepath, encoding='utf-8-sig', index=False)
        
        print(f"🎉 저장 완료: {filepath}")
        print(f"📁 파일 크기: {os.path.getsize(filepath)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
        return False


def load_from_csv(filename: str, data_dir: str = "data/raw") -> List[Dict[str, Any]]:
    """
    📂 CSV 파일을 딕셔너리 리스트로 불러오는 함수
    
    📖 사용 예시:
    data = load_from_csv("housing_list.csv")
    # 결과: [{"주택명": "오늘공동체주택", "지역": "도봉구", ...}, ...]
    """
    
    try:
        filepath = os.path.join(data_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"❌ 파일이 존재하지 않습니다: {filepath}")
            return []
        
        print(f"📂 '{filename}' 파일 로딩 중...")
        
        # CSV → DataFrame → 딕셔너리 리스트 변환
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        data = df.to_dict('records')  # 🎯 핵심: DataFrame을 딕셔너리 리스트로 변환
        
        print(f"✅ {len(data)}개 레코드 로딩 완료")
        return data
        
    except Exception as e:
        print(f"❌ 로딩 중 오류 발생: {e}")
        return []


def merge_data(new_data: List[Dict[str, Any]], existing_file: str, 
               key_field: str = "주택명", data_dir: str = "data/raw") -> List[Dict[str, Any]]:
    """
    🔄 새 데이터와 기존 데이터를 병합하는 함수 (중복 제거)
    
    📋 처리 과정:
    1. 기존 CSV 파일 로드
    2. 새 데이터와 병합
    3. key_field 기준으로 중복 제거
    4. 병합된 데이터 반환
    
    📖 사용 예시:
    new_data = [{"주택명": "신규주택", "지역": "서초구"}]
    merged = merge_data(new_data, "housing_list.csv", key_field="주택명")
    """
    
    try:
        print(f"🔄 데이터 병합 시작...")
        
        # 1. 기존 데이터 로드
        existing_data = load_from_csv(existing_file, data_dir)
        
        # 2. 새 데이터와 기존 데이터 합치기
        all_data = existing_data + new_data
        
        if not all_data:
            print("❌ 병합할 데이터가 없습니다.")
            return []
        
        # 3. DataFrame으로 변환 후 중복 제거
        df = pd.DataFrame(all_data)
        
        # key_field 기준으로 중복 제거 (마지막 값 유지)
        df_unique = df.drop_duplicates(subset=[key_field], keep='last')
        
        # 4. 다시 딕셔너리 리스트로 변환
        merged_data = df_unique.to_dict('records')
        
        print(f"✅ 병합 완료: {len(existing_data)} + {len(new_data)} → {len(merged_data)}개")
        print(f"🗑️ 중복 제거: {len(all_data) - len(merged_data)}개")
        
        return merged_data
        
    except Exception as e:
        print(f"❌ 병합 중 오류 발생: {e}")
        return new_data  # 실패시 새 데이터만 반환


def add_timestamp(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    🕒 데이터에 수집 시간 추가하는 함수
    
    📖 사용 예시:
    data = [{"주택명": "오늘공동체주택"}]
    timestamped = add_timestamp(data)
    # 결과: [{"주택명": "오늘공동체주택", "수집일시": "2025-01-20 14:30:00"}]
    """
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for item in data:
        item["수집일시"] = current_time
    
    print(f"🕒 {len(data)}개 레코드에 타임스탬프 추가: {current_time}")
    return data


# 💡 딕셔너리 리스트 vs 다른 형태 비교 예시:
"""
🎯 왜 딕셔너리 리스트가 좋은가?

1️⃣ 딕셔너리 리스트 (✅ 권장):
data = [
    {"주택명": "오늘공동체주택", "지역": "도봉구", "가격": "1000만원"},
    {"주택명": "청년주택ABC", "지역": "강남구", "가격": "1500만원"}
]

pandas 변환:
df = pd.DataFrame(data)  # 한 줄로 끝!

CSV 저장:
df.to_csv("result.csv")  # 자동으로 헤더 포함

결과 CSV:
주택명,지역,가격
오늘공동체주택,도봉구,1000만원
청년주택ABC,강남구,1500만원

2️⃣ 리스트의 리스트 (❌ 비추천):
data = [
    ["오늘공동체주택", "도봉구", "1000만원"],
    ["청년주택ABC", "강남구", "1500만원"]
]

pandas 변환:
df = pd.DataFrame(data, columns=["주택명", "지역", "가격"])  # 컬럼명 따로 지정 필요
# 컬럼 순서 바뀌면 데이터 엉킴!

3️⃣ 단일 딕셔너리 (❌ 잘못된 구조):
data = {"주택명": ["오늘공동체주택", "청년주택ABC"], "지역": ["도봉구", "강남구"]}
# 복잡하고 실수하기 쉬움

🏆 결론: 딕셔너리 리스트가 최고!
- 가독성 ⭐⭐⭐⭐⭐
- 유지보수성 ⭐⭐⭐⭐⭐  
- pandas 호환성 ⭐⭐⭐⭐⭐
- 에러 발생 가능성 ⭐ (낮음)
"""