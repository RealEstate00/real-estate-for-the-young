"""
main.py - 간단하고 명확한 크롤링 실행 파일

🎯 핵심 기능:
1. test_crawl(): 2개 주택 테스트 (모든 CSV 생성)
2. main_crawl(): 모든 주택 실행 (모든 CSV 생성)

📊 생성되는 CSV 파일들:
✅ listing.csv: 목록 페이지 상세정보 (9개 컬럼)
✅ overview.csv: 상세소개 정보
✅ floorplan.csv: 평면도 이미지
✅ movein.csv: 입주현황
✅ location.csv: 위치정보
✅ amenities.csv: 편의시설
✅ about.csv: 사업자정보
"""

from src.driver import get_driver, safe_quit
from src.listing import collect_house_links
from src.storage import save_to_csv, add_timestamp
from src.detail import collect_details
import time


def test_crawl():
    """
    🧪 테스트 크롤링 (2개 주택)
    
    모든 CSV 파일을 생성하여 크롤링 시스템이 정상 작동하는지 확인
    """
    print("=" * 60)
    print("🧪 테스트 크롤링 시작 (2개 주택, 모든 정보)")
    print("=" * 60)
    
    driver = get_driver()
    
    try:
        # 1단계: 주택 링크 수집
        print("\n🔍 1단계: 주택 목록 수집")
        house_links = collect_house_links(driver, max_pages=None)
        
        if not house_links:
            print("❌ 수집된 주택이 없습니다.")
            return
        
        # 테스트용으로 2개만 선택
        test_houses = house_links[:11]
        print(f"🧪 테스트 대상: {len(test_houses)}개 주택")
        
        # 목록 데이터 저장
        save_to_csv(add_timestamp(test_houses), "listing.csv")
        print(f"💾 listing.csv 저장 완료")
        
        # 2단계: 각 주택의 전체 상세 정보 수집
        print(f"\n🔍 2단계: 전체 상세 정보 수집")
        
        all_overview = []
        all_floorplan = []
        all_movein = []
        all_location = []
        all_amenities = []
        all_about = []
        
        for i, house in enumerate(test_houses, 1):
            house_name = house["주택명"]
            house_id = house["house_id"]
            
            print(f"\n[{i}/{len(test_houses)}] 📍 '{house_name}' 처리 중...")
            
            try:
                # JavaScript로 상세페이지 이동
                driver.execute_script(f"modify({house_id});")
                time.sleep(3)
                
                # 모든 섹션 데이터 수집
                details = collect_details(driver, house_name)
                
                # 섹션별 데이터 분류
                if details.get("overview"):
                    all_overview.append(details["overview"])
                
                if details.get("floorplan"):
                    all_floorplan.extend(details["floorplan"])
                
                if details.get("movein"):
                    all_movein.extend(details["movein"])
                
                if details.get("location"):
                    all_location.append(details["location"])
                
                if details.get("amenities"):
                    all_amenities.append(details["amenities"])
                
                if details.get("about"):
                    all_about.append(details["about"])
                
                print(f"  ✅ '{house_name}' 완료!")
                
            except Exception as e:
                print(f"  ❌ '{house_name}' 실패: {e}")
                continue
        
        # 3단계: 모든 CSV 파일 저장
        print(f"\n💾 3단계: CSV 파일 저장")
        
        csv_files = []
        
        if all_overview:
            save_to_csv(add_timestamp(all_overview), "overview.csv")
            csv_files.append(f"overview.csv ({len(all_overview)}개)")
        
        if all_floorplan:
            save_to_csv(add_timestamp(all_floorplan), "floorplan.csv")
            csv_files.append(f"floorplan.csv ({len(all_floorplan)}개)")
        
        if all_movein:
            save_to_csv(add_timestamp(all_movein), "movein.csv")
            csv_files.append(f"movein.csv ({len(all_movein)}개)")
        
        if all_location:
            save_to_csv(add_timestamp(all_location), "location.csv")
            csv_files.append(f"location.csv ({len(all_location)}개)")
        
        if all_amenities:
            save_to_csv(add_timestamp(all_amenities), "amenities.csv")
            csv_files.append(f"amenities.csv ({len(all_amenities)}개)")
        
        if all_about:
            save_to_csv(add_timestamp(all_about), "about.csv")
            csv_files.append(f"about.csv ({len(all_about)}개)")
        
        print(f"\n🎉 테스트 크롤링 완료!")
        print(f"📊 처리된 주택: {len(test_houses)}개")
        print(f"📁 생성된 파일:")
        for file_info in csv_files:
            print(f"  - {file_info}")
        
    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생: {e}")
        
    finally:
        safe_quit(driver)


