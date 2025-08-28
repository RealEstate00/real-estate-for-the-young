"""
config.py - 크롤러 설정 및 CSS 선택자 중앙 관리 파일

🎯 이 파일의 역할:
- 모든 설정값을 한 곳에서 관리 (URL, 대기시간, 경로 등)
- CSS 선택자를 중앙집중식으로 관리
- 사이트 구조가 바뀌면 이 파일만 수정하면 전체 코드가 자동으로 적용됨

💡 왜 config.py를 사용하나요?
1. 유지보수성: 설정 변경시 한 파일만 수정
2. 가독성: 설정과 로직 분리로 코드 이해 쉬움
3. 재사용성: 다른 사이트 크롤링시 이 파일만 교체
4. 협업: 개발자마다 다른 설정 사용 가능

🔧 사용법:
from src.config import BASE_URL, SEL_LIST_ITEM
driver.get(BASE_URL)
items = driver.find_elements(By.CSS_SELECTOR, SEL_LIST_ITEM)
"""

# ====== 🌐 기본 URL 설정 ======
BASE_URL = "https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043#"

"""
📋 BASE_URL 설정 가이드:
- 서울시 사회주택 목록 페이지의 전체 URL
- 브라우저에서 해당 페이지를 열었을 때의 주소를 그대로 복사
- URL 끝의 # 기호도 포함해야 함 (JavaScript 라우팅용)

🔄 다른 사이트로 변경하려면:
BASE_URL = "https://example.com/house/list"  # 새로운 사이트 URL로 교체
"""

# ====== 🤖 셀레니움 드라이버 옵션 ======
HEADLESS = True           # 브라우저 창 표시 여부
IMPLICIT_WAIT = 3         # 요소 찾기 기본 대기 시간
EXPLICIT_WAIT = 10        # 특정 조건 대기 최대 시간

"""
🖥️ 드라이버 옵션 상세 설명:

1. HEADLESS (브라우저 창 표시 여부):
   - True:  백그라운드에서 실행 (브라우저 창 안 보임) ← 서버/자동화용
   - False: 브라우저 창이 뜸 (크롤링 과정 시각적 확인 가능) ← 디버깅용
   
   💡 개발할 때는 False로 설정해서 동작 확인 후, 완성되면 True로 변경

2. IMPLICIT_WAIT (암시적 대기):
   - find_element() 실행시 요소가 없으면 지정된 시간(초)만큼 기다림
   - 3초 = 요소를 찾을 때까지 최대 3초 대기
   - 너무 짧으면: 페이지 로딩 중 에러 발생
   - 너무 길면: 크롤링 속도 느려짐

3. EXPLICIT_WAIT (명시적 대기):
   - 특정 조건(클릭 가능, 텍스트 나타남 등)을 기다릴 때 사용
   - WebDriverWait(driver, EXPLICIT_WAIT).until(...) 형태로 사용
   - 10초 = 최대 10초까지 조건 만족할 때까지 대기

🔧 상황별 권장 설정:
- 개발/디버깅: HEADLESS=False, IMPLICIT_WAIT=5, EXPLICIT_WAIT=15
- 운영/배치: HEADLESS=True, IMPLICIT_WAIT=3, EXPLICIT_WAIT=10
- 느린 사이트: IMPLICIT_WAIT=10, EXPLICIT_WAIT=30
"""

# ====== 📁 파일 저장 경로 ======
DATA_DIR = "data"                    # 메인 데이터 폴더
RAW_DIR = f"{DATA_DIR}/raw"          # 원본 크롤링 데이터 저장 폴더
MERGED_DIR = f"{DATA_DIR}/merged"    # 병합/가공된 데이터 저장 폴더

"""
📂 폴더 구조 설명:
cohome_crawler/
├── data/                    ← DATA_DIR
│   ├── raw/                ← RAW_DIR (원본 데이터)
│   │   ├── listing.csv     (주택 목록)
│   │   ├── overview.csv    (상세소개)
│   │   ├── floorplan.csv   (평면도)
│   │   └── ...
│   └── merged/             ← MERGED_DIR (최종 데이터)
│       └── complete.csv    (모든 정보 통합)

💡 경로 사용 예시:
import os
from src.config import RAW_DIR
os.makedirs(RAW_DIR, exist_ok=True)  # 폴더 생성
filepath = os.path.join(RAW_DIR, "listing.csv")  # 파일 경로 생성
"""

