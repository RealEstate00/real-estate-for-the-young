# -*- coding: utf-8 -*-
"""
행안부(주소) API 클라이언트 + 정규화 유틸
- Single source of truth for address normalization.
- English-only comments per team convention.

Docs: https://www.data.go.kr/data/15057017/openapi.do
"""

from __future__ import annotations
import os
import time
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

import requests

# 환경변수 로드
load_dotenv()


# ----- Public Exceptions ------------------------------------------------------
class AddressNormalizerError(Exception):
    """Raised when address normalization fails due to bad input or API error."""


# ----- Constants --------------------------------------------------------------
# Use the business endpoint (HTTPS). The public http://juso.go.kr also works,
# but the business endpoint is recommended for programmatic use.
JUSO_URL = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
JUSO_KEY = os.getenv("JUSO_API_KEY")


# ----- Internal helpers -------------------------------------------------------
def _extract_first_juso(payload: dict) -> Optional[dict]:
    """Return the first 'juso' dict from API response or None."""
    try:
        return payload["results"]["juso"][0]
    except Exception:
        return None

def _check_api_ok(payload: dict) -> Tuple[bool, str]:
    """Check the API common status block."""
    common = (payload.get("results") or {}).get("common") or {}
    code = common.get("errorCode")
    msg = common.get("errorMessage") or ""
    return (code == "0", msg)

def _to_float(v) -> Optional[float]:
    try:
        return float(v) if v != "" and v is not None else None
    except (TypeError, ValueError):
        return None

def _to_int(v) -> Optional[int]:
    try:
        return int(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


# ----- Client -----------------------------------------------------------------
class AddressAPI:
    """Thin client for the Juso API with retry & session reuse."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = JUSO_URL, timeout: int = 10):
        self.api_key = api_key or JUSO_KEY
        if not self.api_key:
            raise AddressNormalizerError(
                "JUSO_API_KEY is not set. Put it in your environment or .env."
            )
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def search(self, keyword: str, count_per_page: int = 1, current_page: int = 1, reverse: bool = False) -> dict:
        """Call the search endpoint and return parsed JSON (or raise)."""
        params = {
            "confmKey": self.api_key,
            "currentPage": current_page,
            "countPerPage": min(max(count_per_page, 1), 100),
            "keyword": keyword,
            "resultType": "json",
            # Helpful flags:
            "hstryYn": "Y",   # include changed history
            "relJibun": "Y",  # include related jibun
            "hemdNm": "Y",    # include emd (legal dong) name
        }
        
        # reverse=True일 때는 도로명주소 → 지번주소 변환을 위한 추가 파라미터
        if reverse:
            params["admCd"] = "Y"  # 행정구역코드 포함
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🏠 JUSO API 요청: {keyword}")
        logger.info(f"📋 JUSO API 요청 파라미터: {params}")
        
        resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
        logger.info(f"🔍 JUSO API 응답 상태: {resp.status_code}")
        logger.info(f"📄 JUSO API 전체 응답 내용:")
        logger.info(f"{resp.text}")
        
        resp.raise_for_status()
        data = resp.json()
        ok, msg = _check_api_ok(data)
        if not ok:
            logger.error(f"❌ JUSO API 오류: {msg}")
            logger.error(f"📄 전체 응답: {data}")
            raise AddressNormalizerError(f"Juso API error: {msg}")
        
        results_count = len(data.get('results', {}).get('juso', []))
        logger.info(f"✅ JUSO API 성공: {results_count}개 결과")
        
        # 결과 상세 정보 로깅
        if results_count > 0:
            first_result = data.get('results', {}).get('juso', [])[0]
            logger.info(f"📋 첫 번째 결과 상세:")
            logger.info(f"   - 도로명주소: {first_result.get('roadAddr', 'N/A')}")
            logger.info(f"   - 지번주소: {first_result.get('jibunAddr', 'N/A')}")
            logger.info(f"   - 시도: {first_result.get('siNm', 'N/A')}")
            logger.info(f"   - 시군구: {first_result.get('sggNm', 'N/A')}")
            logger.info(f"   - 읍면동: {first_result.get('emdNm', 'N/A')}")
            logger.info(f"   - 법정동코드: {first_result.get('bcode', 'N/A')}")
            logger.info(f"   - 좌표: ({first_result.get('entY', 'N/A')}, {first_result.get('entX', 'N/A')})")
        
        return data

    def normalize_one(self, address: str, retries: int = 2, backoff: float = 0.3, reverse: bool = False) -> dict:
        """
        Normalize a single raw address string into a canonical dict used by pipeline.

        Returns keys:
          - sido, sigungu, eupmyeon_dong, bcode
          - road_full, jibun_full
          - x (lon), y (lat)  # per API 'entX'/'entY'
        """
        if not address or not str(address).strip():
            raise AddressNormalizerError("Empty address")

        last_err = None
        for attempt in range(retries + 1):
            try:
                data = self.search(address, count_per_page=1, reverse=reverse)
                j = _extract_first_juso(data)
                if not j:
                    raise AddressNormalizerError("No match from Juso API")

                # Notes:
                # - entX/entY are coordinates returned by the API (WGS84 lon/lat).
                # - Some accounts/services may return different key names; adapt here if needed.
                # 괄호 안의 내용 제거 (예: "서울특별시 동대문구 천호대로 425 (장안동)" -> "서울특별시 동대문구 천호대로 425")
                road_addr = j.get("roadAddr", "")
                if road_addr and "(" in road_addr:
                    road_addr = road_addr.split("(")[0].strip()
                
                out = {
                    "sido": j.get("siNm"),
                    "sigungu": j.get("sggNm"),
                    "eupmyeon_dong": j.get("emdNm"),
                    "bcode": j.get("bcode"),
                    "road_full": road_addr,
                    "jibun_full": j.get("jibunAddr"),
                    "x": _to_float(j.get("entX")),  # longitude
                    "y": _to_float(j.get("entY")),  # latitude
                }
                # Minimal completeness check
                if not (out["road_full"] or out["jibun_full"]):
                    raise AddressNormalizerError("Juso result missing road/jibun address")
                return out
            except (requests.RequestException, AddressNormalizerError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(backoff * (attempt + 1))
                else:
                    raise

        # Should not reach here
        raise AddressNormalizerError(str(last_err))

    def normalize_batch(self, addresses: List[str], delay: float = 0.1) -> List[dict]:
        """Normalize multiple addresses; returns best-effort results."""
        out: List[dict] = []
        for i, addr in enumerate(addresses):
            try:
                out.append(self.normalize_one(addr))
            except AddressNormalizerError:
                # Keep a placeholder so caller can quarantine
                out.append(
                    {
                        "sido": None,
                        "sigungu": None,
                        "eupmyeon_dong": None,
                        "bcode": None,
                        "road_full": None,
                        "jibun_full": addr or None,
                        "x": None,
                        "y": None,
                    }
                )
            if delay > 0:
                time.sleep(delay)
        return out

# ----- Module-level convenience API ------------------------------------------
# Keep a single function used by the normalization hook to avoid importing the client everywhere.
def normalize_address(raw: str, reverse: bool = False) -> dict:
    """
    Convenience wrapper used by postprocess_enrich():
    returns the canonical dict consumed by the pipeline.
    
    Args:
        raw: 주소 문자열
        reverse: True면 도로명→지번, False면 지번→도로명
    """
    client = AddressAPI()
    return client.normalize_one(raw, reverse=reverse)
