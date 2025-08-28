"""
quick_test.py - 빠른 크롤링 테스트

🎯 목적:
- 5초 안에 크롤링이 작동하는지 빠르게 확인
- 사이트 접속 및 기본 데이터 수집만 테스트
- 실제 저장은 하지 않음

⚡ 사용법:
python quick_test.py
"""

import sys
import os
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def quick_crawl_test():
    """빠른 크롤링 테스트"""
    print("⚡ 빠른 크롤링 테스트 시작")
    print("=" * 50)
    
    driver = None
    try:
        # 1. 드라이버 초기화 (헤드리스 모드)
        print("🔧 Chrome 드라이버 초기화...")
        from src.driver import get_driver, safe_quit
        
        # 빠른 테스트를 위해 헤드리스 모드 강제 설정
        import src.config as config
        original_headless = config.HEADLESS
        config.HEADLESS = True  # 빠른 테스트를 위해 헤드리스 모드
        
        driver = get_driver()
        print("✅ 드라이버 초기화 완료")
        
        # 2. 사이트 접속 테스트
        print("🌐 사이트 접속 테스트...")
        driver.get(config.BASE_URL)
        print("✅ 사이트 접속 성공")
        
        # 3. 기본 요소 존재 확인
        print("🔍 페이지 요소 확인...")
        from selenium.webdriver.common.by import By
        
        # 테이블 존재 확인
        try:
            table = driver.find_element(By.CSS_SELECTOR, "#cohomeForm")
            print("✅ 주택 테이블 발견")
            
            # 행 개수 확인
            rows = driver.find_elements(By.CSS_SELECTOR, "#cohomeForm tr")
            print(f"✅ 테이블 행 수: {len(rows)}개")
            
            if len(rows) > 0:
                # 첫 번째 행의 데이터 확인
                first_row = rows[0]
                cells = first_row.find_elements(By.CSS_SELECTOR, "td")
                print(f"✅ 첫 번째 행 열 수: {len(cells)}개")
                
                if len(cells) >= 4:
                    # 주택명 확인
                    try:
                        title_cell = cells[3]  # 4번째 열
                        link = title_cell.find_element(By.CSS_SELECTOR, "a")
                        house_name = link.text.strip()
                        js_link = link.get_attribute("href")
                        
                        print(f"✅ 첫 번째 주택: '{house_name}'")
                        print(f"✅ JavaScript 링크: {js_link[:50]}...")
                        
                        # JavaScript 링크 형식 확인
                        if "javascript:modify(" in js_link:
                            print("✅ JavaScript 링크 형식 정상")
                        else:
                            print("⚠️ JavaScript 링크 형식 다름")
                            
                    except Exception as e:
                        print(f"⚠️ 주택명 추출 실패: {e}")
                
            else:
                print("❌ 테이블에 데이터가 없습니다")
                return False
                
        except Exception as e:
            print(f"❌ 테이블 찾기 실패: {e}")
            return False
        
        # 4. 간단한 데이터 추출 테스트
        print("📊 데이터 추출 테스트...")
        
        try:
            # 처음 3개 행만 테스트
            test_rows = rows[:3] if len(rows) >= 3 else rows
            extracted_data = []
            
            for i, row in enumerate(test_rows, 1):
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if len(cells) >= 4:
                    try:
                        # 주택명
                        title_link = cells[3].find_element(By.CSS_SELECTOR, "a")
                        title = title_link.text.strip()
                        
                        # 지역 (3번째 열)
                        region = cells[2].text.strip() if len(cells) > 2 else ""
                        
                        extracted_data.append({
                            "순번": i,
                            "주택명": title,
                            "지역": region
                        })
                        
                        print(f"  {i}. {title} ({region})")
                        
                    except Exception as e:
                        print(f"  {i}. 데이터 추출 실패: {e}")
            
            print(f"✅ {len(extracted_data)}개 주택 데이터 추출 성공")
            
        except Exception as e:
            print(f"❌ 데이터 추출 실패: {e}")
            return False
        
        # 5. 테스트 성공
        print("\n🎉 빠른 테스트 성공!")
        print(f"⏰ 테스트 완료 시간: {datetime.now().strftime('%H:%M:%S')}")
        print("✅ 크롤링 기본 기능이 정상 작동합니다!")
        
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 로딩 실패: {e}")
        print("💡 src 폴더의 파일들이 모두 있는지 확인하세요.")
        return False
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        print("💡 가능한 원인:")
        print("  1. 인터넷 연결 문제")
        print("  2. Chrome/ChromeDriver 설치 문제")
        print("  3. 사이트 구조 변경")
        return False
        
    finally:
        # 설정 복원
        try:
            config.HEADLESS = original_headless
        except:
            pass
            
        # 드라이버 종료
        if driver:
            try:
                safe_quit(driver)
            except:
                pass


def main():
    """메인 실행"""
    print("⚡ 서울시 사회주택 크롤러 빠른 테스트")
    print("(약 10-15초 소요)")
    print()
    
    start_time = datetime.now()
    success = quick_crawl_test()
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 50)
    if success:
        print(f"🎉 테스트 성공! (소요 시간: {duration:.1f}초)")
        print("💡 다음 단계:")
        print("  python test_crawler.py  (상세 테스트)")
        print("  python main.py test     (실제 크롤링 테스트)")
    else:
        print(f"❌ 테스트 실패 (소요 시간: {duration:.1f}초)")
        print("💡 문제를 해결한 후 다시 시도하세요.")


if __name__ == "__main__":
    main()