# ====== 🏠 목록 페이지 CSS 선택자 ======
"""
⚠️ 중요: 실제 사이트의 HTML 구조에 맞춰 아래 선택자들을 반드시 수정하세요!

🔧 선택자 찾는 방법:
1. 브라우저에서 F12 누르기
2. Elements 탭에서 원하는 요소 찾기  
3. 우클릭 → Copy → Copy selector
4. 복사된 선택자를 아래에 붙여넣기

📋 실제 HTML 구조 (개발자 도구에서 확인):
<div class="tableWrap2">
    <table class="boardTable">
        <caption>번호, 사진, 지역, 주택명, 주택유형, 테마, 교통, 금액으로 구성된 주택 리스트</caption>
        <thead>
            <tr>
                <th scope="col" class="no">번호</th>
                <th scope="col" class="img">사진</th>
                <th scope="col" class="region">지역</th>
                <th scope="col" class="name">주택명</th>
                <th scope="col" class="type">주택유형</th>
                <th scope="col" class="theme">테마</th>
                <th scope="col" class="traffic">교통</th>
                <th scope="col" class="price">금액</th>
            </tr>
        </thead>
        <tbody id="cohomeForm">
            <tr>                                                    ← SEL_LIST_ITEM
                <td>1</td>                                          ← 번호 (1열)
                <td>
                    <img src="/coHouse/cmmn/file/fileDown.do?..." alt="오늘공동체주택">  ← SEL_IMG (2열)
                </td>
                <td>도봉구</td>                                      ← SEL_REGION (3열)
                <td>
                    <a href="javascript:modify(20000570);" class="no-scr">오늘공동체주택</a>  ← SEL_TITLE (4열)
                </td>
                <td>기타</td>                                        ← SEL_TYPE (5열)
                <td class="no-scr">...</td>                         ← SEL_THEME (6열)
                <td class="no-scr">인덕원, 독립문</td>               ← SEL_TRAFFIC (7열)
                <td>전세 원</td>                                     ← SEL_PRICE (8열)
            </tr>
            <!-- 더 많은 <tr> 행들... -->
        </tbody>
    </table>
</div>
"""

# 🎯 실제 테이블 구조에 맞춘 CSS 선택자
SEL_LIST_ITEM = "#cohomeForm tr"           # 각 주택 행 (테이블 tbody의 tr 태그)
SEL_TITLE = "td:nth-child(4) a"            # 주택명 링크 (4번째 열의 a 태그)
SEL_REGION = "td:nth-child(3)"             # 지역 정보 (3번째 열의 텍스트)
SEL_TYPE = "td:nth-child(5)"               # 주택유형 (5번째 열의 텍스트)
SEL_THEME = "td:nth-child(6)"              # 테마 (6번째 열의 텍스트)
SEL_TRAFFIC = "td:nth-child(7)"            # 교통정보 (7번째 열의 텍스트)
SEL_PRICE = "td:nth-child(8)"              # 가격정보 (8번째 열의 텍스트)
SEL_IMG = "td:nth-child(2) img"            # 썸네일 이미지 (2번째 열의 img 태그)

"""
💡 테이블 구조 선택자 설명:

🔍 nth-child() 선택자 이해하기:
- td:nth-child(1) = 첫 번째 열 (번호)
- td:nth-child(2) = 두 번째 열 (사진)
- td:nth-child(3) = 세 번째 열 (지역)
- td:nth-child(4) = 네 번째 열 (주택명)
- td:nth-child(5) = 다섯 번째 열 (주택유형)
- td:nth-child(6) = 여섯 번째 열 (테마)
- td:nth-child(7) = 일곱 번째 열 (교통)
- td:nth-child(8) = 여덟 번째 열 (금액)

🎯 실제 사용 예시:
1. 주택명 링크 클릭:
   element = row.find_element(By.CSS_SELECTOR, "td:nth-child(4) a")
   element.click()  # javascript:modify() 함수 실행

2. 이미지 URL 가져오기:
   img = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) img")
   url = img.get_attribute("src")

3. 텍스트 정보 가져오기:
   region = row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text

🚨 테이블 크롤링 주의사항:
- 테이블 헤더(thead)는 제외하고 데이터 행(tbody tr)만 선택
- 일부 셀이 비어있을 수 있으므로 _has() 함수로 체크 필요
- JavaScript 링크의 경우 href 속성 대신 click() 이벤트 사용
- 열 순서가 바뀌면 nth-child 번호도 수정 필요

🔧 열 순서 확인 방법:
1. 개발자 도구에서 테이블 헤더 확인
2. 각 th 태그의 순서가 td 태그의 nth-child 번호와 일치
3. 사이트 업데이트로 열 순서가 바뀔 수 있으니 주기적 점검 필요
"""

