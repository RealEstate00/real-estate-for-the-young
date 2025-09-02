# Selector Diary — RTMS 전월세 실거래 + 공시지가
Last updated: 2025-08-25 KST

목적: 서울시 부동산 포털의 전월세 실거래와 공시지가 파일 수집을 위한 선택자와 동작 특성을 기록한다.

---

## A) RTMS 전월세 실거래
- 아파트: https://land.seoul.go.kr/land/rtms/rtmsApartment.do
- 탭 전환
  - 전월세 탭 함수: `fn_tab('rentApartment')`
  - 주택유형 탭: `#rtmsApartment.on` 내부 a 또는 각 유형 URL
    - 아파트 `/rtmsApartment.do`
    - 단독/다가구 `/rtmsSingleHouse.do`
    - 다세대/연립 `/rtmsMultiHouse.do`
    - 오피스텔 `/rtmsOfficetel.do`
    - 도시형 생활주택 `/rtmsCityHouse.do`
- 구/동 선택
  - 구: `select#selectSigungu` (값: 행정코드, 예 11680=강남구)
  - 동: `select#selectBjdong` (값: 동 코드, 공백=전체)
  - 동 옵션은 구 선택 후 동적 로딩됨
- 기간 선택
  - 구분: `select#selectGubun` 값 `1`=분기, `2`=기간
  - 연도: `select#selectYear`
  - 분기: `select#selectBoongi` (1~4)
- 전월세 구분
  - `select#selectJWGubun` 값: 1=전세, 2=월세, 3=준월세, 4=준전세
- 검색 버튼
  - `input#search[type=button][value="검색"]`
- 결과 테이블
  - 엑셀 다운로드: `input#excel[type=button][value="다운로드"]`
  - 표 캡션 예시: 단지[준공년도], 지번, 전용면적, 전월세가, 매물시세, 계약일(계약구분), 보증금, 층
- 페이징
  - 화면 하단의 페이지네이션 링크. 공통 패턴: `a:has-text("다음")`, `a.next` 등
  - 안전 로직: 다음 버튼 없거나 비활성화면 루프 종료

필드 매핑(예시):
1. 단지[준공년도]  → `td:nth-child(1)` (단지명과 준공년도 분리 저장)
2. 지번            → `td:nth-child(2)`
3. 전용면적        → `td:nth-child(3)` (㎡, 숫자화)
4. 전월세가        → `td:nth-child(4)` (월 임대료, 전세면 0)
5. 매물시세        → `td:nth-child(5)` (선택 저장)
6. 계약일(구분)     → `td:nth-child(6)` (날짜와 구분 텍스트 분리)
7. 보증금          → `td:nth-child(7)`
8. 층              → `td:nth-child(8)`

스모크 체크리스트
- [ ] 구=강동구로 2024년 1분기 월세 1페이지 수집
- [ ] 엑셀 다운로드 1회 성공
- [ ] 다음 페이지 진입 또는 비활성 확인

---

## B) 공시지가 파일 다운로드
- 데이터셋: https://data.seoul.go.kr/dataList/OA-1180/F/1/datasetView.do
- 전체 파일 보기 토글: `span:has-text("전체 파일보기")`
- 파일 다운로드 링크: `a[href^="javascript:downloadFile("]` (title/텍스트에 연도 포함)
- 저장 정책
  - `data/raw/YYYY-MM-DD/official_landprice/`에 파일 저장
  - `manifest.csv`: 파일명, 크기, 원본명, 저장경로, 다운로드 식별, 수집시각
