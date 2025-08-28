"""
movein.py (입주현황) - 서울시 사회주택 입주현황 테이블 크롤링

🎯 이 파일의 역할:
- 입주현황 섹션에서 방별 상세 정보 추출
- HTML → list[dict] 형태로 변환 (방 개수만큼 행 생성)
- 주택마다 방 개수가 달라도 안전하게 처리

💡 실제 HTML 구조 (개발자도구 확인):
<article id="detail3" class="detail">
    <h2 class="subcont_tit4">입주현황</h2>
    <div class="tableWrap">
        <table class="boardTable">
            <caption>방이름, 입주타입, 면적, 보증금, 월임대료, 관리비, 층, 호, 입주가능일 표</caption>
            <thead>
                <tr>
                    <th scope="col">방이름</th>
                    <th scope="col">입주타입</th>
                    <th scope="col">면적</th>
                    <th scope="col">보증금</th>
                    <th scope="col">월임대료</th>
                    <th scope="col">관리비</th>
                    <th scope="col">층</th>
                    <th scope="col">호</th>
                    <th scope="col">입주가능일</th>
                    <th scope="col">입주가능</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>101호</td>
                    <td>개타</td>
                    <td>28.49m²</td>
                    <td>50,000,000원</td>
                    <td>320,000원</td>
                    <td>-</td>
                    <td>1</td>
                    <td>1</td>
                    <td>-</td>
                    <td>-</td>
                </tr>
                <!-- 주택마다 방 개수 다름 -->
            </tbody>
        </table>
    </div>
</article>
"""

from src.utils import to_soup, clean

