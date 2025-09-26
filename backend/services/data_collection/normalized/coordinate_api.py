"""
VWorld API를 사용한 좌표 검색 모듈
"""

import requests
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

class VWorldCoordinateAPI:
    """VWorld API를 사용한 좌표 검색 클래스"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.vworld.kr/req/address"
    
    def get_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        주소로부터 좌표 정보 검색
        
        Args:
            address: 검색할 주소
            
        Returns:
            (위도, 경도) 튜플 또는 None
        """
        try:
            params = {
                'service': 'address',
                'request': 'getCoord',  # 공식 문서에 따르면 getCoord (대문자 C)
                'crs': 'epsg:4326',  # WGS84 좌표계
                'address': address,
                'format': 'json',
                'type': 'road',  # 도로명주소 검색
                'key': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 디버깅을 위한 응답 로그 (필요시 주석 해제)
            # logger.info(f"VWorld API 응답: {data}")
            
            if data.get('response', {}).get('status') == 'OK':
                result = data['response']['result']
                if result:
                    # result는 객체이므로 직접 접근
                    point = result.get('point', {})
                    x = float(point.get('x', 0))
                    y = float(point.get('y', 0))
                    
                    if x != 0 and y != 0:
                        return (y, x)  # VWorld는 (경도, 위도) 순서이므로 (위도, 경도)로 변환
            
            logger.warning(f"VWorld API 응답 없음: {address}")
            return None
            
        except Exception as e:
            logger.error(f"VWorld API 호출 오류: {e}")
            return None
