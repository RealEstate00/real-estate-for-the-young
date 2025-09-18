"""
API 결과(json/xml)를 pandas.DataFrame으로 정제하는 로직
"""
import pandas as pd
from typing import List, Dict
import xml.etree.ElementTree as ET


def normalize_localdata(raw_data: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    df["source"] = "localdata"   # 출처 기록용 소스 컬럼
    return df


def flatten_json_rows(data: list[dict]) -> list[dict]:
    # JSON 전용 평탄화 함수
    return [row for row in data if isinstance(row, dict)]


def flatten_xml_rows(root: ET.Element) -> list[dict]:
    # XML 전용 평탄화 함수
    return [
        {child.tag: child.text for child in elem}
        for elem in root.findall(".//row")
    ]