def parse_movein(html: str, house_name: str) -> list[dict]:
    """
    🏠 입주현황 테이블에서 방별 정보를 추출하는 함수
    
    📋 처리 과정:
    1. 입주현황 섹션 찾기 (#detail3 또는 .detail 영역)
    2. boardTable 클래스 테이블 찾기
    3. tbody의 모든 tr 행 수집
    4. 각 행의 td 데이터 추출
    5. 컬럼 순서에 맞게 매핑
    
    🎯 반환 형태: list[dict] (방 개수만큼)
    """
    
    print(f"  🏠 '{house_name}' 입주현황 정보 추출 중...")
    
    soup = to_soup(html)
    movein_rows = []
    
    # 입주현황 섹션 찾기 (여러 선택자로 안전하게 탐색)
    movein_selectors = [
        "#detail3",                           # ID가 detail3인 섹션
        "article[id*='detail3']",             # detail3가 포함된 article
        ".detail:has(h2:contains('입주현황'))", # 입주현황 제목이 있는 detail 섹션
        "div:has(h2:contains('입주현황'))",     # 입주현황 제목이 있는 div
        ".tableWrap",                         # tableWrap 클래스 직접 찾기
    ]
    
    movein_section = None
    for selector in movein_selectors:
        try:
            movein_section = soup.select_one(selector)
            if movein_section:
                print(f"    📍 입주현황 섹션 발견: {selector}")
                break
        except Exception:
            continue
    
    if not movein_section:
        print("    ⚠️ 입주현황 섹션을 찾을 수 없습니다.")
        return movein_rows
    
    # 테이블 찾기 (여러 선택자로 안전하게)
    table_selectors = [
        ".boardTable",           # boardTable 클래스
        "table",                 # 일반 table 태그
        ".tableWrap table",      # tableWrap 안의 table
    ]
    
    table = None
    for selector in table_selectors:
        try:
            table = movein_section.select_one(selector)
            if table:
                print(f"    📍 입주현황 테이블 발견: {selector}")
                break
        except Exception:
            continue
    
    if not table:
        print("    ⚠️ 입주현황 테이블을 찾을 수 없습니다.")
        return movein_rows
    
    # 테이블 헤더 확인 (컬럼 순서 파악)
    headers = []
    thead = table.find("thead")
    if thead:
        header_cells = thead.find_all("th")
        headers = [clean(th.get_text()) for th in header_cells]
        print(f"    📋 테이블 컬럼: {headers}")
    
    # 테이블 본문 데이터 추출
    tbody = table.find("tbody")
    if not tbody:
        print("    ⚠️ 테이블 본문(tbody)을 찾을 수 없습니다.")
        return movein_rows
    
    rows = tbody.find_all("tr")
    if not rows:
        print("    ⚠️ 테이블 행(tr)을 찾을 수 없습니다.")
        return movein_rows
    
    print(f"    🔍 총 {len(rows)}개의 방 정보 발견")
    
    # 각 행(방) 정보 추출
    for idx, tr in enumerate(rows, 1):
        try:
            # 각 셀의 텍스트 추출
            tds = tr.find_all("td")
            if not tds:
                print(f"    ⚠️ {idx}번째 행: td 셀이 없음")
                continue
            
            # 텍스트 정리
            cell_data = [clean(td.get_text()) for td in tds]
            
            # 빈 행 건너뛰기
            if not any(cell_data):
                continue
            
            # 실제 컬럼 순서에 맞게 매핑 (개발자도구 확인 결과)
            room_data = {
                "주택명": house_name,
                "방이름": cell_data[0] if len(cell_data) > 0 else "",        # 101호, 201호 등
                "입주타입": cell_data[1] if len(cell_data) > 1 else "",      # 개타, 공유 등
                "면적": cell_data[2] if len(cell_data) > 2 else "",          # 28.49m²
                "보증금": cell_data[3] if len(cell_data) > 3 else "",        # 50,000,000원
                "월임대료": cell_data[4] if len(cell_data) > 4 else "",      # 320,000원
                "관리비": cell_data[5] if len(cell_data) > 5 else "",        # - 또는 금액
                "층": cell_data[6] if len(cell_data) > 6 else "",            # 1, 2, 3층
                "호": cell_data[7] if len(cell_data) > 7 else "",            # 1, 2, 3호
                "입주가능일": cell_data[8] if len(cell_data) > 8 else "",    # 날짜 또는 -
                "입주가능": cell_data[9] if len(cell_data) > 9 else "",      # 가능/불가능 또는 -
            }
            
            movein_rows.append(room_data)
            print(f"    ✅ {idx}번째 방 정보 추출 완료: {room_data['방이름']} ({room_data['면적']})")
            
        except Exception as e:
            print(f"    ❌ {idx}번째 방 정보 처리 실패: {e}")
            continue
    
    print(f"    🎉 입주현황 정보 추출 완료: {len(movein_rows)}개 방")
    return movein_rows


# 💡 사용 예시:
"""
🎯 함수 사용법:

# HTML 가져오기 (입주현황 탭 클릭 후)
html = driver.page_source

# 입주현황 정보 추출
movein_data = parse_movein(html, "오늘공동체주택")

# 결과 확인
print(movein_data)
# [
#     {
#         "주택명": "오늘공동체주택",
#         "방이름": "101호",
#         "입주타입": "개타",
#         "면적": "28.49m²",
#         "보증금": "50,000,000원",
#         "월임대료": "320,000원",
#         "관리비": "-",
#         "층": "1",
#         "호": "1",
#         "입주가능일": "-",
#         "입주가능": "-"
#     },
#     {
#         "주택명": "오늘공동체주택",
#         "방이름": "201호",
#         "입주타입": "개타",
#         "면적": "80.02m²",
#         "보증금": "50,000,000원",
#         "월임대료": "1,230,000원",
#         ...
#     }
# ]

🚨 안전장치:
- 입주현황 섹션이 없어도 빈 리스트 반환 (오류 없음)
- 테이블이 없어도 빈 리스트 반환
- 방 개수가 0개~100개여도 안전하게 처리
- 일부 셀이 비어있어도 빈 문자열로 처리
- 각 방 처리 실패시에도 다른 방 계속 처리
- 컬럼 수가 다르거나 누락되어도 안전하게 처리
"""
