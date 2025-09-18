"""
DataFrame을 csv 또는 PostgreSQL에 저장
"""
import pandas as pd
# from sqlalchemy import create_engine
# from sqlalchemy.exc import SQLAlchemyError
from . import config
import logging
import csv
from typing import List, Dict
import os  # 폴더 생성 및 경로 조작용
from datetime import date  # 오늘 날짜 얻기용
from pathlib import Path  # 경로 처리를 위한 pathlib

# 로깅 설정 (레벨은 필요시 config에서도 조정 가능)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def save_to_csv(data: List[Dict], source: str = "localdata"
                , service_name: str = None, path: str = None) -> None:
    """
    수집한 데이터를 CSV 파일로 저장합니다.
    
    - source에 따라 저장 폴더를 자동 분기
        - localdata → backend/data/public-api/localdata/
        - seoul     → backend/data/public-api/openseoul/

    매개변수:
        data (list[dict]): 저장할 데이터
        source (str): "localdata" 또는 "seoul"
        service_name (str): API 서비스 이름 (ex: ChildCareInfo)
        path (str): 저장 경로 (None이면 자동 생성)

    예:
        save_to_csv(data, source="seoul", service_name="ChildCareInfo")
    """
    if not data:
        print("📭 저장할 데이터가 비어 있습니다.")
        return

    # 자동 경로 지정
    if path is None:
        today = date.today().strftime("%Y%m%d")

        # 프로젝트 루트 디렉토리 기준으로 절대 경로 생성
        project_root = Path(__file__).parent.parent.parent.parent.parent
        base_folder = project_root / "backend" / "data" / "public-api"
        
        if source == "seoul":
            folder = base_folder / "openseoul"
        else:
            folder = base_folder / "localdata"

        os.makedirs(folder, exist_ok=True)

        # ✅ 서비스 이름 포함하여 파일명 구성
        if service_name:
            filename = f"{source}_{service_name}_{today}.csv"
        else:
            filename = f"{source}_{today}.csv"

        path = folder / filename

    # 필드 추출 (첫 row 기준)
    fieldnames = data[0].keys()

    # CSV 저장
    path_str = str(path)  # pathlib.Path를 문자열로 변환
    with open(path_str, mode="w", newline="", encoding=config.CSV_ENCODING) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    logger.info(f"✅ CSV 저장 완료: {path_str} ({len(data)}건)")


# 🔹 pandas DataFrame을 PostgreSQL DB로 저장하는 함수
def save_to_postgres(df: pd.DataFrame, table_name: str = None, if_exists: str = "append") -> None:
    """
    PostgreSQL DB에 DataFrame 저장 (에러 처리 및 로깅 포함)

    매개변수:
        df (pd.DataFrame): 저장할 데이터
        table_name (str): 저장할 테이블명 (None이면 config.TARGET_TABLE 사용)
        if_exists (str): "append", "replace", "fail"
    """
    if df.empty:
        logger.warning("❗ 저장하려는 DataFrame이 비어 있습니다. 저장하지 않음.")
        return

    if table_name is None:
        table_name = config.TARGET_TABLE

    try:
        # SQLAlchemy 엔진 생성
        engine = create_engine(config.PG_DSN)
        logger.info(f"📡 DB 연결 성공: {config.PG_DSN}")

        # DataFrame을 테이블로 저장
        df.to_sql(
            name=table_name,
            con=engine,
            schema=config.TARGET_SCHEMA,
            if_exists=if_exists,
            index=False
        )
        logger.info(f"✅ 데이터 저장 완료: {len(df)} rows → {table_name}")

    except SQLAlchemyError as e:
        logger.error(f"❌ DB 저장 중 오류 발생: {e}")
    except Exception as e:
        logger.exception(f"❗예상치 못한 오류 발생: {e}")
