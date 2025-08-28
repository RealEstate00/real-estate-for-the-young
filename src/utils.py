"""
utils.py - 크롤링에 필요한 공통 유틸리티 함수 모음

🎯 이 파일의 역할:
- 모든 크롤링 모듈에서 공통으로 사용하는 도우미 함수들
- 텍스트 정제, HTML 파싱, 안전한 요소 접근 등
- 에러 방지와 코드 재사용성을 높이는 핵심 유틸들

📋 주요 기능:
1. 텍스트 정제: 공백, 줄바꿈, 특수문자 정리
2. BeautifulSoup 연동: HTML 파싱 지원
3. 안전한 요소 접근: 에러 없는 요소 찾기/클릭
4. 명시적 대기: 동적 콘텐츠 로딩 대기

💡 왜 utils.py가 필요한가요?
1. 코드 중복 방지: 같은 기능을 여러 곳에서 재사용
2. 에러 방지: 안전한 함수들로 예외 상황 처리
3. 유지보수성: 공통 로직을 한 곳에서 관리
4. 가독성: 복잡한 로직을 간단한 함수명으로 추상화
"""

import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from src.config import EXPLICIT_WAIT


def to_soup(html: str) -> BeautifulSoup:
    """
    🍲 HTML 문자열을 BeautifulSoup 객체로 변환하는 함수
    
    📋 사용 용도:
    - 셀레니움으로 가져온 HTML을 BeautifulSoup으로 파싱
    - 복잡한 HTML 구조에서 데이터 추출할 때 유용
    - CSS 선택자보다 더 정교한 파싱이 필요할 때
    
    📖 사용 예시:
    html = driver.page_source
    soup = to_soup(html)
    titles = soup.find_all("h2", class_="title")
    
    💡 언제 사용하나요?
    - 셀레니움의 find_element로는 복잡한 구조 파싱이 어려울 때
    - 여러 요소를 한번에 처리해야 할 때
    - 텍스트 추출과 정제를 동시에 해야 할 때
    """
    return BeautifulSoup(html, "html.parser")


def clean(text: str | None) -> str:
    """
    🧹 텍스트를 정제해서 깔끔한 문자열로 변환하는 함수
    
    📋 정제 내용:
    1. None 값 → 빈 문자열로 변환
    2. 연속된 공백/탭/줄바꿈 → 단일 공백으로 통합
    3. 앞뒤 공백 제거 (strip)
    4. 특수 공백 문자들 정리
    
    📖 사용 예시:
    raw_text = "  오늘공동체주택\n\n   도봉구  "
    clean_text = clean(raw_text)  # "오늘공동체주택 도봉구"
    
    💡 왜 필요한가요?
    - 웹에서 가져온 텍스트는 불필요한 공백이 많음
    - CSV 저장시 깔끔한 데이터 필요
    - 데이터 분석시 일관된 형태 유지
    
    🎯 처리 과정:
    "  오늘공동체\n주택\t\t도봉구  " → "오늘공동체 주택 도봉구"
    """
    if not text:
        return ""
    
    # 정규식으로 모든 공백 문자(\s)를 단일 공백으로 치환
    # \s+ : 하나 이상의 공백, 탭, 줄바꿈 등
    cleaned = re.sub(r"\s+", " ", text)
    
    # 앞뒤 공백 제거
    return cleaned.strip()


def safe_text(node, default: str = "") -> str:
    """
    🛡️ BeautifulSoup 노드에서 안전하게 텍스트를 추출하는 함수
    
    📋 안전장치:
    - 노드가 None이어도 에러 없이 기본값 반환
    - 추출된 텍스트를 자동으로 clean() 함수로 정제
    - 예외 발생시 기본값 반환
    
    📖 사용 예시:
    soup = to_soup(html)
    title_node = soup.find("h2", class_="title")
    title = safe_text(title_node, "제목 없음")  # 안전하게 추출
    
    # 위험한 방법 (에러 발생 가능):
    # title = title_node.get_text()  # title_node가 None이면 에러!
    
    💡 언제 사용하나요?
    - BeautifulSoup의 find() 결과가 None일 수 있을 때
    - 선택적 필드(있을 수도 없을 수도 있는 정보) 추출시
    - 안정적인 크롤링 코드 작성시
    """
    try:
        if node and hasattr(node, 'get_text'):
            return clean(node.get_text())
        else:
            return default
    except Exception:
        return default


