"""
driver.py - 셀레니움 Chrome 드라이버 생성 및 설정 모듈

🎯 이 파일의 역할:
- Chrome 브라우저 드라이버를 생성하고 최적화된 옵션 설정
- config.py의 설정값(HEADLESS, IMPLICIT_WAIT)을 기반으로 구성
- 서울시 사회주택 사이트 크롤링에 최적화된 브라우저 환경 제공

💡 왜 Chrome을 사용하나요?
1. 가장 널리 사용되는 브라우저 (호환성 최고)
2. JavaScript 실행 성능이 우수
3. 개발자 도구와 셀레니움 연동이 완벽
4. 서울시 사회주택 사이트의 JavaScript 링크 처리에 최적

🔧 설정 옵션 설명:
- HEADLESS: 브라우저 창 표시 여부 (개발시 False, 운영시 True)
- IMPLICIT_WAIT: 요소 찾기 기본 대기 시간 (사이트 로딩 속도에 맞춤)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from src.config import HEADLESS, IMPLICIT_WAIT, PAGE_LOAD_TIMEOUT
import time

def get_driver():
    """
    🚀 Chrome 드라이버를 생성하여 반환하는 함수
    
    📋 설정되는 옵션들:
    1. 헤드리스 모드: 브라우저 창 표시 여부
    2. 보안 옵션: 서버/컨테이너 환경 안정화
    3. 성능 옵션: 메모리 사용량 최적화
    4. 사이트 특화 옵션: 서울시 사회주택 사이트 최적화
    
    📖 사용 예시:
    driver = get_driver()
    driver.get("https://soco.seoul.go.kr/...")
    # ... 크롤링 작업 ...
    driver.quit()  # 반드시 종료해야 함!
    
    🎯 반환값: 설정된 Chrome WebDriver 객체
    """
    
    print("🔧 Chrome 드라이버 초기화 중...")
    
    # Chrome 옵션 객체 생성
    opts = Options()
    
    # 🖥️ 헤드리스 모드 설정 (config.py에서 제어)
    if HEADLESS:
        # --headless=new는 Chrome 109+ 최신 방식 (성능/안정성 향상)
        opts.add_argument("--headless=new")
        print("  ✅ 헤드리스 모드 활성화 (브라우저 창 숨김)")
    else:
        print("  ✅ GUI 모드 활성화 (브라우저 창 표시)")
    
    # 🛡️ 보안 및 안정성 옵션 (서버/컨테이너 환경용)
    opts.add_argument("--no-sandbox")              # 샌드박스 비활성화 (리눅스 서버 필수)
    opts.add_argument("--disable-dev-shm-usage")   # /dev/shm 사용 안함 (메모리 부족 방지)
    opts.add_argument("--disable-gpu")             # GPU 가속 비활성화 (서버 환경 안정성)
    
    # 🚀 성능 최적화 옵션
    opts.add_argument("--disable-blink-features=AutomationControlled")  # 자동화 감지 우회
    opts.add_argument("--disable-extensions")      # 확장 프로그램 비활성화
    opts.add_argument("--disable-plugins")         # 플러그인 비활성화
    opts.add_argument("--disable-images")          # 이미지 로딩 비활성화 (속도 향상)
    
    # 🌐 서울시 사회주택 사이트 최적화 옵션
    opts.add_argument("--disable-web-security")    # CORS 제한 완화
    opts.add_argument("--allow-running-insecure-content")  # Mixed content 허용
    opts.add_argument("--ignore-certificate-errors")  # SSL 인증서 오류 무시
    
    # 📱 User-Agent 설정 (일반 사용자처럼 보이기)
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 🖼️ 윈도우 크기 설정 (테이블이 잘 보이도록)
    opts.add_argument("--window-size=1920,1080")
    
    try:
        # Chrome 드라이버 생성
        driver = webdriver.Chrome(options=opts)
        
        # ⏰ 타임아웃 설정
        driver.implicitly_wait(IMPLICIT_WAIT)  # 요소 찾기 기본 대기 시간
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)  # 페이지 로딩 최대 대기 시간
        
        # 📏 브라우저 창 크기 설정 (GUI 모드일 때)
        if not HEADLESS:
            driver.maximize_window()
        
        print(f"  ✅ 암시적 대기 시간: {IMPLICIT_WAIT}초")
        print(f"  ✅ 페이지 로딩 타임아웃: {PAGE_LOAD_TIMEOUT}초")
        print("🎉 Chrome 드라이버 초기화 완료!")
        
        return driver
        
    except Exception as e:
        print(f"❌ Chrome 드라이버 초기화 실패: {e}")
        print("💡 해결 방법:")
        print("  1. Chrome 브라우저가 설치되어 있는지 확인")
        print("  2. ChromeDriver가 설치되어 있는지 확인")
        print("  3. pip install selenium 실행")
        print("  4. Chrome과 ChromeDriver 버전이 호환되는지 확인")
        raise


def safe_quit(driver):
    """
    🛡️ 드라이버를 안전하게 종료하는 함수
    
    📋 처리 과정:
    1. 모든 창 닫기
    2. 드라이버 프로세스 종료
    3. 에러 발생시에도 안전하게 처리
    
    📖 사용 예시:
    driver = get_driver()
    try:
        # 크롤링 작업...
    finally:
        safe_quit(driver)  # 반드시 실행되도록 finally 블록에서 호출
    """
    
    try:
        if driver:
            print("🔚 브라우저 종료 중...")
            driver.quit()
            print("✅ 브라우저 종료 완료")
    except Exception as e:
        print(f"⚠️ 브라우저 종료 중 오류 (무시됨): {e}")


# 💡 Chrome 드라이버 사용 팁:
"""
🎯 개발 단계별 권장 설정:

1️⃣ 개발/디버깅 단계:
   - HEADLESS = False  (브라우저 창 보면서 확인)
   - IMPLICIT_WAIT = 5  (여유있게 대기)
   - --disable-images 제거 (이미지도 확인)

2️⃣ 테스트 단계:
   - HEADLESS = True   (빠른 테스트)
   - IMPLICIT_WAIT = 3  (적당한 대기)
   - 모든 최적화 옵션 적용

3️⃣ 운영/배치 단계:
   - HEADLESS = True   (서버 환경)
   - IMPLICIT_WAIT = 3  (효율성)
   - 모든 보안/성능 옵션 적용

🚨 주의사항:
- driver.quit() 반드시 호출해야 함 (메모리 누수 방지)
- 예외 발생시에도 종료되도록 try-finally 사용
- 여러 드라이버 동시 실행시 메모리 사용량 주의
- Chrome 버전과 ChromeDriver 버전 호환성 확인 필수

🔧 문제 해결:
1. "chromedriver not found" → ChromeDriver 설치 필요
2. "This version of ChromeDriver only supports Chrome version X" → 버전 불일치
3. 메모리 부족 → --disable-images, --disable-extensions 옵션 추가
4. 느린 로딩 → IMPLICIT_WAIT, PAGE_LOAD_TIMEOUT 값 증가
"""
