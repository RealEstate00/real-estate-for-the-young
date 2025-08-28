"""
overview.py (상세소개) - 서울시 사회주택 상세페이지 크롤링

🎯 이 파일의 역할:
- 상세페이지의 기본 정보 섹션에서 데이터 추출
- HTML → dict(단일행) 형태로 변환
- 실제 HTML 구조: <strong>라벨</strong> : 값 형태

📋 수집하는 정보:
- 주택 ID, 주택명, 주소, 입주대상, 주거형태, 면적, 총인원 등

💡 실제 HTML 구조 (개발자도구 확인):
<li class="dashline">
    <p>
        <strong>주소</strong> : 서울 도봉구 도봉로191길 80 (도봉동 351-2)
        <strong>입주대상</strong> : 재직업종
        <strong>주거형태</strong> : 다세대주택
        <strong>면적</strong> : 전용 655.42㎡ / 공용 237.24㎡
        <strong>총 주거인원수 / 총실</strong> : 총 14명 / 총 6호 / 총 6실
        <strong>주택유형</strong> : 기타
    </p>
</li>
"""

from src.utils import to_soup, clean
import re

def _extract_by_strong_label(soup, label: str) -> str:
    """
    🔍 <strong>라벨</strong> : 값 패턴에서 값을 추출하는 함수
    
    📖 사용 예시:
    HTML: <strong>주소</strong> : 서울 도봉구 도봉로191길 80
    _extract_by_strong_label(soup, "주소") → "서울 도봉구 도봉로191길 80"
    
    💡 동작 원리:
    1. <strong>라벨</strong> 태그 찾기
    2. 해당 태그의 부모 요소에서 전체 텍스트 추출
    3. "라벨 : 값" 패턴에서 값 부분만 추출
    """
    try:
        # <strong>라벨</strong> 태그 찾기
        strong_tag = soup.find("strong", string=lambda x: x and label in x)
        if not strong_tag:
            return ""
        
        # 부모 요소의 전체 텍스트 가져오기
        parent_text = strong_tag.parent.get_text() if strong_tag.parent else ""
        
        # 정규식으로 "라벨 : 값" 패턴에서 값 추출
        # 예: "주소 : 서울 도봉구..." → "서울 도봉구..." 추출
        pattern = rf'{re.escape(label)}\s*:\s*([^강]*?)(?=\s*(?:<strong>|\s*$|다음\s+강))'
        match = re.search(pattern, parent_text)
        
        if match:
            value = match.group(1).strip()
            # 다음 <strong> 태그 이전까지만 추출
            next_strong_match = re.search(r'^(.*?)(?=\s*[가-힣]+\s*:)', value)
            if next_strong_match:
                value = next_strong_match.group(1).strip()
            return clean(value)
        
        return ""
        
    except Exception as e:
        print(f"⚠️ {label} 추출 실패: {e}")
        return ""

def _extract_area_info(soup) -> tuple:
    """
    📐 면적 정보를 전용/공용으로 분리해서 추출
    
    📖 예시:
    HTML: <strong>면적</strong> : 전용 655.42㎡ / 공용 237.24㎡
    반환: ("전용 655.42㎡", "공용 237.24㎡")
    """
    try:
        area_text = _extract_by_strong_label(soup, "면적")
        if not area_text:
            return "", ""
        
        # "전용 XXX㎡ / 공용 XXX㎡" 패턴에서 분리
        parts = area_text.split("/")
        if len(parts) >= 2:
            exclusive_area = clean(parts[0])  # 전용
            common_area = clean(parts[1])     # 공용
            return exclusive_area, common_area
        else:
            return clean(area_text), ""  # 전체 면적만 있는 경우
            
    except Exception as e:
        print(f"⚠️ 면적 정보 추출 실패: {e}")
        return "", ""

