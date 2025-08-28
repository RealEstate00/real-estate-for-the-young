<<<<<<< HEAD

# real-estate-for-the-young

## 설치 항목

- playwright install chromium

## 크롤링 진행

- 1. seoul portal happy intro // 서울주거포털 행복주택 소개 스냅샷

  - python3 -m scripts.crawl_platforms_raw seoul_happy_intro
  - python -m scripts.crawl_platforms_raw seoul_happy_intro

- 2. sh happy plan // SH 공급계획(행복주택 탭) 표 스냅샷

  - python3 -m scripts.crawl_platforms_raw sh_happy
  - python -m scripts.crawl_platforms_raw sh_happy

- 3. lh announcements // LH 공고 목록(최대 80행)

  - python3 -m scripts.crawl_platforms_raw lh_ann
  - python -m scripts.crawl_platforms_raw lh_ann

- 4. sohouse // 사회주택 목록→상세/이미지

  - python3 -m scripts.crawl_platforms_raw sohouse
  - python -m scripts.crawl_platforms_raw sohouse

- 5. cohouse // 공동체주택 목록→상세/이미지

  - python3 -m scripts.crawl_platforms_raw cohouse
  - python -m scripts.crawl_platforms_raw cohouse

- 6. platform info // 소개/입주자격/청년안심 소개·금융

  - python3 -m scripts.crawl_platforms_raw platform_info
  - python -m scripts.crawl_platforms_raw platform_info

- 7. youth // 청년안심 주택찾기 + 모집공고(BBS)

  - python3 -m scripts.crawl_platforms_raw youth
  - # python -m scripts.crawl_platforms_raw youth

# 🏠 서울시 공동체주택 크롤러 (COHOME Crawler)

서울시 공동체주택 정보를 자동으로 수집하고 CSV 파일로 저장하는 웹 크롤링 시스템

## 📁 프로젝트 구조

```
cohome_crawler/
├── src/                           # 소스코드
│   ├── config.py                  # 설정 파일 (URL, CSS 셀렉터, 경로)
│   ├── driver.py                  # Selenium WebDriver 관리
│   ├── utils.py                   # 공통 유틸리티 함수
│   ├── listing.py                 # 목록 페이지 크롤링 (페이지네이션 포함)
│   ├── storage.py                 # CSV 파일 저장/로드 관리
│   ├── main.py                    # 메인 실행 파일
│   └── detail/                    # 상세 페이지 크롤링 모듈
│       ├── __init__.py           # 상세 정보 통합 수집
│       ├── overview.py           # 상세소개 정보
│       ├── floorplan.py          # 평면도 이미지
│       ├── movein.py             # 입주현황 정보
│       ├── location.py           # 위치 정보
│       ├── amenities.py          # 편의시설 정보
│       └── about.py              # 사업자 정보
├── data/
│   └── raw/                      # 수집된 CSV 파일들
├── requirements.txt              # Python 패키지 의존성
└── README.MD                     # 프로젝트 설명서
```

## 🚀 빠른 시작

### 1. 환경 설정

- 가상환경 설정

### 2. 크롤링 실행

```bash
# 🧪 테스트 크롤링 (11개 주택)
python -m src.main test

# 🚀 전체 크롤링 (모든 주택)
python -m src.main main
```

## 📊 수집되는 데이터

### 📋 CSV 파일 구조

| 파일명            | 설명          | 주요 컬럼                                                                              |
| ----------------- | ------------- | -------------------------------------------------------------------------------------- |
| **listing.csv**   | 목록 상세정보 | 주택명, house_id, 지역, 주택유형, 테마, 교통정보, 가격정보, 썸네일URL                  |
| **overview.csv**  | 상세소개      | 주택명, 주소, 입주대상, 주거형태, 주택유형, 전용면적, 공용면적, 총인원, 총호수, 총실수 |
| **floorplan.csv** | 평면도 이미지 | 주택명, 이미지순서, 이미지URL, 이미지설명, 이미지크기                                  |
| **movein.csv**    | 입주현황      | 주택명, 방이름, 입주타입, 면적, 보증금, 월임대료, 관리비, 층, 호, 입주가능일, 입주가능 |
| **location.csv**  | 위치정보      | 주택명, 주소, 우편번호                                                                 |
| **amenities.csv** | 편의시설      | 주택명, 지하철, 버스, 마트, 병원, 학교, 카페, 기타시설                                 |
| **about.csv**     | 사업자정보    | 주택명, 상호, 대표자, 대표전화, 이메일                                                 |