def wait_css(driver, css: str, timeout: int = EXPLICIT_WAIT):
    """
    ⏰ 특정 CSS 요소가 나타날 때까지 대기 후 요소를 반환하는 함수 (명시적 대기)
    
    📋 동작 원리:
    1. 지정된 CSS 선택자로 요소 찾기
    2. 요소가 없으면 timeout까지 계속 대기
    3. 요소가 나타나면 즉시 반환
    4. timeout 초과시 TimeoutException 발생
    
    📖 사용 예시:
    # JavaScript로 동적 로딩되는 테이블 대기
    table = wait_css(driver, "#cohomeForm", timeout=10)
    
    # 팝업이나 모달 대기
    modal = wait_css(driver, ".modal.show")
    
    💡 언제 사용하나요?
    - JavaScript로 동적 생성되는 요소 대기
    - AJAX 로딩 완료 대기
    - 페이지 전환 후 새 요소 로딩 대기
    - 서울시 사회주택 사이트의 탭 전환 후 대기
    
    🚨 주의사항:
    - timeout 값을 너무 크게 설정하면 전체 크롤링 속도 저하
    - 너무 작게 설정하면 로딩 중인 요소를 놓칠 수 있음
    - 사이트별로 적절한 timeout 값 조정 필요
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )
        return element
    except TimeoutException:
        print(f"⏰ 요소 대기 시간 초과: {css} (timeout: {timeout}초)")
        raise


def click_if_exists(driver, css: str) -> bool:
    """
    🖱️ 요소가 존재하면 클릭, 없으면 조용히 넘어가는 안전한 클릭 함수
    
    📋 동작 과정:
    1. CSS 선택자로 요소 찾기
    2. 요소가 있으면 클릭
    3. 요소가 없거나 클릭 실패해도 에러 없이 False 반환
    4. 성공시 True 반환
    
    📖 사용 예시:
    # 선택적 팝업 닫기 버튼 클릭
    popup_closed = click_if_exists(driver, ".popup-close")
    
    # 쿠키 동의 버튼 클릭 (있을 수도 없을 수도)
    cookie_accepted = click_if_exists(driver, ".cookie-accept")
    
    if popup_closed:
        print("팝업이 닫혔습니다")
    
    💡 언제 사용하나요?
    - 선택적으로 나타나는 버튼들 (팝업, 광고, 쿠키 동의 등)
    - 에러 없이 안전하게 클릭하고 싶을 때
    - 클릭 성공 여부를 확인하고 싶을 때
    
    🎯 반환값: 클릭 성공시 True, 실패시 False
    """
    try:
        element = driver.find_element(By.CSS_SELECTOR, css)
        element.click()
        return True
    except Exception as e:
        # 디버깅용 (필요시 주석 해제)
        # print(f"클릭 실패 (무시됨): {css} - {e}")
        return False


def has_css(driver, css: str) -> bool:
    """
    🔍 특정 CSS 요소가 페이지에 존재하는지 확인하는 함수
    
    📋 동작 과정:
    1. CSS 선택자로 요소 찾기 시도
    2. 요소가 있으면 True 반환
    3. 요소가 없으면 False 반환 (에러 없음)
    
    📖 사용 예시:
    # 로그인 상태 확인
    is_logged_in = has_css(driver, ".user-profile")
    
    # 특정 탭이 활성화되어 있는지 확인
    is_overview_active = has_css(driver, "#tab01.active")
    
    # 에러 메시지가 있는지 확인
    has_error = has_css(driver, ".error-message")
    
    if has_error:
        print("에러가 발생했습니다!")
    
    💡 언제 사용하나요?
    - 조건부 로직 구현시 (요소 있으면 A, 없으면 B)
    - 페이지 상태 확인시
    - 에러 없이 요소 존재 여부만 확인하고 싶을 때
    - listing.py의 _has() 함수와 유사하지만 driver 전체 대상
    """
    try:
        driver.find_element(By.CSS_SELECTOR, css)
        return True
    except NoSuchElementException:
        return False
    except Exception:
        # 다른 예외 (네트워크 오류 등)도 False 처리
        return False


def page_html(driver) -> str:
    """
    📄 현재 페이지의 전체 HTML 소스코드를 반환하는 함수
    
    📋 사용 용도:
    - 디버깅: 페이지 구조 분석
    - BeautifulSoup 파싱: to_soup()와 함께 사용
    - HTML 파일 저장: 문제 상황 재현용
    - 로깅: 특정 시점의 페이지 상태 기록
    
    📖 사용 예시:
    # 현재 페이지 HTML 가져오기
    html = page_html(driver)
    
    # BeautifulSoup으로 파싱
    soup = to_soup(html)
    
    # 디버깅용 HTML 파일 저장
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    💡 언제 사용하나요?
    - CSS 선택자가 작동하지 않을 때 HTML 구조 확인
    - 복잡한 파싱 작업시 BeautifulSoup과 연동
    - 크롤링 실패시 디버깅용 HTML 저장
    - 사이트 구조 변경 분석
    """
    try:
        return driver.page_source
    except Exception as e:
        print(f"⚠️ HTML 소스 가져오기 실패: {e}")
        return ""


def scroll_to_element(driver, css: str) -> bool:
    """
    📜 특정 요소까지 스크롤하는 함수
    
    📋 동작 과정:
    1. CSS 선택자로 요소 찾기
    2. 해당 요소까지 부드럽게 스크롤
    3. 스크롤 완료 후 잠시 대기
    
    📖 사용 예시:
    # 테이블 하단까지 스크롤 (더 많은 데이터 로딩)
    scroll_to_element(driver, "#cohomeForm tr:last-child")
    
    # 특정 탭까지 스크롤
    scroll_to_element(driver, "#tab05")
    
    💡 언제 사용하나요?
    - 무한 스크롤 사이트에서 더 많은 데이터 로딩
    - 긴 페이지에서 특정 섹션으로 이동
    - JavaScript 이벤트가 스크롤에 의해 트리거될 때
    """
    try:
        element = driver.find_element(By.CSS_SELECTOR, css)
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", element)
        time.sleep(1)  # 스크롤 완료 대기
        return True
    except Exception as e:
        print(f"⚠️ 스크롤 실패: {css} - {e}")
        return False


# 💡 utils.py 사용 패턴:
"""
🎯 일반적인 사용 패턴:

1️⃣ 텍스트 정제:
   raw_text = element.text
   clean_text = clean(raw_text)

2️⃣ 안전한 요소 접근:
   if has_css(driver, ".target-element"):
       element = driver.find_element(By.CSS_SELECTOR, ".target-element")
       # 처리 로직

3️⃣ 동적 요소 대기:
   wait_css(driver, "#dynamic-content")
   data = driver.find_element(By.CSS_SELECTOR, "#dynamic-content").text

4️⃣ BeautifulSoup 연동:
   html = page_html(driver)
   soup = to_soup(html)
   items = soup.find_all("div", class_="item")

5️⃣ 선택적 클릭:
   click_if_exists(driver, ".cookie-accept")
   click_if_exists(driver, ".popup-close")

🚨 주의사항:
- 모든 함수는 예외 상황을 안전하게 처리하도록 설계됨
- 에러 발생시에도 크롤링이 중단되지 않음
- 디버깅이 필요할 때는 예외 메시지를 주석 해제해서 확인
- timeout 값들은 사이트 특성에 맞게 조정 필요

🎉 결과:
- 안정적인 크롤링 코드 작성 가능
- 예외 상황에 강한 로직 구현
- 코드 재사용성과 가독성 향상
- 유지보수 비용 절감
"""
