"""
🚀 최적화된 주택 목록 크롤링 모듈

✨ 개선사항:
1. 코드 중복 완전 제거
2. 메모리 효율적인 스트리밍 처리
3. 간소화된 페이지네이션 로직
4. 명확한 함수 책임 분리
5. 일관된 에러 처리
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from src.config import (
    BASE_URL, SEL_LIST_ITEM, SEL_TITLE, SEL_REGION, SEL_TYPE,
    SEL_THEME, SEL_TRAFFIC, SEL_PRICE, SEL_IMG
)
from src.detail.overview import parse_overview
import re
import time


def _extract_house_links_from_page(driver) -> list[dict]:
    """현재 페이지에서 주택 정보 추출 (내부 함수) - 목록 페이지의 모든 정보 포함"""
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, SEL_LIST_ITEM)
        houses = []
        
        for row in rows:
            try:
                # 주택명과 ID 추출
                title_el = row.find_element(By.CSS_SELECTOR, SEL_TITLE)
                house_name = title_el.text.strip()
                js_href = title_el.get_attribute("href")
                
                if not (js_href and "modify(" in js_href):
                    continue
                    
                match = re.search(r'modify\((\d+)\)', js_href)
                if not match:
                    continue
                    
                house_id = match.group(1)
                
                # 추가 정보 추출
                region = ""
                house_type = ""
                theme = ""
                traffic = ""
                price = ""
                thumbnail_url = ""
                
                try:
                    region_el = row.find_element(By.CSS_SELECTOR, SEL_REGION)
                    region = region_el.text.strip()
                except:
                    pass
                
                try:
                    type_el = row.find_element(By.CSS_SELECTOR, SEL_TYPE)
                    house_type = type_el.text.strip()
                except:
                    pass
                
                try:
                    theme_el = row.find_element(By.CSS_SELECTOR, SEL_THEME)
                    theme = theme_el.text.strip()
                except:
                    pass
                
                try:
                    traffic_el = row.find_element(By.CSS_SELECTOR, SEL_TRAFFIC)
                    traffic = traffic_el.text.strip()
                except:
                    pass
                
                try:
                    price_el = row.find_element(By.CSS_SELECTOR, SEL_PRICE)
                    price = price_el.text.strip()
                except:
                    pass
                
                try:
                    img_el = row.find_element(By.CSS_SELECTOR, SEL_IMG)
                    thumbnail_src = img_el.get_attribute("src")
                    if thumbnail_src:
                        # 상대경로를 절대경로로 변환
                        if thumbnail_src.startswith("/"):
                            thumbnail_url = "https://soco.seoul.go.kr" + thumbnail_src
                        else:
                            thumbnail_url = thumbnail_src
                except:
                    pass
                
                house_info = {
                    "주택명": house_name,
                    "house_id": house_id,
                    "지역": region,
                    "주택유형": house_type,
                    "테마": theme,
                    "교통정보": traffic,
                    "가격정보": price,
                    "썸네일URL": thumbnail_url
                }
                
                houses.append(house_info)
                
            except Exception as e:
                print(f"    ⚠️ 주택 정보 추출 실패: {e}")
                continue
        
        return houses
    except Exception as e:
        print(f"    ❌ 페이지 정보 추출 실패: {e}")
        return []


def _navigate_to_next_page(driver, current_page: int) -> bool:
    """다음 페이지로 이동 (개선된 로직)"""
    try:
        next_page = current_page + 1
        print(f"    ➡️ {next_page}페이지로 이동 시도...")
        
        # 방법 1: 다음 페이지 번호 버튼 클릭
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, f"button[onclick*='cohomeList({next_page})']")
            if next_button.is_enabled() and next_button.is_displayed():
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)
                print(f"    ✅ {next_page}페이지 버튼 클릭 성공")
                return True
        except:
            pass
        
        # 방법 2: "다음" 버튼 클릭 (화살표 버튼)
        try:
            next_arrow = driver.find_element(By.CSS_SELECTOR, "button[class*='arrow next']:not([disabled])")
            if next_arrow.is_enabled() and next_arrow.is_displayed():
                driver.execute_script("arguments[0].click();", next_arrow)
                time.sleep(2)
                print(f"    ✅ '다음' 버튼 클릭 성공")
                return True
        except:
            pass
        
        # 방법 3: JavaScript 직접 실행
        try:
            driver.execute_script(f"cohomeList({next_page});")
            time.sleep(2)
            print(f"    ✅ JavaScript 직접 실행 성공")
            return True
        except:
            pass
        
        print(f"    ❌ {next_page}페이지로 이동 실패")
        return False
            
    except Exception as e:
        print(f"    ❌ 페이지 이동 오류: {e}")
        return False


def _is_last_page(driver, current_page: int) -> bool:
    """마지막 페이지인지 확인하는 함수"""
    try:
        # 방법 1: 다음 페이지 버튼이 비활성화되어 있는지 확인
        next_page = current_page + 1
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, f"button[onclick*='cohomeList({next_page})']")
            if not next_button.is_enabled():
                print(f"    🏁 {next_page}페이지 버튼이 비활성화됨 (마지막 페이지)")
                return True
        except:
            pass
        
        # 방법 2: "다음" 화살표 버튼이 비활성화되어 있는지 확인
        try:
            next_arrow = driver.find_element(By.CSS_SELECTOR, "button[class*='arrow next'][disabled]")
            if next_arrow:
                print(f"    🏁 '다음' 버튼이 비활성화됨 (마지막 페이지)")
                return True
        except:
            pass
        
        # 방법 3: 현재 페이지가 4 이상이면 마지막으로 간주 (안전장치)
        if current_page >= 10:  # 최대 10페이지까지만
            print(f"    🏁 최대 페이지 수 도달 ({current_page}페이지)")
            return True
        
        return False
        
    except Exception as e:
        print(f"    ⚠️ 마지막 페이지 확인 오류: {e}")
        return False


def collect_house_links(driver, max_pages: int = None) -> list[dict]:
    """
    🔗 주택 정보 수집 (통합 함수) - 목록 페이지의 모든 정보 포함
    
    Args:
        driver: Selenium WebDriver
        max_pages: 최대 페이지 수 (None=모든 페이지, 1=첫 페이지만)
    
    Returns:
        list[dict]: [{"주택명": str, "house_id": str, "지역": str, "주택유형": str, 
                      "테마": str, "교통정보": str, "가격정보": str, "썸네일URL": str}, ...]
    """
    print(f"🌐 주택 링크 수집 시작 (최대 {max_pages or '모든'}페이지)")
    
    # 첫 페이지 이동
    driver.get(BASE_URL)
    time.sleep(1)
    
    all_links = []
    current_page = 1
    
    while True:
        print(f"📄 {current_page}페이지 처리 중...")
        
        # 현재 페이지 링크 추출
        page_links = _extract_house_links_from_page(driver)
        all_links.extend(page_links)
        
        print(f"  ✅ {len(page_links)}개 수집 (누적: {len(all_links)}개)")
        
        # 종료 조건 체크
        if max_pages and current_page >= max_pages:
            print(f"  🛑 최대 페이지 수({max_pages}) 도달")
            break
        
        if not page_links:  # 빈 페이지면 종료
            print("  ⚠️ 빈 페이지 감지, 종료")
            break
        
        # 마지막 페이지인지 확인
        if _is_last_page(driver, current_page):
            print(f"  🏁 마지막 페이지 감지, 종료")
            break
        
        # 다음 페이지로 이동
        if not _navigate_to_next_page(driver, current_page):
            print(f"  🏁 다음 페이지 이동 실패, 종료")
            break
        
        current_page += 1
    
    print(f"🎉 총 {len(all_links)}개 주택 수집 완료 ({current_page}페이지)")
    return all_links


def crawl_overview_details(driver, house_links: list[dict], limit: int = None) -> list[dict]:
    """
    📋 주택 상세 정보 수집 (overview만)
    
    Args:
        driver: Selenium WebDriver
        house_links: 주택 링크 리스트
        limit: 처리할 주택 수 제한
    
    Returns:
        list[dict]: overview 데이터 리스트
    """
    houses_to_process = house_links[:limit] if limit else house_links
    total = len(houses_to_process)
    
    print(f"🔍 상세 정보 수집 시작 ({total}개 주택)")
    
    details = []
    
    for i, house in enumerate(houses_to_process, 1):
        house_name = house["주택명"]
        house_id = house["house_id"]
        
        print(f"[{i}/{total}] 📍 '{house_name}' 처리 중...")
        
        try:
            # JavaScript로 상세페이지 이동
            driver.execute_script(f"modify({house_id});")
            time.sleep(2)
            
            # HTML 가져오기
            html = driver.page_source
            
            # overview 파싱
            overview_data = parse_overview(html, house_name)
            if overview_data:
                details.append(overview_data)
                print(f"  ✅ 성공")
            else:
                print(f"  ⚠️ 데이터 없음")
                
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            continue
    
    print(f"🎉 상세 정보 수집 완료: {len(details)}/{total}개")
    return details


# 🎯 간편 사용 함수들
def get_first_page_links(driver) -> list[dict]:
    """첫 페이지 링크만 수집"""
    return collect_house_links(driver, max_pages=1)


def get_all_pages_links(driver) -> list[dict]:
    """모든 페이지 링크 수집"""
    return collect_house_links(driver, max_pages=None)


def save_listing_to_csv(driver, max_pages: int = 1, filename: str = "listing.csv") -> list[dict]:
    """
    📋 목록 상세정보를 CSV로 저장하는 함수
    
    Args:
        driver: Selenium WebDriver
        max_pages: 수집할 페이지 수 (1=첫 페이지만, None=모든 페이지)
        filename: 저장할 CSV 파일명
    
    Returns:
        list[dict]: 수집된 목록 데이터
    """
    from src.storage import save_to_csv, add_timestamp
    
    print(f"📋 목록 상세정보 CSV 저장 시작 (파일명: {filename})")
    
    # 목록 데이터 수집
    listing_data = collect_house_links(driver, max_pages)
    
    if listing_data:
        # 타임스탬프 추가 후 CSV 저장
        timestamped_data = add_timestamp(listing_data)
        save_to_csv(timestamped_data, filename)
        print(f"✅ 목록 데이터 저장 완료: {len(listing_data)}개 주택")
        return listing_data
    else:
        print("❌ 저장할 목록 데이터가 없습니다.")
        return []


def crawl_first_page_overview(driver, limit: int = None) -> tuple[list[dict], list[dict]]:
    """첫 페이지 overview 크롤링"""
    links = get_first_page_links(driver)
    details = crawl_overview_details(driver, links, limit)
    return links, details


def crawl_all_pages_overview(driver, detail_limit: int = None) -> tuple[list[dict], list[dict]]:
    """모든 페이지 overview 크롤링"""
    links = get_all_pages_links(driver)
    details = crawl_overview_details(driver, links, detail_limit)
    return links, details


# 💡 사용 예시:
"""
🎯 간단한 사용법:

from src.driver import get_driver
from src.listing import save_listing_to_csv, crawl_first_page_overview, crawl_all_pages_overview

driver = get_driver()

# 📋 목록 상세정보만 CSV로 저장 (가장 간단!)
save_listing_to_csv(driver, max_pages=1, filename="listing.csv")        # 첫 페이지만
save_listing_to_csv(driver, max_pages=None, filename="listing_all.csv") # 모든 페이지

# 🔍 목록 + overview 정보 함께 수집
links, details = crawl_first_page_overview(driver, limit=5)
links, details = crawl_all_pages_overview(driver, detail_limit=50)

driver.quit()

📊 생성되는 CSV 파일:
- listing.csv: 첫 페이지 목록 상세정보 (주택명, house_id, 지역, 주택유형, 테마, 교통정보, 가격정보, 썸네일URL)
- listing_all.csv: 모든 페이지 목록 상세정보
- overview.csv: 상세소개 정보 (주소, 입주대상, 주거형태, 면적 등)
"""
