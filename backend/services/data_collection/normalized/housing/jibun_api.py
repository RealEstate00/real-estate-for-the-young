#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
===========================================
JUSO API 모듈 (JUSO API)
===========================================
JUSO API를 사용하여 도로명주소 및 지번주소 정보를 추출하는 모듈
"""

import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ----------------------------
# 1) JUSO API 클래스
# ----------------------------

class JusoAPI:
    """JUSO API 클래스 - 도로명주소 및 지번주소 정보 제공"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
    
    def search_address(self, address: str) -> Optional[Dict[str, str]]:
        """
        주소 검색 (도로명주소 및 지번주소 정보)
        
        Args:
            address: 검색할 주소
            
        Returns:
            주소 정보 딕셔너리 또는 None
        """
        try:
            # 주소 전처리
            processed_address = self._preprocess_address(address)
            
            # API 호출
            params = {
                'confmKey': self.api_key,
                'currentPage': 1,
                'countPerPage': 10,
                'keyword': processed_address,
                'resultType': 'json'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 디버깅을 위한 로그 추가
            logger.info(f"[DEBUG] JUSO API 응답 분석:")
            logger.info(f"  results 존재: {bool(data.get('results'))}")
            if data.get('results'):
                common = data['results'].get('common', {})
                error_code = common.get('errorCode')
                logger.info(f"  errorCode: {error_code} (타입: {type(error_code)})")
                logger.info(f"  errorCode == '0': {error_code == '0'}")
                logger.info(f"  str(errorCode) == '0': {str(error_code) == '0'}")
                
                juso_list = data['results'].get('juso', [])
                logger.info(f"  juso 리스트 개수: {len(juso_list)}")
            
            if data.get('results') and str(data['results'].get('common', {}).get('errorCode')) == '0':
                juso_list = data['results'].get('juso', [])
                if juso_list:
                    logger.info(f"[DEBUG] JUSO API 성공: {len(juso_list)}개 결과")
                    return self._parse_juso_response(juso_list[0])
                else:
                    logger.warning(f"[DEBUG] JUSO API: juso 리스트가 비어있음")
            else:
                logger.warning(f"[DEBUG] JUSO API: 조건 불만족")
            
            logger.warning(f"JUSO API 응답 없음: {address}")
            return None
            
        except Exception as e:
            logger.error(f"JUSO API 호출 오류: {e}")
            return None
    
    def get_coordinates(self, adm_cd: str, rn_mgt_sn: str, udrt_yn: str, buld_mnnm: str, buld_slno: str) -> Optional[Dict[str, str]]:
        """
        좌표 검색 (JUSO 좌표 API 사용)
        
        Args:
            adm_cd: 행정구역코드
            rn_mgt_sn: 도로명코드
            udrt_yn: 지하여부 (0: 지상, 1: 지하)
            buld_mnnm: 건물본번
            buld_slno: 건물부번
            
        Returns:
            좌표 정보 딕셔너리 또는 None
        """
        try:
            # 좌표 API 호출
            coord_url = "https://business.juso.go.kr/addrlink/addrCoordApi.do"
            params = {
                'confmKey': self.api_key,
                'admCd': adm_cd,
                'rnMgtSn': rn_mgt_sn,
                'udrtYn': udrt_yn,
                'buldMnnm': buld_mnnm,
                'buldSlno': buld_slno,
                'resultType': 'json'
            }
            
            response = requests.get(coord_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 디버깅을 위한 로그 추가
            logger.info(f"좌표 API 호출 파라미터: {params}")
            logger.info(f"좌표 API 응답: {data}")
            
            if data.get('results') and str(data['results'].get('common', {}).get('errorCode')) == '0':
                juso_list = data['results'].get('juso', [])
                if juso_list:
                    return self._parse_coord_response(juso_list[0])
            
            # 에러 메시지 로깅
            error_code = data.get('results', {}).get('common', {}).get('errorCode', '')
            error_message = data.get('results', {}).get('common', {}).get('errorMessage', '')
            logger.warning(f"JUSO 좌표 API 응답 없음: {adm_cd}, 에러코드: {error_code}, 메시지: {error_message}")
            return None
            
        except Exception as e:
            logger.error(f"JUSO 좌표 API 호출 오류: {e}")
            return None
    
    def _preprocess_address(self, address: str) -> str:
        """주소 전처리 - 도로명주소와 지번주소 분리 처리"""
        if not address:
            return address
        
        import re
        
        # 괄호와 그 안의 내용 제거 (예: "(구산동, 함께주택5호)" -> "")
        address = re.sub(r'\([^)]*\)', '', address)
        
        # 불필요한 정보 제거
        address = address.replace('(주)', '').replace('(유)', '').replace('(사)', '')
        address = address.replace('주식회사', '').replace('유한회사', '').replace('사단법인', '')
        
        # "~" 기호와 그 뒤의 내용 제거 (예: "98-46 1 ~" -> "98-46")
        address = re.sub(r'\s+\d+\s*~.*$', '', address)
        
        # 마지막에 오는 점(.) 제거
        address = re.sub(r'\.\s*$', '', address)
        
        # 도로명주소와 지번주소 분리 처리
        # 예: "서울특별시 은평구 통일로915 갈현동 391-46" -> "서울특별시 은평구 통일로915"
        # 도로명주소 패턴: "로" + 숫자로 끝나는 부분
        road_pattern = r'^(.+?로\d+)\s+[가-힣]+동\s+\d+-\d+'
        match = re.match(road_pattern, address)
        if match:
            address = match.group(1)
            logger.info(f"도로명주소 추출: {address}")
        else:
            # 도로명주소 패턴 2: "길" + 공백 + 숫자 (나길, 가길 등)
            # 예: "남부순환로105나길 24" -> "남부순환로105나길 24"
            road_pattern2 = r'^(.+?길\s+\d+)'
            match = re.match(road_pattern2, address)
            if match:
                address = match.group(1)
                logger.info(f"도로명주소 추출 (길 패턴): {address}")
            else:
                # 도로명주소 패턴 3: "길" + 숫자-숫자 (마길, 가길 등)
                # 예: "경인로33마길4-7" -> "경인로33마길4-7"
                road_pattern3 = r'^(.+?길\d+-\d+)'
                match = re.match(road_pattern3, address)
                if match:
                    address = match.group(1)
                    logger.info(f"도로명주소 추출 (길-하이픈 패턴): {address}")
                else:
                    # 지번주소 패턴: "동" + 숫자-숫자로 끝나는 부분
                    jibun_pattern = r'^(.+?동\s+\d+-\d+)'
                    match = re.match(jibun_pattern, address)
                    if match:
                        address = match.group(1)
                        logger.info(f"지번주소 추출: {address}")
                    else:
                        # 기존 로직: 숫자로 끝나는 부분까지만 추출
                        number_pattern = r'^(.+?[0-9]+-[0-9]+)'
                        match = re.match(number_pattern, address)
                        if match:
                            address = match.group(1)
                        else:
                            # 단순히 숫자로 끝나는 부분까지만 추출
                            number_pattern2 = r'^(.+?[0-9]+)'
                            match = re.match(number_pattern2, address)
                            if match:
                                address = match.group(1)
        
        # 연속된 공백을 하나로 정리
        address = re.sub(r'\s+', ' ', address).strip()
        
        return address
    
    def _parse_juso_response(self, juso_data: Dict) -> Dict[str, str]:
        """JUSO API 응답 파싱"""
        try:
            # 도로명주소 정보
            road_addr = juso_data.get('roadAddr', '')
            road_addr_part1 = juso_data.get('roadAddrPart1', '')
            road_addr_part2 = juso_data.get('roadAddrPart2', '')
            
            # 지번주소 정보
            jibun_addr = juso_data.get('jibunAddr', '')
            
            # 행정구역 정보
            si_nm = juso_data.get('siNm', '')
            sgg_nm = juso_data.get('sggNm', '')
            emd_nm = juso_data.get('emdNm', '')
            li_nm = juso_data.get('liNm', '')
            
            # 도로명 정보
            rn = juso_data.get('rn', '')
            buld_mnnm = juso_data.get('buldMnnm', '')
            buld_slno = juso_data.get('buldSlno', '')
            
            # 기타 정보
            zip_no = juso_data.get('zipNo', '')
            adm_cd = juso_data.get('admCd', '')
            rn_mgt_sn = juso_data.get('rnMgtSn', '')
            bd_mgt_sn = juso_data.get('bdMgtSn', '')
            
            return {
                # 도로명주소
                'road_addr': road_addr,
                'road_addr_part1': road_addr_part1,
                'road_addr_part2': road_addr_part2,
                'road_name': rn,
                'building_main_no': buld_mnnm,
                'building_sub_no': buld_slno,
                
                # 지번주소
                'jibun_addr': jibun_addr,
                
                # 행정구역
                'si_nm': si_nm,
                'sgg_nm': sgg_nm,
                'emd_nm': emd_nm,
                'li_nm': li_nm,
                
                # 코드 정보
                'zip_no': zip_no,
                'adm_cd': adm_cd,
                'rn_mgt_sn': rn_mgt_sn,
                'bd_mgt_sn': bd_mgt_sn
            }
            
        except Exception as e:
            logger.error(f"JUSO API 응답 파싱 오류: {e}")
            return {}
    
    def _parse_coord_response(self, coord_data: Dict) -> Dict[str, str]:
        """JUSO 좌표 API 응답 파싱"""
        try:
            # 좌표 정보 추출
            ent_x = coord_data.get('entX', '')
            ent_y = coord_data.get('entY', '')
            bd_nm = coord_data.get('bdNm', '')
            
            # 기타 정보
            adm_cd = coord_data.get('admCd', '')
            rn_mgt_sn = coord_data.get('rnMgtSn', '')
            bd_mgt_sn = coord_data.get('bdMgtSn', '')
            udrt_yn = coord_data.get('udrtYn', '')
            buld_mnnm = coord_data.get('buldMnnm', '')
            buld_slno = coord_data.get('buldSlno', '')
            
            return {
                # 좌표 정보
                'ent_x': ent_x,
                'ent_y': ent_y,
                'building_name': bd_nm,
                
                # 기타 정보
                'adm_cd': adm_cd,
                'rn_mgt_sn': rn_mgt_sn,
                'bd_mgt_sn': bd_mgt_sn,
                'udrt_yn': udrt_yn,
                'buld_mnnm': buld_mnnm,
                'buld_slno': buld_slno
            }
            
        except Exception as e:
            logger.error(f"JUSO 좌표 API 응답 파싱 오류: {e}")
            return {}
