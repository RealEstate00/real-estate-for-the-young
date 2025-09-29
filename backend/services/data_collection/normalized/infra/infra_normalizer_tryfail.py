#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
인프라 데이터 재처리 모듈
실패한 주소 정규화 데이터를 재처리하여 완전한 JSON 데이터 생성
"""

import pandas as pd
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from backend.services.data_collection.normalized.infra.infra_normalizer_NoJusoAPI import InfraNormalizer

logger = logging.getLogger(__name__)

class InfraNormalizerRetry:
    """인프라 데이터 재처리 클래스"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.normalizer = InfraNormalizer(data_dir)
        self.retry_facilities: List[Dict] = []
        self.retry_failed_addresses: List[Dict] = []
    
    def _get_next_facility_id(self, facility_type: str, output_dir: Path) -> str:
        """기존 파일에서 마지막 ID를 찾아서 다음 ID 생성"""
        prefix = self.normalizer.facility_id_prefix_map.get(facility_type, 'fac')
        facilities_file = output_dir / "public_facilities.jsonl"
        
        if not facilities_file.exists():
            return f"{prefix}0001"
        
        # 파일에서 마지막 ID 찾기
        last_id = None
        with open(facilities_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if data.get('facility_id', '').startswith(prefix):
                        last_id = data['facility_id']
        
        if not last_id:
            return f"{prefix}0001"
        
        # 마지막 ID에서 번호 추출하여 다음 번호 생성
        last_num = int(last_id.replace(prefix, ''))
        next_num = last_num + 1
        
        return f"{prefix}{next_num:04d}"
    
    def _load_existing_failed_addresses(self, output_dir: Path) -> List[Dict]:
        """기존 실패 데이터 로드"""
        failed_file = output_dir / "failed_addresses.jsonl"
        existing_failed = []
        
        if failed_file.exists():
            with open(failed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        existing_failed.append(json.loads(line))
        
        return existing_failed

    def _remove_successful_from_failed(self, output_dir: Path, success_names: List[str]):
        """성공한 시설들을 실패 목록에서 제거"""
        existing_failed = self._load_existing_failed_addresses(output_dir)
        
        # 성공한 시설들 제외
        remaining_failed = [
            failed for failed in existing_failed 
            if failed['facility_name'] not in success_names
        ]
        
        # 실패 파일 업데이트 (덮어쓰기)
        failed_file = output_dir / "failed_addresses.jsonl"
        with open(failed_file, 'w', encoding='utf-8') as f:
            for failed in remaining_failed:
                f.write(json.dumps(failed, ensure_ascii=False) + '\n')
    
    def retry_failed_addresses_from_jsonl(self, failed_jsonl_path: Path, output_dir: Path) -> Dict[str, List[Dict]]:
        """JSONL 파일에서 실패한 주소들을 읽어서 재정규화"""
        
        if not failed_jsonl_path.exists():
            logger.error(f"실패 데이터 파일이 존재하지 않습니다: {failed_jsonl_path}")
            return {"retry_facilities": [], "retry_failed_addresses": []}
        
        logger.info(f"실패 데이터 재처리 시작: {failed_jsonl_path}")
        
        retry_facilities = []
        retry_failed_addresses = []
        
        # progress.jsonl 파일 경로 설정
        progress_file = output_dir / "progress.jsonl"
        
        # JSONL 파일을 한 줄씩 읽기 (메모리 효율적)
        with open(failed_jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    failed_data = json.loads(line.strip())
                    
                    # 원본 파일에서 해당 행만 로드
                    original_file = failed_data['original_file']
                    row_index = failed_data['original_row_index']
                    
                    logger.info(f"재처리 [{line_num}]: {failed_data['facility_name']} - {failed_data['address_raw']}")
                    
                    # 원본 CSV에서 해당 행만 읽기
                    df = pd.read_csv(original_file, skiprows=range(1, row_index+1), nrows=1)
                    original_row = df.iloc[0]
                    
                    # 주소 정규화 재시도
                    address_info = self.normalizer._normalize_address(
                        failed_data['address_raw'], 
                        failed_data['facility_name'], 
                        failed_data['facility_type']
                    )
                    
                    # progress.jsonl에 기록 저장
                    progress_data = {
                        'timestamp': datetime.now().isoformat(),
                        'operation': 'retry_failed_address',
                        'line_number': line_num,
                        'facility_name': failed_data['facility_name'],
                        'facility_type': failed_data['facility_type'],
                        'address_raw': failed_data['address_raw'],
                        'original_file': original_file,
                        'original_row_index': row_index,
                        'success': address_info.get('normalization_success', False),
                        'address_nm': address_info.get('address_nm'),
                        'lat': address_info.get('lat'),
                        'lon': address_info.get('lon'),
                        'error_reason': failed_data.get('error_reason', '') if not address_info.get('normalization_success', False) else None
                    }
                    
                    # progress.jsonl에 추가
                    with open(progress_file, 'a', encoding='utf-8') as pf:
                        pf.write(json.dumps(progress_data, ensure_ascii=False) + '\n')
                    
                    if address_info.get('normalization_success', False):  # 성공한 경우
                        # 완전한 시설 데이터 구성
                        facility_data = self._build_complete_facility_data(
                            failed_data['facility_type'], 
                            original_row, 
                            address_info
                        )
                        retry_facilities.append(facility_data)
                        logger.info(f"✅ 재정규화 성공: {failed_data['facility_name']}")
                    else:
                        # 여전히 실패
                        retry_failed_addresses.append(failed_data)
                        logger.warning(f"❌ 재정규화 실패: {failed_data['facility_name']}")
                        
                except Exception as e:
                    logger.error(f"재처리 중 오류 (라인 {line_num}): {e}")
                    
                    # 오류도 progress.jsonl에 기록
                    error_progress_data = {
                        'timestamp': datetime.now().isoformat(),
                        'operation': 'retry_failed_address',
                        'line_number': line_num,
                        'facility_name': failed_data.get('facility_name', '') if 'failed_data' in locals() else '',
                        'facility_type': failed_data.get('facility_type', '') if 'failed_data' in locals() else '',
                        'address_raw': failed_data.get('address_raw', '') if 'failed_data' in locals() else '',
                        'original_file': failed_data.get('original_file', '') if 'failed_data' in locals() else '',
                        'original_row_index': failed_data.get('original_row_index', -1) if 'failed_data' in locals() else -1,
                        'success': False,
                        'error_reason': str(e)
                    }
                    
                    with open(progress_file, 'a', encoding='utf-8') as pf:
                        pf.write(json.dumps(error_progress_data, ensure_ascii=False) + '\n')
                    
                    continue
        
        logger.info(f"재처리 완료: 성공 {len(retry_facilities)}개, 실패 {len(retry_failed_addresses)}개")
        
        return {
            "retry_facilities": retry_facilities,
            "retry_failed_addresses": retry_failed_addresses
        }
    
    def _build_complete_facility_data(self, facility_type: str, original_row: pd.Series, 
                                     address_info: Dict) -> Dict:
        """원본 CSV 데이터와 정규화된 주소 정보로 완전한 시설 데이터 구성"""
        
        if facility_type == 'park':
            return {
                'facility_id': self.normalizer._generate_facility_id('park'),
                'cd': self.normalizer._get_facility_cd('park'),
                'name': original_row.get('P_PARK', ''),
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'] or self.normalizer._safe_float(original_row.get('LATITUDE')),
                'lon': address_info['lon'] or self.normalizer._safe_float(original_row.get('LONGITUDE')),
                'phone': original_row.get('P_ADMINTEL', ''),
                'website': original_row.get('TEMPLATE_URL', ''),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    'description': original_row.get('P_LIST_CONTENT', ''),
                    'area': self.normalizer._safe_float(original_row.get('AREA')),
                    'open_date': original_row.get('OPEN_DT', ''),
                    'main_equipment': original_row.get('MAIN_EQUIP', ''),
                    'main_plants': original_row.get('MAIN_PLANTS', ''),
                    'guidance': original_row.get('GUIDANCE', ''),
                    'visit_road': original_row.get('VISIT_ROAD', ''),
                    'use_refer': original_row.get('USE_REFER', '')
                },
                'data_source': 'openseoul'
            }
        elif facility_type == 'gym':
            return {
                'facility_id': self.normalizer._generate_facility_id('gym'),
                'cd': self.normalizer._get_facility_cd('gym'),
                'name': original_row.get('시설명', ''),
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': original_row.get('연락처', ''),
                'website': original_row.get('홈페이지', ''),
                'operating_hours': f"평일: {original_row.get('운영시간_평일', '')}, 주말: {original_row.get('운영시간_주말', '')}, 공휴일: {original_row.get('운영시간_공휴일', '')}",
                'capacity': self.normalizer._safe_int(original_row.get('시설규모', '')),
                'facility_extra': {
                    '시설유형': original_row.get('시설유형', ''),
                    '운영기관': original_row.get('운영기관', ''),
                    '시설대관여부': original_row.get('시설대관여부', ''),
                    '시설사용료': original_row.get('시설사용료', ''),
                    '주차정보': original_row.get('주차정보', ''),
                    '시설종류': original_row.get('시설종류', ''),
                    '시설운영상태': original_row.get('시설운영상태', ''),
                    '시설편의시설': original_row.get('시설편의시설', ''),
                    '비고': original_row.get('비고', '')
                },
                'data_source': 'localdata'
            }
        elif facility_type == 'mart':
            return {
                'facility_id': self.normalizer._generate_facility_id('mart'),
                'cd': self.normalizer._get_facility_cd('mart'),
                'name': original_row.get('상호명', ''),
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': original_row.get('전화번호', ''),
                'website': original_row.get('홈페이지', ''),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    '업종': original_row.get('업종', ''),
                    '자치구': original_row.get('자치구', '')
                },
                'data_source': 'localdata'
            }
        elif facility_type == 'convenience':
            return {
                'facility_id': self.normalizer._generate_facility_id('convenience'),
                'cd': self.normalizer._get_facility_cd('convenience'),
                'name': original_row.get('사업장명', ''),
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'] or self.normalizer._safe_float(original_row.get('좌표정보Y(EPSG5174)')),
                'lon': address_info['lon'] or self.normalizer._safe_float(original_row.get('좌표정보X(EPSG5174)')),
                'phone': original_row.get('소재지전화', ''),
                'website': original_row.get('홈페이지', ''),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {
                    '소재지면적': original_row.get('소재지면적', ''),
                    '도로명전체주소': original_row.get('도로명전체주소', '')
                },
                'data_source': 'localdata'
            }
        elif facility_type == 'hospital':
            return {
                'facility_id': self.normalizer._generate_facility_id('hospital'),
                'cd': self.normalizer._get_facility_cd('hospital'),
                'name': original_row.get('기관명', ''),
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': original_row.get('전화번호', ''),
                'website': original_row.get('홈페이지', ''),
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': '응급' in str(original_row.get('진료과목', '')),
                'facility_extra': {
                    '진료과목': original_row.get('진료과목', ''),
                    '자치구': original_row.get('자치구', ''),
                    '의료기관종별': original_row.get('의료기관종별', '')
                },
                'data_source': 'localdata'
            }
        else:
            # 기본 구조
            return {
                'facility_id': self.normalizer._generate_facility_id(facility_type),
                'cd': self.normalizer._get_facility_cd(facility_type),
                'name': original_row.get('name', ''),
                'address_raw': address_info['address_raw'],
                'address_nm': address_info['address_nm'],
                'address_id': address_info['address_id'],
                'lat': address_info['lat'],
                'lon': address_info['lon'],
                'phone': None,
                'website': None,
                'operating_hours': None,
                'is_24h': False,
                'is_emergency': False,
                'capacity': None,
                'grade_level': None,
                'facility_extra': {},
                'data_source': 'openseoul'
            }
    
    def save_retry_results(self, output_dir: Path, retry_results: Dict[str, List[Dict]]):
        """재처리 결과를 기존 파일에 누적 저장"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 성공한 재처리 데이터를 기존 파일에 추가 (append)
        if retry_results["retry_facilities"]:
            facilities_file = output_dir / "public_facilities.jsonl"
            
            # facility_id를 기존 데이터 기준으로 부여하고 추가
            success_names = []
            with open(facilities_file, 'a', encoding='utf-8') as f:  # 'a' = append 모드
                for facility in retry_results["retry_facilities"]:
                    # facility_id 재부여
                    facility['facility_id'] = self._get_next_facility_id(
                        facility.get('cd', 'fac'), 
                        output_dir
                    )
                    success_names.append(facility['name'])
                    
                    # 파일에 추가
                    f.write(json.dumps(facility, ensure_ascii=False) + '\n')
            
            logger.info(f"재처리 성공 데이터 추가: {len(retry_results['retry_facilities'])}개")
            
            # 2. 성공한 시설들을 실패 목록에서 제거
            self._remove_successful_from_failed(output_dir, success_names)
            logger.info(f"실패 목록에서 성공한 {len(success_names)}개 제거")
        
        # 3. 여전히 실패한 데이터는 그대로 유지 (별도 처리 없음)
        if retry_results["retry_failed_addresses"]:
            logger.info(f"여전히 실패한 데이터: {len(retry_results['retry_failed_addresses'])}개 (기존 파일에 유지)")
        
        # 4. 최종 요약을 progress.jsonl에 기록
        total_processed = len(retry_results["retry_facilities"]) + len(retry_results["retry_failed_addresses"])
        success_rate = (len(retry_results["retry_facilities"]) / total_processed * 100) if total_processed > 0 else 0
        
        summary_progress_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'retry_summary',
            'total_processed': total_processed,
            'success_count': len(retry_results["retry_facilities"]),
            'failure_count': len(retry_results["retry_failed_addresses"]),
            'success_rate': success_rate,
            'summary': f"재처리 완료: 전체 {total_processed}개 중 성공 {len(retry_results['retry_facilities'])}개 ({success_rate:.1f}%)"
        }
        
        progress_file = output_dir / "progress.jsonl"
        with open(progress_file, 'a', encoding='utf-8') as pf:
            pf.write(json.dumps(summary_progress_data, ensure_ascii=False) + '\n')
        
        logger.info(f"📊 재처리 요약: 전체 {total_processed}개 중 성공 {len(retry_results['retry_facilities'])}개 ({success_rate:.1f}%)")

# 예시 사용법
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 현재 스크립트 위치에서 상대 경로로 계산
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[3]  # backend/services/data_collection/normalized/infra -> backend
    data_path = project_root / "data" / "public-api" / "openseoul"
    output_dir = project_root / "data" / "normalized" / "infra"  # 기존 파일 위치
    
    # 재처리 실행
    retry_normalizer = InfraNormalizerRetry(data_path)
    failed_jsonl_path = output_dir / "failed_addresses.jsonl"  # 기존 실패 파일
    
    retry_results = retry_normalizer.retry_failed_addresses_from_jsonl(failed_jsonl_path, output_dir)
    retry_normalizer.save_retry_results(output_dir, retry_results)  # 기존 파일들 수정


