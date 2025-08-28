"""
about.py (사업자소개) - 서울시 사회주택 사업자 정보 크롤링

🎯 이 파일의 역할:
- 사업자소개 섹션에서 업체 정보 추출
- HTML → dict 형태로 변환
- 상호, 대표자, 대표전화, 이메일 등 사업자 정보 수집

💡 실제 HTML 구조 (개발자도구 확인):
<article id="detail6" class="detail">
    <h2 class="subcont_tit4">사업자소개</h2>
    <ul class="flexbox-detail">
        <li>
            " "
        </li>
        <li class="textbox">
            <ul class="detail-list">
                <li class="dashline">
                    <p>
                        <strong>상호</strong> : "주택협동조합 오늘공동체"
                    </p>
                </li>
                <li class="dashline">
                    <p>
                        <strong>대표자</strong> : "석주리"
                    </p>
                </li>
                <li class="dashline">
                    <p>
                        <strong>대표전화</strong> : "010-3595-8114"
                    </p>
                </li>
            </ul>
        </li>
    </ul>
</article>
"""

from src.utils import to_soup, clean
from .overview import _extract_by_strong_label

def parse_about(html: str, house_name: str) -> dict:
    """
    🏢 사업자소개 섹션에서 업체 정보를 추출하는 함수
    
    📋 처리 과정:
    1. 사업자소개 섹션 찾기 (#detail6 또는 관련 영역)
    2. ul.detail-list 내 li.dashline 요소들 수집
    3. 각 li에서 <strong>라벨</strong> : 값 패턴 추출
    4. 상호, 대표자, 대표전화, 이메일 정보 분류
    
    🎯 반환 형태: dict (사업자 정보)
    """
    
    print(f"  🏢 '{house_name}' 사업자 정보 추출 중...")
    
    soup = to_soup(html)
    
    # 사업자소개 섹션 찾기 (여러 선택자로 안전하게 탐색)
    about_selectors = [
        "#detail6",                           # ID가 detail6인 섹션
        "article[id*='detail6']",             # detail6가 포함된 article
        ".detail:has(h2:contains('사업자소개'))", # 사업자소개 제목이 있는 detail 섹션
        "div:has(h2:contains('사업자소개'))",     # 사업자소개 제목이 있는 div
        "ul.flexbox-detail",                  # flexbox-detail 클래스 ul
        ".detail-list",                       # detail-list 클래스
    ]
    
    about_section = None
    for selector in about_selectors:
        try:
            about_section = soup.select_one(selector)
            if about_section:
                print(f"    📍 사업자소개 섹션 발견: {selector}")
                break
        except Exception:
            continue
    
    if not about_section:
        print("    ⚠️ 사업자소개 섹션을 찾을 수 없습니다.")
        return {
            "주택명": house_name,
            "상호": "",
            "대표자": "",
            "대표전화": "",
            "이메일": ""
        }
    
    # 사업자 정보 초기화
    business_info = {
        "주택명": house_name,
        "상호": "",
        "대표자": "",
        "대표전화": "",
        "이메일": ""
    }
    
    try:
        # overview.py의 _extract_by_strong_label 함수 활용
        business_info["상호"] = _extract_by_strong_label(soup, "상호")
        business_info["대표자"] = _extract_by_strong_label(soup, "대표자")
        business_info["대표전화"] = _extract_by_strong_label(soup, "대표전화")
        business_info["이메일"] = _extract_by_strong_label(soup, "이메일")
        
        # 추가적으로 다른 패턴도 시도 (이메일의 경우)
        if not business_info["이메일"]:
            # 이메일 패턴을 직접 찾기
            import re
            section_text = about_section.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, section_text)
            if email_match:
                business_info["이메일"] = email_match.group(0)
                print(f"    📧 이메일 패턴 매칭: {business_info['이메일']}")
        
        # 전화번호 패턴 보완 (대표전화가 없는 경우)
        if not business_info["대표전화"]:
            import re
            section_text = about_section.get_text()
            # 전화번호 패턴: 010-1234-5678, 02-123-4567 등
            phone_pattern = r'\b(?:010|02|031|032|033|041|042|043|044|051|052|053|054|055|061|062|063|064)-?\d{3,4}-?\d{4}\b'
            phone_match = re.search(phone_pattern, section_text)
            if phone_match:
                business_info["대표전화"] = phone_match.group(0)
                print(f"    ☎️ 전화번호 패턴 매칭: {business_info['대표전화']}")
        
        # 텍스트 정리
        for key in business_info:
            if key != "주택명" and business_info[key]:
                business_info[key] = clean(business_info[key])
                
    except Exception as e:
        print(f"    ❌ 사업자 정보 추출 실패: {e}")
    
    # 추출 결과 로그
    extracted_count = sum(1 for v in business_info.values() if v and str(v).strip())
    print(f"    ✅ 사업자 정보 추출 완료: {extracted_count}/{len(business_info)}개 필드")
    
    # 추출된 정보들 로그 출력
    for category, content in business_info.items():
        if content and category != "주택명":
            print(f"      - {category}: {content}")
    
    return business_info


# 💡 사용 예시:
"""
🎯 함수 사용법:

# HTML 가져오기 (사업자소개 탭 클릭 후)
html = driver.page_source

# 사업자 정보 추출
about_data = parse_about(html, "오늘공동체주택")

# 결과 확인
print(about_data)
# {
#     "주택명": "오늘공동체주택",
#     "상호": "주택협동조합 오늘공동체",
#     "대표자": "석주리",
#     "대표전화": "010-3595-8114",
#     "이메일": "today.coop@gmail.com"
# }

🚨 안전장치:
- 사업자소개 섹션이 없어도 빈 값으로 dict 반환 (오류 없음)
- 각 정보가 없어도 빈 문자열로 처리
- overview.py의 _extract_by_strong_label 함수 재사용
- 이메일/전화번호 정규식 패턴으로 보완 추출
- 텍스트 정리 및 공백 제거
- 각 필드 처리 실패시에도 다른 필드 계속 처리
"""
