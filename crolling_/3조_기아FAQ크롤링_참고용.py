import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 드라이버 설정 (headless)
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

url = "https://www.kia.com/kr/customer-service/center/faq"
driver.get(url)
time.sleep(5)

categories = ["TOP 10", "전체", "차량 구매", "차량 정비", "기아멤버스", "홈페이지", "PBV", "기타"]
faq_data = []

for category in categories:
    try:
        # 카테고리 버튼 찾고 클릭
        btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//button[span[contains(text(), '{category}')]]"))
        )
        driver.execute_script("arguments[0].classList.add('is-active');", btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("div.cmp-accordion__item")

            for item in items:
                q = item.select_one("span.cmp-accordion__title")
                a = item.select_one("div.cmp-accordion__panel")
                faq_data.append({
                    "category": category,
                    "question": q.get_text(strip=True) if q else "제목 없음",
                    "answer": a.get_text(strip=True) if a else "내용 없음"
                })

            try:
                next_btn = driver.find_element(By.XPATH, "//ul[@class='paging-list']/li[@class='is-active']/following-sibling::li[1]/a")
                driver.execute_script("arguments[0].classList.add('is-active');", next_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
            except:
                print(f"{category} 완료.")
                break

    except Exception as e:
        print(f"[{category}] 오류: {e}")

pd.DataFrame(faq_data).to_csv("kia_faq_data.csv", index=False, encoding="utf-8-sig")

driver.quit()