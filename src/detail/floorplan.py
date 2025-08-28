"""
floorplan.py (평면도) - 서울시 사회주택 평면도 이미지 크롤링

🎯 이 파일의 역할:
- 평면도 섹션에서 모든 이미지 URL 추출
- HTML → list[dict] 형태로 변환
- 주택마다 이미지 개수가 달라도 안전하게 처리

💡 실제 HTML 구조 (개발자도구 확인):
<article id="detail2" class="detail">
    <h2 class="subcont_tit4">평면도</h2>
    <div class="detail-box">
        <img style="width: 100%; object-fit: contain;" 
             src="/coHouse/cmmn/file/fileDown.do?atchFileId=1f4e0b3...&fileSn=15" 
             alt="오늘공동체주택_평면도_1">
        <img style="width: 100%; object-fit: contain;" 
             src="/coHouse/cmmn/file/fileDown.do?atchFileId=1f4e0b3...&fileSn=17" 
             alt="오늘공동체주택_평면도_2">
        <!-- 주택마다 이미지 개수 다름 (1~10개 이상 가능) -->
    </div>
</article>
"""

from src.utils import to_soup, clean

def parse_floorplan(html: str, house_name: str) -> list[dict]:
    """
    🖼️ 평면도 섹션에서 모든 이미지를 추출하는 함수
    
    📋 처리 과정:
    1. 평면도 섹션 찾기 (#detail2 또는 .detail 영역)
    2. 섹션 내 모든 img 태그 수집
    3. 각 이미지의 src와 alt 정보 추출
    4. 상대경로를 절대경로로 변환
    5. 리스트 형태로 반환
    
    🎯 반환 형태: list[dict] (이미지 개수만큼)
    """
    
    print(f"  🖼️ '{house_name}' 평면도 이미지 추출 중...")
    
    soup = to_soup(html)
    floorplan_images = []
    
    # 평면도 섹션 찾기 (여러 선택자로 안전하게 탐색)
    floorplan_selectors = [
        "#detail2",                    # ID가 detail2인 섹션
        "article[id*='detail2']",      # detail2가 포함된 article
        ".detail:has(h2:contains('평면도'))",  # 평면도 제목이 있는 detail 섹션
        "div:has(h2:contains('평면도'))",      # 평면도 제목이 있는 div
        ".detail-box",                 # detail-box 클래스 직접 찾기
    ]
    
    floorplan_section = None
    for selector in floorplan_selectors:
        try:
            floorplan_section = soup.select_one(selector)
            if floorplan_section:
                print(f"    📍 평면도 섹션 발견: {selector}")
                break
        except Exception:
            continue
    
    if not floorplan_section:
        print("    ⚠️ 평면도 섹션을 찾을 수 없습니다.")
        return floorplan_images
    
    # 섹션 내 모든 이미지 찾기
    images = floorplan_section.find_all("img")
    
    if not images:
        print("    ⚠️ 평면도 이미지를 찾을 수 없습니다.")
        return floorplan_images
    
    print(f"    🔍 총 {len(images)}개의 평면도 이미지 발견")
    
    # 각 이미지 정보 추출
    for idx, img in enumerate(images, 1):
        try:
            # 이미지 URL 추출
            src = img.get("src", "").strip()
            if not src:
                print(f"    ⚠️ {idx}번째 이미지: src 속성 없음")
                continue
            
            # 상대경로를 절대경로로 변환
            if src.startswith("/"):
                absolute_url = "https://soco.seoul.go.kr" + src
            else:
                absolute_url = src
            
            # alt 텍스트 추출 (이미지 설명)
            alt_text = clean(img.get("alt", ""))
            if not alt_text:
                alt_text = f"{house_name}_평면도_{idx}"
            
            # 이미지 크기 정보 (있다면)
            style = img.get("style", "")
            width_info = ""
            if "width:" in style:
                import re
                width_match = re.search(r'width:\s*([^;]+)', style)
                if width_match:
                    width_info = width_match.group(1).strip()
            
            # 이미지 데이터 구성
            image_data = {
                "주택명": house_name,           # 주택 이름
                "이미지순서": idx,              # 이미지 순서 (1, 2, 3, ...)
                "이미지URL": absolute_url,      # 절대경로 이미지 URL
                "이미지설명": alt_text,         # alt 텍스트 또는 기본 설명
                "이미지크기": width_info,       # 스타일에서 추출한 크기 정보
            }
            
            floorplan_images.append(image_data)
            print(f"    ✅ {idx}번째 이미지 추출 완료: {alt_text}")
            
        except Exception as e:
            print(f"    ❌ {idx}번째 이미지 처리 실패: {e}")
            continue
    
    print(f"    🎉 평면도 이미지 추출 완료: {len(floorplan_images)}개")
    return floorplan_images


# 💡 사용 예시:
"""
🎯 함수 사용법:

# HTML 가져오기 (평면도 탭 클릭 후)
html = driver.page_source

# 평면도 이미지 추출
floorplan_data = parse_floorplan(html, "오늘공동체주택")

# 결과 확인
print(floorplan_data)
# [
#     {
#         "주택명": "오늘공동체주택",
#         "이미지순서": 1,
#         "이미지URL": "https://soco.seoul.go.kr/coHouse/cmmn/file/fileDown.do?...",
#         "이미지설명": "오늘공동체주택_평면도_1",
#         "이미지크기": "100%"
#     },
#     {
#         "주택명": "오늘공동체주택", 
#         "이미지순서": 2,
#         "이미지URL": "https://soco.seoul.go.kr/coHouse/cmmn/file/fileDown.do?...",
#         "이미지설명": "오늘공동체주택_평면도_2",
#         "이미지크기": "100%"
#     }
# ]

🚨 안전장치:
- 평면도 섹션이 없어도 빈 리스트 반환 (오류 없음)
- 이미지 개수가 0개~100개여도 안전하게 처리
- src 속성이 없는 이미지는 건너뜀
- 상대경로 자동 절대경로 변환
- 각 이미지 처리 실패시에도 다음 이미지 계속 처리
"""
