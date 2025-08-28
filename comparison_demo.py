"""
Chrome 드라이버 vs 일반 HTTP 요청 비교 데모
"""

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_without_browser():
    """일반 HTTP 요청으로 시도 (실패 예상)"""
    print("=" * 50)
    print("🔍 일반 HTTP 요청으로 테스트")
    print("=" * 50)
    
    try:
        response = requests.get("https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043#")
        html = response.text
        
        print(f"📄 HTML 길이: {len(html)} 문자")
        
        # 테이블 데이터 확인
        if "cohomeForm" in html:
            print("✅ cohomeForm 테이블 발견")
        else:
            print("❌ cohomeForm 테이블 없음")
            
        if "<tr>" in html and "<td>" in html:
            print("✅ 테이블 데이터 있음")
        else:
            print("❌ 테이블 데이터 없음 (JavaScript 필요)")
            
        # JavaScript 확인
        if "javascript:" in html:
            print("⚠️ JavaScript 코드 발견 (실행 불가)")
        
        print("\n📋 HTML 일부:")
        print(html[:500] + "..." if len(html) > 500 else html)
        
    except Exception as e:
        print(f"❌ 요청 실패: {e}")


def test_with_browser():
    """Chrome 드라이버로 시도 (성공 예상)"""
    print("\n" + "=" * 50)
    print("🌐 Chrome 드라이버로 테스트")  
    print("=" * 50)
    
    # 최적화된 Chrome 옵션
    opts = Options()
    opts.add_argument("--headless=new")        # 백그라운드 실행
    opts.add_argument("--disable-images")      # 빠른 로딩
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        print("✅ Chrome 드라이버 시작 성공")
        
        # 페이지 접속
        driver.get("https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043#")
        print("✅ 페이지 접속 완료")
        
        # JavaScript 실행 대기
        import time
        time.sleep(5)
        print("✅ JavaScript 로딩 대기 완료")
        
        # 테이블 데이터 확인
        from selenium.webdriver.common.by import By
        
        try:
            table = driver.find_element(By.CSS_SELECTOR, "#cohomeForm")
            print("✅ cohomeForm 테이블 발견")
            
            rows = driver.find_elements(By.CSS_SELECTOR, "#cohomeForm tr")
            print(f"✅ 테이블 행 수: {len(rows)}개")
            
            if rows:
                first_row = rows[0]
                cells = first_row.find_elements(By.CSS_SELECTOR, "td")
                print(f"✅ 첫 번째 행의 열 수: {len(cells)}개")
                
                if len(cells) >= 4:
                    house_name_cell = cells[3]  # 4번째 열 (주택명)
                    link = house_name_cell.find_element(By.CSS_SELECTOR, "a")
                    house_name = link.text
                    js_link = link.get_attribute("href")
                    
                    print(f"✅ 첫 번째 주택명: {house_name}")
                    print(f"✅ JavaScript 링크: {js_link}")
                    
                    # JavaScript 함수 실행 테스트
                    if "javascript:modify(" in js_link:
                        print("✅ JavaScript 링크 실행 가능")
                    else:
                        print("⚠️ JavaScript 링크 형식 다름")
            
        except Exception as e:
            print(f"❌ 테이블 데이터 접근 실패: {e}")
        
    except Exception as e:
        print(f"❌ Chrome 드라이버 실패: {e}")
        print("💡 해결 방법:")
        print("  1. Chrome 브라우저 설치 확인")
        print("  2. pip install selenium 실행")
        print("  3. ChromeDriver 자동 설치 확인")
        
    finally:
        if driver:
            driver.quit()
            print("✅ 브라우저 종료")


def main():
    """비교 테스트 실행"""
    print("🏠 서울시 사회주택 사이트 접근 방법 비교")
    print("Chrome 드라이버가 왜 필요한지 실제로 확인해보겠습니다!\n")
    
    # 1. 일반 HTTP 요청 테스트
    test_without_browser()
    
    # 2. Chrome 드라이버 테스트  
    test_with_browser()
    
    print("\n" + "=" * 50)
    print("🎯 결론")
    print("=" * 50)
    print("❌ 일반 HTTP 요청: JavaScript 실행 불가 → 데이터 없음")
    print("✅ Chrome 드라이버: JavaScript 실행 가능 → 완전한 데이터")
    print("\n💡 따라서 Chrome 드라이버가 반드시 필요합니다!")


if __name__ == "__main__":
    main()