def main_crawl():
    """
    🚀 메인 크롤링 (모든 주택)
    
    모든 주택의 모든 정보를 수집하여 완전한 데이터셋 생성
    """
    print("=" * 60)
    print("🚀 메인 크롤링 시작 (모든 주택, 모든 정보)")
    print("=" * 60)
    
    driver = get_driver()
    
    try:
        # 1단계: 주택 링크 수집
        print("\n🔍 1단계: 주택 목록 수집")
        house_links = collect_house_links(driver, max_pages=None)
        
        if not house_links:
            print("❌ 수집된 주택이 없습니다.")
            return
        
        print(f"🏠 총 {len(house_links)}개 주택 발견")
        
        # 목록 데이터 저장
        save_to_csv(add_timestamp(house_links), "listing.csv")
        print(f"💾 listing.csv 저장 완료")
        
        # 2단계: 각 주택의 전체 상세 정보 수집
        print(f"\n🔍 2단계: 전체 상세 정보 수집")
        
        all_overview = []
        all_floorplan = []
        all_movein = []
        all_location = []
        all_amenities = []
        all_about = []
        
        for i, house in enumerate(house_links, 1):
            house_name = house["주택명"]
            house_id = house["house_id"]
            
            print(f"\n[{i}/{len(house_links)}] 📍 '{house_name}' 처리 중...")
            
            try:
                # JavaScript로 상세페이지 이동
                driver.execute_script(f"modify({house_id});")
                time.sleep(3)
                
                # 모든 섹션 데이터 수집
                details = collect_details(driver, house_name)
                
                # 섹션별 데이터 분류
                if details.get("overview"):
                    all_overview.append(details["overview"])
                
                if details.get("floorplan"):
                    all_floorplan.extend(details["floorplan"])
                
                if details.get("movein"):
                    all_movein.extend(details["movein"])
                
                if details.get("location"):
                    all_location.append(details["location"])
                
                if details.get("amenities"):
                    all_amenities.append(details["amenities"])
                
                if details.get("about"):
                    all_about.append(details["about"])
                
                print(f"  ✅ '{house_name}' 완료!")
                time.sleep(1)  # 서버 부하 방지
                
            except Exception as e:
                print(f"  ❌ '{house_name}' 실패: {e}")
                continue
        
        # 3단계: 모든 CSV 파일 저장
        print(f"\n💾 3단계: CSV 파일 저장")
        
        csv_files = []
        
        if all_overview:
            save_to_csv(add_timestamp(all_overview), "overview.csv")
            csv_files.append(f"overview.csv ({len(all_overview)}개)")
        
        if all_floorplan:
            save_to_csv(add_timestamp(all_floorplan), "floorplan.csv")
            csv_files.append(f"floorplan.csv ({len(all_floorplan)}개)")
        
        if all_movein:
            save_to_csv(add_timestamp(all_movein), "movein.csv")
            csv_files.append(f"movein.csv ({len(all_movein)}개)")
        
        if all_location:
            save_to_csv(add_timestamp(all_location), "location.csv")
            csv_files.append(f"location.csv ({len(all_location)}개)")
        
        if all_amenities:
            save_to_csv(add_timestamp(all_amenities), "amenities.csv")
            csv_files.append(f"amenities.csv ({len(all_amenities)}개)")
        
        if all_about:
            save_to_csv(add_timestamp(all_about), "about.csv")
            csv_files.append(f"about.csv ({len(all_about)}개)")
        
        print(f"\n🎉 메인 크롤링 완료!")
        print(f"📊 처리된 주택: {len(house_links)}개")
        print(f"📁 생성된 파일:")
        for file_info in csv_files:
            print(f"  - {file_info}")
        
    except Exception as e:
        print(f"\n💥 크롤링 중 오류 발생: {e}")
        
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            test_crawl()
        elif command == "main":
            main_crawl()
        else:
            print("❌ 잘못된 명령어입니다.")
            print("📖 사용법:")
            print("  python main.py test  # 🧪 2개 주택 테스트")
            print("  python main.py main  # 🚀 모든 주택 크롤링")
    else:
        print("📖 사용법:")
        print("  python main.py test  # 🧪 2개 주택 테스트")
        print("  python main.py main  # 🚀 모든 주택 크롤링")


# 💡 사용 가이드:
"""
🎯 간단한 사용법:

1️⃣ 테스트 (2개 주택):
   python main.py test

2️⃣ 실제 크롤링 (모든 주택):
   python main.py main

📊 생성되는 파일:
- listing.csv: 목록 상세정보
- overview.csv: 상세소개
- floorplan.csv: 평면도 이미지
- movein.csv: 입주현황
- location.csv: 위치정보  
- amenities.csv: 편의시설
- about.csv: 사업자정보
"""
