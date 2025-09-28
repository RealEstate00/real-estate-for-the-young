import requests
import xml.etree.ElementTree as ET
import csv
import time
import logging
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🔑 인증키 (환경변수에서 가져오기)
API_KEY = os.getenv('SEOUL_API_KEY')
if not API_KEY:
    logger.error("SEOUL_API_KEY 환경변수가 설정되지 않았습니다.")
    exit(1)

# 📋 다운로드할 서비스 목록
SERVICES = [
    "busStopLocationXyInfo",      # 버스정류장 위치정보
    "subwayStationMaster",        # 지하철역 마스터정보
    "ChildCareInfo",              # 어린이집 정보
    "childSchoolInfo",            # 유치원 정보
    "neisSchoolInfo",             # 초중고등학교 정보
    "SearchParkInfoService",      # 공원 정보
    "SearchSTNBySubwayLineInfo",  # 지하철역 정보
    "SebcCollegeInfoKor",         # 대학교 정보
    "StationAdresTelno",          # 지하철역 주소/전화번호
    "TbPharmacyOperateInfo"       # 약국 운영정보
]

TYPE = "xml"

# 💡 한 번에 가져올 데이터 수 (서울시 기준 max 1000 이하 권장)
PAGE_SIZE = 1000

def fetch_total_count(service):
    """전체 데이터 건수 조회"""
    url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/{TYPE}/{service}/1/5"
    try:
        logger.info(f"전체 건수 조회 중: {url}")
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        root = ET.fromstring(res.content)
        total = root.findtext(".//list_total_count")
        if total:
            logger.info(f"전체 건수: {total}")
            return int(total)
        else:
            logger.error("전체 건수를 찾을 수 없습니다.")
            return 0
    except requests.RequestException as e:
        logger.error(f"API 요청 실패: {e}")
        return 0
    except ET.ParseError as e:
        logger.error(f"XML 파싱 실패: {e}")
        return 0

def fetch_data(service, start_index, end_index):
    """지정된 범위의 데이터 조회"""
    url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/{TYPE}/{service}/{start_index}/{end_index}"
    try:
        logger.info(f"데이터 조회 중: {start_index}~{end_index}")
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        root = ET.fromstring(res.content)
        
        # API 오류 체크
        result = root.find(".//RESULT")
        if result is not None:
            code = result.findtext("CODE")
            message = result.findtext("MESSAGE")
            if code != "INFO-000":
                logger.error(f"API 오류: {code} - {message}")
                return []
        
        rows = []
        for row in root.iter("row"):
            row_data = {child.tag: child.text for child in row}
            rows.append(row_data)
        
        logger.info(f"조회된 데이터: {len(rows)}건")
        return rows
        
    except requests.RequestException as e:
        logger.error(f"API 요청 실패: {e}")
        return []
    except ET.ParseError as e:
        logger.error(f"XML 파싱 실패: {e}")
        return []

def save_to_csv(all_rows, filename):
    """데이터를 CSV 파일로 저장"""
    if not all_rows:
        logger.warning("저장할 데이터가 없습니다.")
        return False
    
    try:
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
            writer.writeheader()
            writer.writerows(all_rows)
        logger.info(f"총 {len(all_rows)}건 저장 완료: {filename}")
        return True
    except Exception as e:
        logger.error(f"CSV 저장 실패: {e}")
        return False

def download_service_data(service):
    """개별 서비스 데이터 다운로드"""
    logger.info(f"📡 {service} 데이터 수집 시작")
    
    # 전체 건수 조회
    total_count = fetch_total_count(service)
    if total_count == 0:
        logger.warning(f"⚠️ {service}: 데이터를 가져올 수 없습니다.")
        return False
    
    logger.info(f"🔍 {service} 전체 건수: {total_count}")

    # 데이터 수집
    all_rows = []
    for start in range(1, total_count + 1, PAGE_SIZE):
        end = min(start + PAGE_SIZE - 1, total_count)
        logger.info(f"📦 {service} {start} ~ {end} 데이터 수집 중...")
        
        rows = fetch_data(service, start, end)
        if rows:
            all_rows.extend(rows)
        else:
            logger.warning(f"⚠️ {service} {start}~{end} 범위 데이터 수집 실패")
        
        time.sleep(0.3)  # 과도한 요청 방지 (서울시 서버에 예의 있게)

    if not all_rows:
        logger.error(f"❌ {service}: 수집된 데이터가 없습니다.")
        return False

    # 출력 디렉토리 설정 (프로젝트 구조에 맞게)
    output_dir = Path(__file__).resolve().parents[3] / "data" / "public-api" / "openseoul"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일명에 타임스탬프 추가
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"seoul_{service}_{timestamp}.csv"
    output_path = output_dir / filename
    
    # CSV 저장
    if save_to_csv(all_rows, str(output_path)):
        logger.info(f"✅ {service} 데이터 수집 완료: {len(all_rows)}건")
        return True
    else:
        logger.error(f"❌ {service} CSV 저장 실패")
        return False

def main():
    """메인 실행 함수"""
    logger.info("🚀 서울시 공공데이터 수집 시작")
    
    success_count = 0
    total_count = len(SERVICES)
    
    for i, service in enumerate(SERVICES, 1):
        logger.info(f"📊 진행률: {i}/{total_count} - {service}")
        
        if download_service_data(service):
            success_count += 1
        
        logger.info("-" * 50)  # 구분선
    
    logger.info(f"🎉 전체 수집 완료: {success_count}/{total_count} 서비스 성공")

if __name__ == "__main__":
    main()
