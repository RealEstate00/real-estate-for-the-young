# pipeline.py
# 데이터 수집부터 저장까지 전체 파이프라인을 정의

from .config import SEOUL_API_KEY, LOCALDATA_API_KEY
from .api_client import LocalDataClient, SeoulOpenDataClient  # API 클라이언트 임포트
from .transform import flatten_xml_rows, flatten_json_rows     # 데이터 정리 함수 임포트
from .db import save_to_csv, save_to_postgres                  # 저장 함수 임포트
import logging


# ========== 1. 로컬데이터 포털 파이프라인 ==========
def run_localdata_pipeline(
    start_date=None,
    end_date=None,
    save_csv=True,
    save_db=False
):
    """
    로컬데이터 포털 파이프라인 실행
    - 변동분 데이터를 조회해서 CSV나 DB에 저장
    """
    client = LocalDataClient(api_key=LOCALDATA_API_KEY)
    parsed_data = client.fetch_delta_data(start_date=start_date, end_date=end_date) 

    if save_csv:
        save_to_csv(parsed_data, source="localdata")  # 파일로 저장
    if save_db:
        save_to_postgres(parsed_data)


# ========== 2. 서울 열린데이터광장 파이프라인 ==========
def run_seoul_pipeline(
    start=1,
    end=1000,
    service_name: str = None,
    save_csv=True,
    save_db=False,
):
    """
    서울 열린데이터광장 파이프라인 실행
    - 특정 범위(start~end)의 데이터를 조회해서 CSV나 DB에 저장
    """
    logging.info(f"[INFO] 서울 API 수집 - {service_name} 시작...")

    client = SeoulOpenDataClient(api_key=SEOUL_API_KEY)  # 인증키와 서비스 이름이 설정된 클라이언트 생성
    raw_data = client.fetch_path_data(start=start, end=end, service_name=service_name)  # JSON 데이터 호출
    parsed_data = flatten_json_rows(raw_data)  # JSON 내부 리스트를 평탄화

    if save_csv:
        save_to_csv(parsed_data, source="seoul", service_name=service_name)      # 서울 열린데이터광장용
    if save_db:
        save_to_postgres(parsed_data)


# 이 파일은 run.py에서 불러와서 실행하게 됨
