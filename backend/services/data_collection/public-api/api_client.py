"""
- 로컬데이터 포털 및 서울열린데이터광장 API 요청 모듈
- config.py 설정 기반으로 동작
"""
from .config import (
    build_localdata_url,
    build_seoul_url,
    LOCALDATA_DELTA_START_KEY,
    LOCALDATA_DELTA_END_KEY,
    LOCALDATA_LOCALCODE_KEY,
    LOCALDATA_DEFAULT_PAGE_SIZE,
    LOCALDATA_DEFAULT_MAX_PAGES,
    SEOUL_DEFAULT_START,
    SEOUL_DEFAULT_END,
    CSV_DIR_LOCALDATA,
    CSV_DIR_OPENSEOUL,
    CSV_ENCODING
)

import requests
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class BaseAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _request_with_retry(self, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> requests.Response:
        for attempt in range(1, 4):  # 최대 3회 재시도
            try:
                response = requests.get(url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                return response
            except Exception as e:
                logger.warning(f"[시도 {attempt}/3] 요청 실패: {e}")
                if attempt == 3:
                    raise
                time.sleep(2.0 ** (attempt - 1))


class LocalDataClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.api_type = "TO0"
        self.default_page_size = LOCALDATA_DEFAULT_PAGE_SIZE
        self.default_max_pages = LOCALDATA_DEFAULT_MAX_PAGES

    def _fetch_single_page(self, url: str, params: Dict[str, Any], page: int) -> List[Dict[str, Any]]:
        response = self._request_with_retry(url, params=params)

        # 👉 응답이 JSON이 아닐 수 있으므로 방어
        try:
            json_data = response.json()
        except ValueError:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            error_msg = root.findtext(".//message") or "알 수 없는 오류"
            logger.error(f"[🚫 JSON 디코딩 실패] XML 응답 메시지: {error_msg}")
            return []

        # 👉 정상 JSON 응답인 경우 계속 진행
        if 'records' not in json_data:
            logger.warning(f"페이지 {page}: 'records' 키 없음. 전체 응답: {json_data}")
            return []

        return json_data['records']



    def fetch_delta_data(self, start_date: str = None, end_date: str = None,
                        local_code: str = None, page_size: int = None,
                        max_pages: int = None) -> List[Dict[str, Any]]:
        from .config import default_delta_range

        if start_date is None or end_date is None:
            start_date, end_date = default_delta_range()
            logger.info(f"날짜 미지정으로 기본 범위 사용: {start_date} ~ {end_date}")
        if page_size is None:
            page_size = self.default_page_size
        if max_pages is None:
            max_pages = self.default_max_pages

        url = build_localdata_url(self.api_type)
        all_data = []

        logger.info(f"로컬데이터 변동분 조회 시작")
        logger.info(f"  - 기간: {start_date} ~ {end_date}")
        logger.info(f"  - 지자체 코드: {local_code or '전국'}")
        logger.info(f"  - 페이지 크기: {page_size}, 최대 페이지: {max_pages}")

        for page in range(1, max_pages + 1):
            logger.info(f"페이지 {page}/{max_pages} 조회 중...")
            params = {
                "authKey": self.api_key,
                LOCALDATA_DELTA_START_KEY: start_date,
                LOCALDATA_DELTA_END_KEY: end_date,
                "pageSize": page_size,
                "pageIndex": page
            }
            if local_code:
                params[LOCALDATA_LOCALCODE_KEY] = local_code

            page_data = self._fetch_single_page(url, params, page)

            if not page_data:
                logger.info(f"페이지 {page}에서 데이터가 없어 조회 종료")
                break

            all_data.extend(page_data)
            logger.info(f"페이지 {page} 완료: {len(page_data)}건 수집 (누적: {len(all_data)}건)")

            if len(page_data) < page_size:
                logger.info(f"페이지 {page}가 마지막 페이지 (데이터 {len(page_data)}개 < 페이지 크기 {page_size})")
                break

        logger.info(f"로컬데이터 변동분 조회 완료: 총 {len(all_data)}건")
        return all_data


class SeoulOpenDataClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(api_key)

    def fetch_path_data(self, service_name: str = None, start: int = SEOUL_DEFAULT_START
                        , end: int = SEOUL_DEFAULT_END) -> List[Dict[str, Any]]:
        url = build_seoul_url(service_name=service_name, start=start, end=end)
        response = self._request_with_retry(url)
        
        # XML 응답 처리
        if response.text.strip().startswith('<'):
            logger.error(f"API 응답이 XML 형식입니다. API 키를 확인해주세요: {response.text[:200]}")
            return []
        
        json_data = response.json()

        service_key = next(iter(json_data))
        records = json_data[service_key].get("row", [])

        if not isinstance(records, list):
            logger.warning(f"예상치 못한 응답 형식: {records}")
            return []

        return records