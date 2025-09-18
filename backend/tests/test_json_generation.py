#!/usr/bin/env python3
"""
JSON 생성 테스트 함수
- sohouse, cohouse, youth 플랫폼의 JSON 생성 테스트
- related_housing_info의 title/index 포함 확인
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_collection.crawlers.so import SoHouseCrawler
from backend.services.data_collection.crawlers.co import CoHouseCrawler
from backend.services.data_collection.crawlers.youth import YouthCrawler
from playwright.sync_api import sync_playwright
import json

def test_json_generation(platform: str, test_url: str = None):
    """JSON 생성 테스트"""
    print(f"\n=== {platform.upper()} JSON 생성 테스트 ===")
    
    # 크롤러 인스턴스 생성
    if platform == "sohouse":
        crawler = SoHouseCrawler(progress=None)
        if not test_url:
            test_url = "https://www.sohouse.go.kr/sohouse/sohouseDetail.do?sohouseId=SH2024000001"
    elif platform == "cohouse":
        crawler = CoHouseCrawler(progress=None)
        if not test_url:
            test_url = "https://www.cohouse.go.kr/cohouse/cohouseDetail.do?cohouseId=CH2024000001"
    elif platform == "youth":
        crawler = YouthCrawler(progress=None)
        if not test_url:
            test_url = "https://www.youth.go.kr/youth/youthDetail.do?youthId=YH2024000001"
    else:
        print(f"지원하지 않는 플랫폼: {platform}")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print(f"테스트 URL: {test_url}")
            page.goto(test_url, wait_until="networkidle")
            
            # JSON 생성 테스트
            print("JSON 생성 중...")
            
            # platform_specific_fields 추출
            ps_fields = crawler._extract_platform_specific_fields(page)
            
            # kv_pairs 추출 (간단한 테스트용)
            kv_pairs = {}
            
            # JSON 필드 생성
            json_data = crawler._filter_json_fields(kv_pairs, ps_fields)
            
            # JSON 구조 확인
            print("\n=== JSON 구조 확인 ===")
            print(f"최상위 키: {list(json_data.keys())}")
            
            # facilities 확인
            if "facilities" in json_data:
                print(f"\nFacilities: {json_data['facilities']}")
            else:
                print("\nFacilities: 없음")
            
            # company_info 확인
            if "company_info" in json_data:
                print(f"\nCompany Info: {json_data['company_info']}")
            else:
                print("\nCompany Info: 없음")
            
            # housing_specific 확인
            if "housing_specific" in json_data:
                print(f"\nHousing Specific: {json_data['housing_specific']}")
            else:
                print("\nHousing Specific: 없음")
            
            # building_details 확인
            if "building_details" in json_data:
                print(f"\nBuilding Details: {json_data['building_details']}")
            else:
                print("\nBuilding Details: 없음")
            
            # related_housing_info 확인
            if "related_housing_info" in json_data:
                print(f"\nRelated Housing Info:")
                related = json_data["related_housing_info"]
                for key, value in related.items():
                    print(f"  {key}: {value}")
            else:
                print("\nRelated Housing Info: 없음")
            
            # platform_specific_fields 확인
            if "platform_specific_fields" in json_data:
                print(f"\nPlatform Specific Fields: {json_data['platform_specific_fields']}")
            else:
                print("\nPlatform Specific Fields: 없음")
            
            # JSON 파일로 저장 (test_output 디렉토리에)
            output_dir = Path("backend/tests/test_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"test_{platform}_json_output.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"\nJSON 저장됨: {output_file}")
            
            return json_data
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

def test_sohouse_with_real_data():
    """실제 sohouse 데이터로 테스트"""
    print("\n=== SOHOUSE 실제 데이터 테스트 ===")
    
    # 실제 sohouse HTML 파일 경로 (최신 크롤링 결과)
    html_file = "/Users/jina/Documents/GitHub/SeoulHousingAssistBot/backend/data/raw/sohouse/2025-09-15__20250915T014729/html/detail_0000.html"
    
    if not os.path.exists(html_file):
        print(f"HTML 파일이 존재하지 않습니다: {html_file}")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # HTML 파일 로드
            page.goto(f"file://{html_file}")
            
            crawler = SoHouseCrawler(progress=None)
            
            # platform_specific_fields 추출
            ps_fields = crawler._extract_platform_specific_fields(page)
            
            # kv_pairs 추출 (간단한 테스트용)
            kv_pairs = {}
            
            # JSON 필드 생성
            json_data = crawler._filter_json_fields(kv_pairs, ps_fields)
            
            # platform_specific_fields에서 related_housing_info 확인
            print(f"\nPlatform Specific Fields: {ps_fields}")
            
            # related_housing_info 상세 확인
            if "related_housing_info" in json_data:
                print("\n=== Related Housing Info 상세 분석 ===")
                related = json_data["related_housing_info"]
                
                for category, info in related.items():
                    print(f"\n{category}:")
                    if isinstance(info, dict):
                        for key, value in info.items():
                            if key == "links" and isinstance(value, list):
                                print(f"  {key} ({len(value)}개):")
                                for i, link in enumerate(value):
                                    print(f"    [{i}] {link}")
                            elif key == "items" and isinstance(value, list):
                                print(f"  {key} ({len(value)}개):")
                                for i, item in enumerate(value):
                                    print(f"    [{i}] {item}")
                            else:
                                print(f"  {key}: {value}")
                    else:
                        print(f"  {info}")
            else:
                print("\nRelated Housing Info: 없음")
            
            # JSON 파일로 저장 (test_output 디렉토리에)
            output_dir = Path("backend/tests/test_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "test_sohouse_real_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"\n실제 데이터 JSON 저장됨: {output_file}")
            
            return json_data
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

def test_cohouse_with_real_data():
    """실제 cohouse 데이터로 테스트"""
    print("\n=== COHOUSE 실제 데이터 테스트 ===")
    
    # 실제 cohouse HTML 파일 경로 (최신 크롤링 결과)
    html_file = "/Users/jina/Documents/GitHub/SeoulHousingAssistBot/backend/data/raw/cohouse/2025-09-15__20250915T082117/html/detail_0005.html"
    
    if not os.path.exists(html_file):
        print(f"HTML 파일이 존재하지 않습니다: {html_file}")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # HTML 파일 로드
            page.goto(f"file://{html_file}")
            
            crawler = CoHouseCrawler(progress=None)
            
            # platform_specific_fields 추출
            ps_fields = crawler._extract_platform_specific_fields(page)
            
            # kv_pairs 추출 (간단한 테스트용)
            kv_pairs = {}
            
            # JSON 필드 생성
            json_data = crawler._filter_json_fields(kv_pairs, ps_fields)
            
            # JSON 구조 확인
            print("\n=== JSON 구조 확인 ===")
            print(f"최상위 키: {list(json_data.keys())}")
            
            # facilities 확인
            if "facilities" in json_data:
                print(f"\nFacilities: {json_data['facilities']}")
            else:
                print("\nFacilities: 없음")
            
            # company_info 확인
            if "company_info" in json_data:
                print(f"\nCompany Info: {json_data['company_info']}")
            else:
                print("\nCompany Info: 없음")
            
            # housing_specific 확인
            if "housing_specific" in json_data:
                print(f"\nHousing Specific: {json_data['housing_specific']}")
            else:
                print("\nHousing Specific: 없음")
            
            # building_details 확인
            if "building_details" in json_data:
                print(f"\nBuilding Details: {json_data['building_details']}")
            else:
                print("\nBuilding Details: 없음")
            
            # cohouse_text_extracted_info 확인
            if "cohouse_text_extracted_info" in json_data:
                print(f"\nCoHouse Text Extracted Info: {json_data['cohouse_text_extracted_info']}")
            else:
                print("\nCoHouse Text Extracted Info: 없음")
            
            # JSON 파일로 저장 (test_output 디렉토리에)
            output_dir = Path("backend/tests/test_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "test_cohouse_real_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"\n실제 데이터 JSON 저장됨: {output_file}")
            
            return json_data
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

def main():
    """메인 테스트 함수"""
    print("JSON 생성 테스트 시작")
    
    # 실제 데이터로 테스트
    test_sohouse_with_real_data()
    test_cohouse_with_real_data()
    
    # 테스트할 플랫폼들 (실제 URL이 있는 경우)
    platforms = ["sohouse", "cohouse", "youth"]
    
    for platform in platforms:
        try:
            test_json_generation(platform)
        except Exception as e:
            print(f"{platform} 테스트 실패: {e}")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()