### 🔑 데이터 연결 구조

- **Primary Key**: `주택명` (모든 테이블 공통)
- **Foreign Key**: `house_id` (JavaScript `modify()` 함수의 매개변수)
- **관계**: 1:N (주택 1개 → 여러 방, 여러 이미지, 여러 편의시설)

## ⚙️ 주요 기능

### 🌐 스마트 페이지네이션

- **자동 페이지 탐지**: 1~4페이지 자동 순회
- **마지막 페이지 감지**: 빈 페이지나 비활성화된 버튼 감지
- **견고한 네비게이션**: 3가지 방법으로 페이지 이동 시도

### 🔄 효율적인 데이터 수집

- **JavaScript 링크 처리**: `javascript:modify(ID)` 자동 실행
- **동적 콘텐츠 대응**: Selenium으로 JavaScript 렌더링 대기
- **에러 복구**: 개별 주택 실패 시 다음 주택 계속 진행

### 💾 안정적인 데이터 저장

- **타임스탬프 자동 추가**: 모든 레코드에 수집일시 기록
- **데이터 검증**: 저장 전 레코드 유효성 검사
- **중복 방지**: 기존 파일 덮어쓰기 방식

## 🛠️ 기술 스택

- **Python 3.8+**
- **Selenium**: 동적 웹페이지 자동화
- **BeautifulSoup4**: HTML 파싱
- **pandas**: 데이터 처리 및 CSV 저장
- **Chrome WebDriver**: 헤드리스 브라우저

## 📈 크롤링 성능

- **총 수집 주택**: ~33개 (4페이지)
- **상세 정보**: 주택당 평균 6개 섹션
- **이미지 정보**: 주택당 평균 5-8개 평면도
- **방 정보**: 주택당 평균 6-23개 방
- **처리 시간**: 주택당 약 15-20초

## 🔧 설정 옵션

### `src/config.py` 주요 설정

```python
# 기본 설정
BASE_URL = "https://soco.seoul.go.kr/youth/bbs/BMSR00015/list.do"
HEADLESS = True                    # False로 설정시 브라우저 창 표시
IMPLICIT_WAIT = 3                  # 요소 대기 시간 (초)
PAGE_LOAD_TIMEOUT = 30             # 페이지 로딩 타임아웃 (초)

# 저장 경로
DATA_DIR = "data"
RAW_DIR = "data/raw"
```

## 🐛 문제 해결

### 일반적인 문제들

1. **ModuleNotFoundError**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Chrome Driver 오류**:

   ```bash
   pip install --upgrade chromedriver-autoinstaller
   ```

3. **페이지 로딩 실패**:

   - `config.py`에서 `PAGE_LOAD_TIMEOUT` 증가
   - `HEADLESS = False`로 설정해서 브라우저 동작 확인

4. **CSS 셀렉터 변경**:

   - 웹사이트 구조 변경 시 `config.py`의 셀렉터 업데이트

### 디버깅 팁

```python
# 브라우저 창 표시 (디버깅용)
HEADLESS = False

# HTML 소스 저장 (셀렉터 확인용)
with open("debug.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
```

## 📝 개발 히스토리

- **v1.0**: 기본 크롤링 기능 구현
- **v1.1**: 모듈화 및 페이지네이션 추가
- **v1.2**: 상세 정보 크롤링 최적화
- **v1.3**: 에러 처리 및 안정성 개선
- **v2.0**: 전면 리팩토링 및 성능 최적화

> > > > > > > 08014f3 (공동체 주택 크롤링 완료!!)