# ====== 📑 상세 페이지 탭 선택자 ======
"""
📋 상세페이지 탭 구조 예시:
<div class="tab-menu">
    <a href="#tab01" class="active">상세소개</a>     ← 클릭할 탭
    <a href="#tab02">평면도</a>
    <a href="#tab03">입주현황</a>
</div>
<div id="tab01" class="tab-content">...</div>        ← 탭 내용 영역
<div id="tab02" class="tab-content">...</div>
<div id="tab03" class="tab-content">...</div>

🔧 탭 선택자 사용법:
1. TAB_OVERVIEW = "#tab01"           # 탭 내용 영역 ID
2. 또는 "a[href='#tab01']"          # 탭 메뉴 링크
3. 또는 ".tab-content.overview"     # 탭 내용 클래스

💡 실제 사이트에서 확인 방법:
1. 상세페이지에서 탭을 클릭해보기
2. URL이 바뀌는지 확인 (#tab01, #tab02 등)
3. 개발자도구에서 탭 내용 영역의 ID나 클래스 확인
"""

TAB_OVERVIEW  = "#tab01"    # 상세소개 탭 (주소, 입주대상, 주거형태 등)
TAB_FLOORPLAN = "#tab02"    # 평면도 탭 (평면도 이미지들)
TAB_MOVEIN    = "#tab03"    # 입주현황 탭 (방별 가격, 면적 등)
TAB_LOCATION  = "#tab04"    # 위치 탭 (지도, 위치 설명)
TAB_AMENITIES = "#tab05"    # 편의시설 탭 (교통, 주변 시설)
TAB_ABOUT     = "#tab06"    # 사업자소개 탭 (연락처, 업체정보)

"""
🎯 탭별 수집 정보:
- TAB_OVERVIEW:  주소, 입주대상, 주거형태, 면적, 총인원
- TAB_FLOORPLAN: 평면도 이미지 URL들
- TAB_MOVEIN:    방이름, 면적, 보증금, 월세, 관리비, 층/호
- TAB_LOCATION:  상세 주소, 위치 설명
- TAB_AMENITIES: 지하철, 버스, 마트, 병원, 학교 등
- TAB_ABOUT:     상호, 대표자, 전화번호, 이메일

🔄 탭이 없는 사이트인 경우:
- 모든 정보가 한 페이지에 있다면 탭 선택자 대신 섹션 선택자 사용
- 예: SECTION_OVERVIEW = ".overview-section"
"""

# ====== 🎛️ 고급 설정 ======
"""
🚀 성능 최적화 옵션들 (필요시 사용):
"""

# 페이지 로딩 대기 시간
PAGE_LOAD_TIMEOUT = 30      # 페이지 전체 로딩 최대 대기 시간 (초)
SCROLL_PAUSE_TIME = 2       # 스크롤 후 대기 시간 (동적 로딩 대기)

# 재시도 설정
MAX_RETRIES = 3            # 실패시 최대 재시도 횟수
RETRY_DELAY = 5            # 재시도 간격 (초)

# 크롤링 속도 조절
CRAWL_DELAY = 1            # 각 요청 사이 대기 시간 (서버 부하 방지)

"""
💡 고급 설정 사용 예시:

1. 페이지 로딩 타임아웃:
   driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

2. 스크롤링 (무한스크롤 사이트):
   driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
   time.sleep(SCROLL_PAUSE_TIME)

3. 재시도 로직:
   for attempt in range(MAX_RETRIES):
       try:
           # 크롤링 코드
           break
       except Exception as e:
           if attempt < MAX_RETRIES - 1:
               time.sleep(RETRY_DELAY)
           else:
               raise e

4. 속도 조절:
   import time
   time.sleep(CRAWL_DELAY)  # 각 페이지 크롤링 후 잠시 대기
"""
