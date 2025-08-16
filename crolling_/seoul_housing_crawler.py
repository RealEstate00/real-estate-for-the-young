import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import time

class SeoulHousingCrawler:
    """서울시 사회주택 크롤링 클래스"""
    
    async def collect_floor_plan_images(self, page, housing_data):
        """평면도 탭에서 이미지 수집"""
        try:
            # 평면도 탭 클릭
            floor_plan_tab = await page.query_selector("a[href='#detail2']")
            if floor_plan_tab:
                await floor_plan_tab.click()
                await page.wait_for_timeout(2000)
                
                # h2 클래스 내 모든 이미지 찾기
                images = await page.query_selector_all("h2 img, .detail img, #detail2 img")
                
                for img in images:
                    try:
                        src = await img.get_attribute("src")
                        alt = await img.get_attribute("alt")
                        if src:
                            housing_data["평면도_이미지"].append({
                                "url": src,
                                "alt": alt or "평면도"
                            })
                    except:
                        continue
                        
                print(f"평면도 이미지 {len(housing_data['평면도_이미지'])}개 수집")
        except Exception as e:
            print(f"평면도 수집 중 오류: {e}")
    
    async def collect_occupancy_status(self, page, housing_data):
        """입주현황 탭에서 테이블 데이터 수집"""
        try:
            # 입주현황 탭 클릭
            occupancy_tab = await page.query_selector("a[href='#detail3']")
            if occupancy_tab:
                await occupancy_tab.click()
                await page.wait_for_timeout(2000)
                
                # 테이블 데이터 수집
                rows = await page.query_selector_all("#detail3 table tbody tr")
                
                for row in rows:
                    try:
                        cells = await row.query_selector_all("td")
                        if len(cells) >= 10:
                            room_data = {
                                "방이름": await cells[0].text_content(),
                                "입주타입": await cells[1].text_content(),
                                "면적": await cells[2].text_content(),
                                "보증금": await cells[3].text_content(),
                                "월임대료": await cells[4].text_content(),
                                "관리비": await cells[5].text_content(),
                                "층": await cells[6].text_content(),
                                "호": await cells[7].text_content(),
                                "인원": await cells[8].text_content(),
                                "입주가능일": await cells[9].text_content() if len(cells) > 9 else "정보 없음",
                                "입주가능": await cells[10].text_content() if len(cells) > 10 else "정보 없음"
                            }
                            
                            # 텍스트 정리
                            for key, value in room_data.items():
                                room_data[key] = value.strip() if value else "정보 없음"
                            
                            housing_data["입주현황"].append(room_data)
                    except Exception as e:
                        print(f"행 처리 중 오류: {e}")
                        continue
                        
                print(f"입주현황 {len(housing_data['입주현황'])}개 방 정보 수집")
        except Exception as e:
            print(f"입주현황 수집 중 오류: {e}")
    
    async def collect_facilities(self, page, housing_data):
        """편의시설 탭에서 교통/시설 정보 수집"""
        try:
            # 편의시설 탭 클릭
            facilities_tab = await page.query_selector("a[href='#detail4']")
            if facilities_tab:
                await facilities_tab.click()
                await page.wait_for_timeout(3000)
                
                print("편의시설 페이지 구조 분석 중...")
                
                # 페이지 전체 텍스트 가져오기
                page_text = await page.text_content("#detail4")
                print(f"편의시설 페이지 텍스트 일부: {page_text[:200] if page_text else '텍스트 없음'}")
                
                # 다양한 셀렉터로 교통 정보 찾기
                transport_selectors = [
                    "#detail4 .bus",
                    "#detail4 .subway", 
                    "#detail4 .transport",
                    "#detail4 li",
                    "#detail4 div",
                    "#detail4 span"
                ]
                
                for selector in transport_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"교통 정보 요소 발견: {selector} ({len(elements)}개)")
                        for i, elem in enumerate(elements[:5]):  # 처음 5개만 확인
                            try:
                                text = await elem.text_content()
                                if text and text.strip():
                                    print(f"  {i+1}: {text.strip()}")
                            except:
                                continue
                
                # 지하철 정보 추출 (정규식)
                if page_text:
                    import re
                    
                    # 지하철 노선 찾기
                    subway_patterns = [
                        r'(\d+호선)',
                        r'(\d+선)',
                        r'지하철[^\n]*(\d+호선)',
                        r'(\d+호선[^\n,]*)',
                        r'1선도봉산역|7호선도봉산역'  # 특정 역명 패턴
                    ]
                    
                    for pattern in subway_patterns:
                        subway_match = re.search(pattern, page_text, re.IGNORECASE)
                        if subway_match:
                            housing_data["지하철"] = subway_match.group(1).strip()
                            print(f"지하철 정보 발견: {housing_data['지하철']}")
                            break
                    
                    # 버스 정보 찾기
                    bus_patterns = [
                        r'버스[^\n]*?(\d+(?:,\s*\d+)*)',
                        r'(\d+(?:,\s*\d+)+)(?=\s*번)',
                        r'140, 150, 160'  # 특정 버스 번호 패턴
                    ]
                    
                    for pattern in bus_patterns:
                        bus_match = re.search(pattern, page_text)
                        if bus_match:
                            housing_data["버스"] = bus_match.group(1).strip()
                            print(f"버스 정보 발견: {housing_data['버스']}")
                            break
                
                # 편의시설 정보 수집 (더 넓은 범위)
                facility_selectors = [
                    "#detail4 .facility",
                    "#detail4 .flexbox .facility", 
                    "#detail4 .convenience",
                    "#detail4 ul li",
                    "#detail4 .amenity"
                ]
                
                for selector in facility_selectors:
                    facility_items = await page.query_selector_all(selector)
                    if facility_items:
                        print(f"편의시설 요소 발견: {selector} ({len(facility_items)}개)")
                        for item in facility_items:
                            try:
                                facility_text = await item.text_content()
                                if facility_text and facility_text.strip() and len(facility_text.strip()) > 2:
                                    clean_text = facility_text.strip()
                                    if clean_text not in housing_data["편의시설"]:
                                        housing_data["편의시설"].append(clean_text)
                            except:
                                continue
                        break  # 첫 번째로 찾은 셀렉터 사용
                        
                print(f"편의시설 {len(housing_data['편의시설'])}개 항목 수집")
                
            else:
                print("편의시설 탭을 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"편의시설 수집 중 오류: {e}")
    
    async def collect_business_info(self, page, housing_data):
        """사업자소개 탭에서 연락처 정보 수집"""
        try:
            # 사업자소개 탭 클릭
            business_tab = await page.query_selector("a[href='#detail5']")
            if business_tab:
                await business_tab.click()
                await page.wait_for_timeout(3000)
                
                print("사업자소개 페이지 구조 분석 중...")
                
                # 사업자 정보 추출
                business_text = await page.text_content("#detail5")
                print(f"사업자 페이지 텍스트 일부: {business_text[:200] if business_text else '텍스트 없음'}")
                
                if business_text:
                    import re
                    
                    # 더 유연한 패턴으로 정보 추출
                    patterns = {
                        "상호": [
                            r'상호\s*[:\s]\s*([^\n\r]+)',
                            r'회사명\s*[:\s]\s*([^\n\r]+)',
                            r'업체명\s*[:\s]\s*([^\n\r]+)',
                        ],
                        "대표자": [
                            r'대표자?\s*[:\s]\s*([^\n\r]+)',
                            r'대표\s*[:\s]\s*([^\n\r]+)',
                            r'성명\s*[:\s]\s*([^\n\r]+)',
                        ],
                        "대표전화": [
                            r'대표전화\s*[:\s]\s*([^\n\r]+)',
                            r'전화\s*[:\s]\s*([^\n\r]+)',
                            r'연락처\s*[:\s]\s*([^\n\r]+)',
                            r'TEL\s*[:\s]\s*([^\n\r]+)',
                            r'(\d{2,3}-\d{3,4}-\d{4})',  # 전화번호 패턴
                        ],
                        "이메일": [
                            r'이메일\s*[:\s]\s*([^\n\r\s]+)',
                            r'E-?mail\s*[:\s]\s*([^\n\r\s]+)',
                            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # 이메일 패턴
                        ]
                    }
                    
                    for field, pattern_list in patterns.items():
                        for pattern in pattern_list:
                            match = re.search(pattern, business_text, re.IGNORECASE)
                            if match:
                                value = match.group(1).strip()
                                if value and len(value) > 1:  # 유효한 값인지 확인
                                    housing_data[field] = value
                                    print(f"{field} 정보 발견: {value}")
                                    break
                    
                    # dashline에서도 정보 찾기 (이전에 수집된 정보 활용)
                    if housing_data["상호"] == "정보 없음":
                        # 이전 dashline에서 수집된 상호 정보 사용
                        for i in range(len(housing_data.get("dashline_raw", []))):
                            dashline_text = str(housing_data.get("dashline_raw", [{}])[i])
                            company_match = re.search(r'상호\s*:\s*([^\n]+)', dashline_text)
                            if company_match:
                                housing_data["상호"] = company_match.group(1).strip()
                                break
                                
                print("사업자 정보 수집 완료")
            else:
                print("사업자소개 탭을 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"사업자 정보 수집 중 오류: {e}")
    
    def print_results(self, housing_data):
        """결과 출력"""
        print("주택명:", housing_data["주택명"])
        print("주소:", housing_data["주소"])
        print("입주대상:", housing_data["입주대상"])
        print("주거형태:", housing_data["주거형태"])
        print("면적:", housing_data["면적"])
        print("총 주거인원:", housing_data["총 주거인원"])
        print(f"평면도 이미지: {len(housing_data['평면도_이미지'])}개")
        print(f"입주현황: {len(housing_data['입주현황'])}개 방")
        print("지하철:", housing_data["지하철"])
        print("버스:", housing_data["버스"])
        print(f"편의시설: {len(housing_data['편의시설'])}개")
        print("상호:", housing_data["상호"])
        print("대표자:", housing_data["대표자"])
        print("대표전화:", housing_data["대표전화"])
        print("이메일:", housing_data["이메일"])
    
    async def save_data(self, housing_data):
        """데이터 저장"""
        import json
        
        # JSON 파일로 저장 (전체 데이터)
        with open("crolling_/seoul_housing_complete.json", "w", encoding="utf-8") as f:
            json.dump(housing_data, f, ensure_ascii=False, indent=2)
        
        # CSV용 기본 데이터 저장
        basic_data = {
            "주택명": housing_data["주택명"],
            "주소": housing_data["주소"],
            "입주대상": housing_data["입주대상"],
            "주거형태": housing_data["주거형태"],
            "면적": housing_data["면적"],
            "총 주거인원": housing_data["총 주거인원"],
            "평면도_이미지_수": len(housing_data["평면도_이미지"]),
            "입주가능_방수": len(housing_data["입주현황"]),
            "지하철": housing_data["지하철"],
            "버스": housing_data["버스"],
            "편의시설_수": len(housing_data["편의시설"]),
            "상호": housing_data["상호"],
            "대표자": housing_data["대표자"],
            "대표전화": housing_data["대표전화"],
            "이메일": housing_data["이메일"]
        }
        
        df = pd.DataFrame([basic_data])
        df.to_csv("crolling_/seoul_housing_data.csv", index=False, encoding="utf-8-sig")
        
        print("\n데이터 저장 완료:")
        print("- seoul_housing_complete.json (전체 상세 데이터)")
        print("- seoul_housing_data.csv (요약 데이터)")

async def crawl_seoul_housing():
    """서울시 사회주택 정보 크롤링"""
    crawler = SeoulHousingCrawler()
    
    async with async_playwright() as p:
        # 브라우저 실행 (headless=False로 설정하여 브라우저 창을 볼 수 있음)
        browser = await p.chromium.launch(headless=False, slow_mo=2000)
        page = await browser.new_page()
        
        # 뷰포트 설정
        await page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            print("페이지 접속 중...")
            # 대상 사이트 접속
            await page.goto("https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043#", wait_until="networkidle")
            
            # 페이지 로딩 대기
            await page.wait_for_timeout(5000)
            
            print("주택 목록 로딩 대기 중...")
            # 페이지 구조 파악을 위해 HTML 출력
            await page.wait_for_timeout(5000)  # 더 긴 대기 시간
            
            # 페이지 소스 일부 확인
            page_content = await page.content()
            print("페이지 로딩 완료, 주택 목록 찾는 중...")
            
            # 페이지 구조 디버깅
            print("페이지 구조 분석 중...")
            
            # 모든 테이블 찾기
            tables = await page.query_selector_all("table")
            print(f"페이지에서 발견된 테이블 수: {len(tables)}")
            
            # 모든 tr 태그 찾기
            rows = await page.query_selector_all("tr")
            print(f"페이지에서 발견된 행(tr) 수: {len(rows)}")
            
            # 모든 링크 찾기
            all_links = await page.query_selector_all("a")
            print(f"페이지에서 발견된 링크 수: {len(all_links)}")
            
            # JavaScript modify 함수가 있는 링크 찾기
            modify_links = await page.query_selector_all("a[href*='modify']")
            print(f"modify 함수가 있는 링크 수: {len(modify_links)}")
            
            # 첫 번째 몇 개 링크의 정보 출력
            print("첫 10개 링크 정보:")
            for i, link in enumerate(all_links[:10]):
                try:
                    href = await link.get_attribute("href")
                    text = await link.text_content()
                    if text and text.strip():
                        print(f"링크 {i+1}: '{text.strip()}' -> {href}")
                except:
                    continue
            
            # 테이블 구조에서 첫 번째 주택 찾기
            print("\n테이블에서 첫 번째 주택 찾는 중...")
            
            # 다양한 셀렉터로 시도
            selectors_to_try = [
                "tbody tr:first-child td a",
                "table tbody tr:first-child a",
                "tr:first-child a[href*='javascript:modify']",
                "tr:first-child a[href*='modify']", 
                "tr:first-child a",
                "tbody tr:first-child a",
                "table tr:first-child a",
                "a[href*='modify']:first-of-type"
            ]
            
            first_house_link = None
            for selector in selectors_to_try:
                try:
                    first_house_link = await page.query_selector(selector)
                    if first_house_link:
                        print(f"첫 번째 주택 링크를 찾았습니다: {selector}")
                        break
                except:
                    continue
            
            if first_house_link:
                # 주택명 추출 (클릭하기 전에)
                house_name = await first_house_link.text_content()
                house_name = house_name.strip() if house_name else "정보 없음"
                print(f"선택된 주택: {house_name}")
                
                # href 속성에서 JavaScript 함수 추출
                href = await first_house_link.get_attribute("href")
                print(f"링크 href: {href}")
                
                # JavaScript 함수 직접 실행 시도
                try:
                    if href and "javascript:" in href:
                        # javascript:modify(20000570) 형태에서 함수 추출
                        js_function = href.replace("javascript:", "")
                        print(f"실행할 JavaScript: {js_function}")
                        await page.evaluate(js_function)
                        print("JavaScript 함수 실행 성공!")
                    else:
                        # 일반 클릭 시도
                        await first_house_link.click(force=True)
                        print("일반 클릭 성공!")
                except Exception as click_error:
                    print(f"클릭/실행 실패: {click_error}")
                    # 마지막 시도: 강제 클릭
                    await page.evaluate("(element) => element.click()", first_house_link)
                
                await page.wait_for_timeout(3000)
                
                print("종합 정보 추출 시작...")
                # 상세 페이지 로딩 대기
                await page.wait_for_timeout(2000)
                
                # 전체 데이터 구조
                housing_data = {
                    # 상세소개
                    "주택명": house_name,
                    "주소": "정보 없음",
                    "입주대상": "정보 없음", 
                    "주거형태": "정보 없음",
                    "면적": "정보 없음",
                    "총 주거인원": "정보 없음",
                    
                    # 평면도
                    "평면도_이미지": [],
                    
                    # 입주현황
                    "입주현황": [],
                    
                    # 편의시설
                    "지하철": "정보 없음",
                    "버스": "정보 없음", 
                    "편의시설": [],
                    
                    # 사업자소개
                    "상호": "정보 없음",
                    "대표자": "정보 없음",
                    "대표전화": "정보 없음",
                    "이메일": "정보 없음"
                }
                
                print("상세 페이지 구조 분석 중...")
                
                # dashline 클래스가 있는 li 요소들에서 정보 추출
                dashline_items = await page.query_selector_all("li.dashline")
                print(f"dashline 항목 수: {len(dashline_items)}")
                
                if dashline_items:
                    print("dashline 항목들에서 정보 추출 중...")
                    for i, item in enumerate(dashline_items):
                        try:
                            text_content = await item.text_content()
                            text_content = text_content.strip() if text_content else ""
                            print(f"dashline {i+1}: {text_content}")
                            
                            # 텍스트 정리 (공백, 줄바꿈 제거)
                            import re
                            clean_text = re.sub(r'\s+', ' ', text_content).strip()
                            
                            # 각 항목에서 정보 추출
                            if "주소" in clean_text and ":" in clean_text and housing_data["주소"] == "정보 없음":
                                # 첫 번째 주소만 추출 (여러 개가 있을 수 있음)
                                parts = clean_text.split("주소 :", 1)
                                if len(parts) > 1:
                                    address_part = parts[1].split("입주대상")[0].strip()
                                    if address_part:  # 빈 값이 아닐 때만 저장
                                        housing_data["주소"] = address_part
                                    
                            if "입주대상" in clean_text and ":" in clean_text:
                                parts = clean_text.split("입주대상 :", 1)
                                if len(parts) > 1:
                                    target_part = parts[1].split("주거형태")[0].strip()
                                    housing_data["입주대상"] = target_part
                                    
                            if "주거형태" in clean_text and ":" in clean_text:
                                parts = clean_text.split("주거형태 :", 1)
                                if len(parts) > 1:
                                    type_part = parts[1].split("면적")[0].strip()
                                    housing_data["주거형태"] = type_part
                                    
                            if "면적" in clean_text and ":" in clean_text:
                                parts = clean_text.split("면적 :", 1)
                                if len(parts) > 1:
                                    area_part = parts[1].split("총 주거인원")[0].strip()
                                    housing_data["면적"] = area_part
                                    
                            if "총 주거인원" in clean_text and ":" in clean_text:
                                parts = clean_text.split("총 주거인원", 1)
                                if len(parts) > 1:
                                    # : 다음부터 주택유형 전까지 추출
                                    residents_part = parts[1].split(":", 1)
                                    if len(residents_part) > 1:
                                        residents_text = residents_part[1].split("주택유형")[0].strip()
                                        housing_data["총 주거인원"] = residents_text
                        except Exception as e:
                            print(f"dashline 항목 처리 중 오류: {e}")
                            continue
                else:
                    print("dashline 요소를 찾을 수 없습니다. 다른 방법으로 시도...")
                    # 전체 페이지 텍스트에서 정규식으로 추출
                    try:
                        page_text = await page.text_content("body")
                        if page_text:
                            import re
                            
                            # 주소 추출
                            address_match = re.search(r'주소\s*:\s*([^\n]+)', page_text)
                            if address_match:
                                housing_data["주소"] = address_match.group(1).strip()
                            
                            # 입주대상 추출
                            target_match = re.search(r'입주대상\s*:\s*([^\n]+)', page_text)
                            if target_match:
                                housing_data["입주대상"] = target_match.group(1).strip()
                            
                            # 주거형태 추출
                            type_match = re.search(r'주거형태\s*:\s*([^\n]+)', page_text)
                            if type_match:
                                housing_data["주거형태"] = type_match.group(1).strip()
                            
                            # 면적 추출
                            area_match = re.search(r'면적\s*:\s*([^\n]+)', page_text)
                            if area_match:
                                housing_data["면적"] = area_match.group(1).strip()
                            
                            # 총 주거인원 추출
                            residents_match = re.search(r'총 주거인원[^:]*:\s*([^\n]+)', page_text)
                            if residents_match:
                                housing_data["총 주거인원"] = residents_match.group(1).strip()
                                
                            print("정규식으로 정보 추출 완료")
                    except Exception as e:
                        print(f"정규식 추출 중 오류: {e}")
                
                # 2. 평면도 탭 클릭하여 이미지 수집
                print("\n=== 평면도 정보 수집 ===")
                await crawler.collect_floor_plan_images(page, housing_data)
                
                # 3. 입주현황 탭 클릭하여 테이블 데이터 수집
                print("\n=== 입주현황 정보 수집 ===")
                await crawler.collect_occupancy_status(page, housing_data)
                
                # 4. 편의시설 탭 클릭하여 교통/시설 정보 수집
                print("\n=== 편의시설 정보 수집 ===")
                await crawler.collect_facilities(page, housing_data)
                
                # 5. 사업자소개 탭 클릭하여 연락처 정보 수집
                print("\n=== 사업자소개 정보 수집 ===")
                await crawler.collect_business_info(page, housing_data)
                
                # 결과 출력
                print("\n=== 종합 크롤링 결과 ===")
                crawler.print_results(housing_data)
                
                # JSON과 CSV 파일로 저장
                await crawler.save_data(housing_data)
                
                return housing_data
                
            else:
                print("첫 번째 주택을 찾을 수 없습니다.")
                return None
                
        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            return None
            
        finally:
            await browser.close()

async def main():
    """메인 실행 함수"""
    print("서울시 사회주택 크롤링을 시작합니다...")
    result = await crawl_seoul_housing()
    
    if result:
        print("\n크롤링이 성공적으로 완료되었습니다!")
    else:
        print("\n크롤링에 실패했습니다.")

if __name__ == "__main__":
    asyncio.run(main())
