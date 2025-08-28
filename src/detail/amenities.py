"""
amenities.py (편의시설) - 서울시 사회주택 편의시설 정보 크롤링

🎯 이 파일의 역할:
- 편의시설 섹션에서 교통/생활시설 정보 추출
- HTML → dict 형태로 변환
- 아이콘과 함께 표시된 편의시설 목록 수집

💡 실제 HTML 구조 (개발자도구 확인):
<article id="detail5" class="detail">
    <h2 class="subcont_tit4">편의시설</h2>
    <ul class="flexbox w4 trans">
        <li>
            <li class="subway">
                :before
                <span class="hide">지하철</span>
                1호선 도봉산역
                7호선 도봉산역
            </li>
        </li>
        <li class="bus">
            :before
            <span class="hide">버스</span>
            140, 150, 160
        </li>
        <li class="flexbox facility">
            <li>
                :before
                <span class="hide">세븐일레븐 도봉산점</span>
                세븐일레븐 도봉산점
            </li>
        </li>
        <!-- 병원, 학교, 도봉초등학교, 감로다카페도서관, 유정원 등 -->
    </ul>
</article>
"""

from src.utils import to_soup, clean

def parse_amenities(html: str, house_name: str) -> dict:
    """
    🏪 편의시설 섹션에서 모든 시설 정보를 추출하는 함수
    
    📋 처리 과정:
    1. 편의시설 섹션 찾기 (#detail5 또는 관련 영역)
    2. ul.flexbox 내 모든 li 요소 수집
    3. 각 li의 클래스와 텍스트 내용 분석
    4. 시설 유형별로 분류하여 정보 추출
    
    🎯 반환 형태: dict (시설 유형별 정보)
    """
    
    print(f"  🏪 '{house_name}' 편의시설 정보 추출 중...")
    
    soup = to_soup(html)
    
    # 편의시설 섹션 찾기 (여러 선택자로 안전하게 탐색)
    amenities_selectors = [
        "#detail5",                           # ID가 detail5인 섹션
        "article[id*='detail5']",             # detail5가 포함된 article
        ".detail:has(h2:contains('편의시설'))", # 편의시설 제목이 있는 detail 섹션
        "div:has(h2:contains('편의시설'))",     # 편의시설 제목이 있는 div
        "ul.flexbox.w4.trans",                # flexbox 클래스가 있는 ul
        "ul.flexbox",                         # flexbox 클래스 ul
    ]
    
    amenities_section = None
    for selector in amenities_selectors:
        try:
            amenities_section = soup.select_one(selector)
            if amenities_section:
                print(f"    📍 편의시설 섹션 발견: {selector}")
                break
        except Exception:
            continue
    
    if not amenities_section:
        print("    ⚠️ 편의시설 섹션을 찾을 수 없습니다.")
        return {
            "주택명": house_name,
            "지하철": "",
            "버스": "",
            "마트": "",
            "병원": "",
            "학교": "",
            "카페": "",
            "기타시설": ""
        }
    
    # 편의시설 정보 초기화
    facilities = {
        "주택명": house_name,
        "지하철": "",
        "버스": "",
        "마트": "",
        "병원": "",
        "학교": "",
        "카페": "",
        "기타시설": ""
    }
    
    try:
        # ul 태그 내 모든 li 요소 찾기
        ul_tag = amenities_section.find("ul") if amenities_section.name != "ul" else amenities_section
        if not ul_tag:
            ul_tag = amenities_section  # 섹션 자체가 ul일 수도 있음
        
        li_elements = ul_tag.find_all("li", recursive=True) if ul_tag else []
        
        if not li_elements:
            print("    ⚠️ 편의시설 li 요소를 찾을 수 없습니다.")
            return facilities
        
        print(f"    🔍 총 {len(li_elements)}개의 편의시설 항목 발견")
        
        other_facilities = []  # 기타 시설들을 저장할 리스트
        
        # 각 li 요소 분석
        for idx, li in enumerate(li_elements, 1):
            try:
                # li의 클래스 확인
                li_class = " ".join(li.get("class", []))
                
                # li 내 텍스트 추출 (span.hide 제외하고)
                # span.hide는 화면에 보이지 않는 텍스트이므로 제외
                li_text = ""
                for content in li.contents:
                    if hasattr(content, 'name'):
                        if content.name == 'span' and 'hide' in content.get('class', []):
                            continue  # span.hide는 건너뛰기
                        li_text += content.get_text()
                    else:
                        li_text += str(content)
                
                li_text = clean(li_text).strip()
                
                if not li_text:
                    continue
                
                print(f"    📋 {idx}번째 시설: 클래스='{li_class}', 내용='{li_text}'")
                
                # 클래스 기반 시설 분류
                if "subway" in li_class or "지하철" in li_text:
                    if facilities["지하철"]:
                        facilities["지하철"] += f", {li_text}"
                    else:
                        facilities["지하철"] = li_text
                        
                elif "bus" in li_class or any(keyword in li_text for keyword in ["버스", "번"]) and any(char.isdigit() for char in li_text):
                    if facilities["버스"]:
                        facilities["버스"] += f", {li_text}"
                    else:
                        facilities["버스"] = li_text
                        
                elif any(keyword in li_text for keyword in ["마트", "편의점", "세븐일레븐", "CU", "GS25", "이마트"]):
                    if facilities["마트"]:
                        facilities["마트"] += f", {li_text}"
                    else:
                        facilities["마트"] = li_text
                        
                elif any(keyword in li_text for keyword in ["병원", "의원", "클리닉", "한의원"]):
                    if facilities["병원"]:
                        facilities["병원"] += f", {li_text}"
                    else:
                        facilities["병원"] = li_text
                        
                elif any(keyword in li_text for keyword in ["학교", "초등학교", "중학교", "고등학교", "대학교"]):
                    if facilities["학교"]:
                        facilities["학교"] += f", {li_text}"
                    else:
                        facilities["학교"] = li_text
                        
                elif any(keyword in li_text for keyword in ["카페", "커피", "스타벅스", "도서관"]):
                    if facilities["카페"]:
                        facilities["카페"] += f", {li_text}"
                    else:
                        facilities["카페"] = li_text
                        
                else:
                    # 기타 시설로 분류
                    other_facilities.append(li_text)
                    
            except Exception as e:
                print(f"    ❌ {idx}번째 시설 처리 실패: {e}")
                continue
        
        # 기타 시설들을 하나의 문자열로 합치기
        if other_facilities:
            facilities["기타시설"] = ", ".join(other_facilities)
            
    except Exception as e:
        print(f"    ❌ 편의시설 정보 추출 실패: {e}")
    
    # 추출 결과 로그
    extracted_count = sum(1 for v in facilities.values() if v and str(v).strip())
    print(f"    ✅ 편의시설 정보 추출 완료: {extracted_count}/{len(facilities)}개 필드")
    
    # 추출된 시설들 로그 출력
    for category, content in facilities.items():
        if content and category != "주택명":
            print(f"      - {category}: {content}")
    
    return facilities


# 💡 사용 예시:
"""
🎯 함수 사용법:

# HTML 가져오기 (편의시설 탭 클릭 후)
html = driver.page_source

# 편의시설 정보 추출
amenities_data = parse_amenities(html, "오늘공동체주택")

# 결과 확인
print(amenities_data)
# {
#     "주택명": "오늘공동체주택",
#     "지하철": "1호선 도봉산역, 7호선 도봉산역",
#     "버스": "140, 150, 160",
#     "마트": "세븐일레븐 도봉산점",
#     "병원": "",
#     "학교": "도봉초등학교",
#     "카페": "감로다카페도서관",
#     "기타시설": "유정원"
# }

🚨 안전장치:
- 편의시설 섹션이 없어도 빈 값으로 dict 반환 (오류 없음)
- li 요소가 없어도 빈 문자열로 처리
- span.hide 요소는 자동으로 제외 (화면에 보이지 않는 텍스트)
- 시설 분류 실패시 기타시설로 분류
- 각 시설 처리 실패시에도 다른 시설 계속 처리
- 동일 카테고리 여러 시설은 쉼표로 구분하여 연결
"""