def _extract_capacity_info(soup) -> tuple:
    """
    👥 총 주거인원수/총실 정보 추출
    
    📖 예시:
    HTML: <strong>총 주거인원수 / 총실</strong> : 총 14명 / 총 6호 / 총 6실
    반환: ("총 14명", "총 6호", "총 6실")
    """
    try:
        capacity_text = _extract_by_strong_label(soup, "총 주거인원수")
        if not capacity_text:
            # 다른 패턴도 시도
            capacity_text = _extract_by_strong_label(soup, "총실")
        
        if not capacity_text:
            return "", "", ""
        
        # "총 14명 / 총 6호 / 총 6실" 패턴에서 분리
        parts = [clean(part) for part in capacity_text.split("/")]
        
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]  # 총인원, 총호, 총실
        elif len(parts) == 2:
            return parts[0], parts[1], ""        # 총인원, 총호
        elif len(parts) == 1:
            return parts[0], "", ""              # 총인원만
        else:
            return "", "", ""
            
    except Exception as e:
        print(f"⚠️ 인원 정보 추출 실패: {e}")
        return "", "", ""


def parse_overview(html: str, house_name: str) -> dict:
    """
    🚀 상세소개 섹션에서 모든 정보를 추출하는 메인 함수
    
    📋 추출하는 정보:
    - 기본 정보: 주택명, 주소, 입주대상, 주거형태, 주택유형
    - 면적 정보: 전용면적, 공용면적
    - 인원 정보: 총인원, 총호수, 총실수
    - 이미지: 메인 이미지 URL
    
    🎯 반환 형태: dict (CSV 저장용)
    """
    
    print(f"  📊 '{house_name}' 상세소개 정보 추출 중...")
    
    soup = to_soup(html)
    
    # 기본 정보 추출
    address = _extract_by_strong_label(soup, "주소")
    target = _extract_by_strong_label(soup, "입주대상")
    housing_type = _extract_by_strong_label(soup, "주거형태")
    house_category = _extract_by_strong_label(soup, "주택유형")
    
    # 면적 정보 추출
    exclusive_area, common_area = _extract_area_info(soup)
    
    # 인원 정보 추출
    total_people, total_units, total_rooms = _extract_capacity_info(soup)
    
    overview_data = {
        "주택명": house_name,                # 주택 이름
        "주소": address,                     # 전체 주소
        "입주대상": target,                  # 입주 대상 (예: "재직업종")
        "주거형태": housing_type,            # 주거 형태 (예: "다세대주택")
        "주택유형": house_category,          # 주택 유형 (예: "기타")
        "전용면적": exclusive_area,          # 전용 면적
        "공용면적": common_area,             # 공용 면적
        "총인원": total_people,             # 총 거주 인원
        "총호수": total_units,              # 총 호수
        "총실수": total_rooms               # 총 방 수
    }
    
    # 추출 결과 로그
    extracted_count = sum(1 for v in overview_data.values() if v and str(v).strip())
    print(f"    ✅ 상세소개 정보 추출 완료: {extracted_count}/{len(overview_data)}개 필드")
    
    return overview_data


# 💡 사용 예시:
"""
🎯 함수 사용법:

# HTML 가져오기
html = driver.page_source

# 상세소개 정보 추출
overview_data = parse_overview(html, "오늘공동체주택")

# 결과 확인
print(overview_data)
# {
#     "ID": "오늘공동체주택",
#     "주택명": "오늘공동체주택", 
#     "주소": "서울 도봉구 도봉로191길 80 (도봉동 351-2)",
#     "입주대상": "재직업종",
#     "주거형태": "다세대주택",
#     "주택유형": "기타",
#     "전용면적": "전용 655.42㎡",
#     "공용면적": "공용 237.24㎡",
#     "총인원": "총 14명",
#     "총호수": "총 6호", 
#     "총실수": "총 6실",
#     "메인이미지": "https://soco.seoul.go.kr/coHouse/cmmn/file/fileDown.do?..."
# }

🚨 주의사항:
- HTML 구조가 변경되면 _extract_by_strong_label 함수의 정규식 수정 필요
- 일부 주택은 정보가 누락될 수 있으므로 빈 문자열로 처리
- 이미지 URL은 상대경로를 절대경로로 변환하여 저장
"""
