"""
location.py (위치) - 서울시 사회주택 위치 정보 크롤링

🎯 이 파일의 역할:
- 위치 섹션에서 주소와 우편번호 추출
- HTML → dict 형태로 변환
- 지도와 함께 표시된 주소 정보 수집

💡 실제 HTML 구조 (개발자도구 확인):
<div class="lm_inner">
    <h3>오늘공동체주택</h3>
    <p>
        :before "서울 도봉구 도봉로191길 80 (도봉동 351-2) (도봉동 351-2)"
        <br>
        "01301" == $0
        <br>
    </p>
</div>
"""

from src.utils import to_soup, clean
import re

def parse_location(html: str, house_name: str) -> dict:
    """
    🗺️ 위치 섹션에서 주소와 우편번호를 추출하는 함수
    
    📋 처리 과정:
    1. 위치 섹션 찾기 (.lm_inner 또는 관련 영역)
    2. 주소 텍스트 추출
    3. <br> 태그로 구분된 우편번호 추출
    4. 텍스트 정리 및 구조화
    
    🎯 반환 형태: dict (단일 정보)
    """
    
    print(f"  🗺️ '{house_name}' 위치 정보 추출 중...")
    
    soup = to_soup(html)
    
    # 위치 섹션 찾기 (여러 선택자로 안전하게 탐색)
    location_selectors = [
        ".lm_inner",                          # lm_inner 클래스
        "div:has(h3:contains('공동체주택'))",   # 주택명이 포함된 h3가 있는 div
        ".location",                          # location 클래스
        "#detail4",                           # detail4 ID
        "article[id*='detail4']",             # detail4가 포함된 article
        ".detail:has(h2:contains('위치'))",    # 위치 제목이 있는 detail 섹션
    ]
    
    location_section = None
    for selector in location_selectors:
        try:
            location_section = soup.select_one(selector)
            if location_section:
                print(f"    📍 위치 섹션 발견: {selector}")
                break
        except Exception:
            continue
    
    if not location_section:
        print("    ⚠️ 위치 섹션을 찾을 수 없습니다.")
        return {
            "주택명": house_name,
            "주소": "",
            "우편번호": ""
        }
    
    # 주소 정보 추출
    address = ""
    postal_code = ""
    
    try:
        # p 태그에서 주소 정보 찾기
        p_tag = location_section.find("p")
        if p_tag:
            # p 태그의 전체 텍스트 가져오기
            full_text = p_tag.get_text(separator="\n").strip()
            print(f"    📝 위치 섹션 전체 텍스트: {repr(full_text)}")
            
            # 줄바꿈으로 분리
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # 주소 찾기 (서울로 시작하는 줄 또는 가장 긴 줄)
            for line in lines:
                if "서울" in line and len(line) > 10:  # 서울이 포함되고 충분히 긴 줄
                    address = clean(line)
                    print(f"    🏠 주소 발견: {address}")
                    break
            
            # 우편번호 찾기 (5자리 숫자)
            for line in lines:
                postal_match = re.search(r'\b(\d{5})\b', line)
                if postal_match:
                    postal_code = postal_match.group(1)
                    print(f"    📮 우편번호 발견: {postal_code}")
                    break
        
        # p 태그가 없으면 다른 방법으로 시도
        if not address:
            # 전체 섹션에서 주소 패턴 찾기
            section_text = location_section.get_text()
            
            # 서울 주소 패턴 찾기
            seoul_pattern = r'서울\s+[가-힣]+구\s+[가-힣\d\s\-()]+\d+'
            address_match = re.search(seoul_pattern, section_text)
            if address_match:
                address = clean(address_match.group(0))
                print(f"    🏠 주소 패턴 매칭: {address}")
            
            # 우편번호 패턴 찾기
            postal_match = re.search(r'\b(\d{5})\b', section_text)
            if postal_match:
                postal_code = postal_match.group(1)
                print(f"    📮 우편번호 패턴 매칭: {postal_code}")
        
        # h3 태그에서 주택명 확인 (검증용)
        h3_tag = location_section.find("h3")
        if h3_tag:
            h3_text = clean(h3_tag.get_text())
            print(f"    🏷️ 섹션 내 주택명: {h3_text}")
            
    except Exception as e:
        print(f"    ❌ 위치 정보 추출 실패: {e}")
    
    # 결과 구성
    location_data = {
        "주택명": house_name,
        "주소": address,
        "우편번호": postal_code
    }
    
    # 추출 결과 로그
    extracted_count = sum(1 for v in location_data.values() if v and str(v).strip())
    print(f"    ✅ 위치 정보 추출 완료: {extracted_count}/{len(location_data)}개 필드")
    
    return location_data


# 💡 사용 예시:
"""
🎯 함수 사용법:

# HTML 가져오기 (위치 탭 클릭 후)
html = driver.page_source

# 위치 정보 추출
location_data = parse_location(html, "오늘공동체주택")

# 결과 확인
print(location_data)
# {
#     "주택명": "오늘공동체주택",
#     "주소": "서울 도봉구 도봉로191길 80 (도봉동 351-2)",
#     "우편번호": "01301"
# }

🚨 안전장치:
- 위치 섹션이 없어도 빈 값으로 dict 반환 (오류 없음)
- 주소나 우편번호가 없어도 빈 문자열로 처리
- 여러 패턴으로 주소 정보 탐색
- 정규식으로 우편번호 안전하게 추출
- 텍스트 정리 및 공백 제거
"""
