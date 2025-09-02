# 실거래가 부동산 정보

https://land.seoul.go.kr/land/rtms/rtmsApartment.do
2006년부터 서울시 '전월세' 전체 실거래가 정보 저장
`<a href="javascript:fn_tab('rentApartment');" title="전월세 - 선택됨"><span>`전월세`</a>`

**페이징** : 1. 실거래 가격정보 클래스 안에서 '단독/다가구', '다세대/연립', '오피스텔', '도시형 생활주택', '아파트' 내용 크롤링 예정

<li id="rtmsApartment" class="on">
<a href="/land/rtms/rtmsApartment.do" title="선택됨">아파트</a>
<a href="/land/rtms/rtmsSingleHouse.do">단독/다가구</a>
<a href="/land/rtms/rtmsMultiHouse.do">다세대/연립</a>
<a href="/land/rtms/rtmsOfficetel.do">오피스텔</a>
<a href="/land/rtms/rtmsCityHouse.do">도시형 생활주택</a>

2. 지역선택 / 구 / 전체
   <select class="basic" id="selectSigungu" name="selectSigungu"><option value="11000">자치구 선택</option><option value="11680">강남구</option><option value="11740">강동구</option><option value="11305">강북구</option><option value="11500">강서구</option><option value="11620">관악구</option><option value="11215">광진구</option><option value="11530">구로구</option><option value="11545">금천구</option><option value="11350">노원구</option><option value="11320">도봉구</option><option value="11230">동대문구</option><option value="11590">동작구</option><option value="11440">마포구</option><option value="11410">서대문구</option><option value="11650">서초구</option><option value="11200">성동구</option><option value="11290">성북구</option><option value="11710">송파구</option><option value="11470">양천구</option><option value="11560">영등포구</option><option value="11170">용산구</option><option value="11380">은평구</option><option value="11110">종로구</option><option value="11140">중구</option><option value="11260">중랑구</option></select>

<select class="basic" id="selectBjdong" name="selectBjdong"><option value="">전체</option><option value="11000">강일동</option><option value="10200">고덕동</option><option value="10500">길동</option><option value="10600">둔촌동</option><option value="10100">명일동</option><option value="10300">상일동</option><option value="10800">성내동</option><option value="10700">암사동</option><option value="10900">천호동</option></select>

3. 데이터 기간 선택 - "분기"로 데이터 저장
   `<select class="basic" id="selectGubun" name="selectGubun">`
   <option value="1">분기</option>
   <option value="2">기간</option>
   </select>

<select class="basic" id="selectYear" name="selectYear" style="display: inline-block;"><option value="2025">2025</option><option value="2024">2024</option><option value="2023">2023</option><option value="2022">2022</option><option value="2021">2021</option><option value="2020">2020</option><option value="2019">2019</option><option value="2018">2018</option><option value="2017">2017</option><option value="2016">2016</option><option value="2015">2015</option><option value="2014">2014</option><option value="2013">2013</option><option value="2012">2012</option><option value="2011">2011</option></select>

<select class="basic" id="selectBoongi" name="selectBoongi" style="display: inline-block;">
								<option value="1">1분기</option>
								<option value="2">2분기</option>
								<option value="3">3분기</option>
								<option value="4">4분기</option>
							</select>

4. 전세/월세/준월세/준전세 셀렉
   `<select class="basic" id="selectJWGubun" name="selectJWGubun">`

   <option value="1">전세</option>
   <option value="2">월세</option>
   <option value="3">준월세</option>
   <option value="4">준전세</option>
   </select>

5. 검색 버튼 클릭
   `<input type="button" id="search" class="on" value="검색">`

** 테이블 **
xls 데이터 다운
`<input type="button" class="btn dark" id="excel" value="다운로드" style="display: inline-block;">`

<caption class="hideCaption">아파트 전월세가/매물/시세 - 단지[준공년도], 지번, 전용면적, 전월세가, 매물시세, 계약일(계약구분), 보증금, 층 항목으로 구성 </caption>

# 공시지가

https://data.seoul.go.kr/dataList/OA-1180/F/1/datasetView.do?utm_source=chatgpt.com
" 전체 파일 보기 " 토글
`<span>`전체 파일보기
파일 다운로드
`<a href="javascript:downloadFile('87');" title="공시지가_2025년.zip"><span class="hide">`공시지가\_2025년.zip 다운로드`</a>`
