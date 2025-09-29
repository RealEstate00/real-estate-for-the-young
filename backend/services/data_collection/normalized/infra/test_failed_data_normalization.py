#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
실패 데이터 정규화 테스트 모듈
failed_addresses.jsonl의 데이터를 다시 정규화하여 주소 전처리 함수의 효과를 테스트
"""

import pandas as pd
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

# infra_normalizer_NoJusoAPI.py에서 필요한 함수들 import
from backend.services.data_collection.normalized.infra.infra_normalizer_NoJusoAPI import (
    preprocess_address,
    preprocess_subway_address, 
    preprocess_park_address,
    detect_address_type,
    detect_address_type_enhanced,
    CoordinateAPI
)
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class FailedDataTester:
    """실패 데이터 정규화 테스트 클래스"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
        # API 클라이언트 초기화
        coordinate_api_key = os.getenv("TOLOLA_API_KEY")
        if not coordinate_api_key:
            raise ValueError("TOLOLA_API_KEY 환경변수가 설정되지 않았습니다.")
        self.coordinate_api = CoordinateAPI(coordinate_api_key)
        
        # 결과 저장용 리스트
        self.success_data: List[Dict] = []
        self.failed_data: List[Dict] = []
    
    def test_failed_addresses(self, failed_jsonl_path: Path, output_dir: Path) -> Dict[str, List[Dict]]:
        """실패한 주소들을 다시 정규화하여 테스트"""
        
        if not failed_jsonl_path.exists():
            logger.error(f"실패 데이터 파일이 존재하지 않습니다: {failed_jsonl_path}")
            return {"success": [], "failed": []}
        
        logger.info(f"실패 데이터 재정규화 테스트 시작: {failed_jsonl_path}")
        
        success_count = 0
        failed_count = 0
        
        # JSONL 파일을 한 줄씩 읽기
        with open(failed_jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    failed_data = json.loads(line.strip())
                    
                    facility_name = failed_data.get('facility_name', '')
                    facility_type = failed_data.get('facility_type', '')
                    address_raw = failed_data.get('address_raw', '')
                    address_processed = failed_data.get('address_processed', '')
                    
                    logger.info(f"테스트 [{line_num}]: {facility_name} - {address_raw}")
                    
                    # 주소 전처리 함수 적용 (시설 타입별)
                    if facility_type == 'subway':
                        addr_processed = preprocess_subway_address(address_raw)
                        logger.info(f"🚇 지하철 전용 전처리 적용")
                    elif '공원' in facility_name:
                        addr_processed = preprocess_park_address(address_raw)
                        logger.info(f"🌳 공원 전용 전처리 적용")
                    else:
                        addr_processed = preprocess_address(address_raw)
                        logger.info(f"🔧 일반 전처리 적용")
                    
                    logger.info(f"✨ 전처리된 주소: {addr_processed}")
                    logger.info(f"📊 기존 전처리: {address_processed}")
                    
                    # 주소 타입 감지
                    address_type = detect_address_type(addr_processed)
                    logger.info(f"🏷️ 감지된 주소 타입: {address_type}")
                    
                    # 좌표 API로 정규화 시도
                    type_param = "ROAD" if address_type == "road" else "PARCEL"
                    result = self.coordinate_api.normalize_address(addr_processed, type_param)
                    
                    # 결과 처리
                    test_result = {
                        "original_failed_data": failed_data,
                        "new_preprocessing": addr_processed,
                        "old_preprocessing": address_processed,
                        "address_type": address_type,
                        "normalization_result": result,
                        "test_timestamp": datetime.now().isoformat()
                    }
                    
                    # 좌표 API 성공 여부만 체크 (주소 API는 체크하지 않음)
                    if result.get('lat') is not None and result.get('lon') is not None:
                        self.success_data.append(test_result)
                        success_count += 1
                        logger.info(f"✅ 좌표 API 성공: {facility_name} (lat: {result['lat']}, lon: {result['lon']})")
                    else:
                        self.failed_data.append(test_result)
                        failed_count += 1
                        logger.warning(f"❌ 좌표 API 실패: {facility_name}")
                        
                except Exception as e:
                    logger.error(f"테스트 중 오류 (라인 {line_num}): {e}")
                    continue
        
        logger.info(f"테스트 완료: 성공 {success_count}개, 실패 {failed_count}개")
        
        return {
            "success": self.success_data,
            "failed": self.failed_data
        }
    
    def save_test_results(self, output_dir: Path, test_results: Dict[str, List[Dict]]):
        """테스트 결과를 JSONL 파일로 저장"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 성공한 데이터 저장
        success_file = output_dir / "성공한_test.jsonl"
        with open(success_file, 'w', encoding='utf-8') as f:
            for result in test_results["success"]:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        # 실패한 데이터 저장
        failed_file = output_dir / "실패한_test.jsonl"
        with open(failed_file, 'w', encoding='utf-8') as f:
            for result in test_results["failed"]:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        logger.info(f"테스트 결과 저장 완료:")
        logger.info(f"  - 성공한_test.jsonl: {len(test_results['success'])}개")
        logger.info(f"  - 실패한_test.jsonl: {len(test_results['failed'])}개")
    
    def analyze_preprocessing_improvements(self, test_results: Dict[str, List[Dict]]):
        """전처리 개선 효과 분석"""
        logger.info("=== 전처리 개선 효과 분석 ===")
        
        success_results = test_results["success"]
        failed_results = test_results["failed"]
        
        # 성공한 케이스 분석
        if success_results:
            logger.info(f"✅ 성공한 케이스 {len(success_results)}개 분석:")
            for i, result in enumerate(success_results[:5]):  # 처음 5개만 출력
                original = result["original_failed_data"]
                new_prep = result["new_preprocessing"]
                old_prep = result["old_preprocessing"]
                
                logger.info(f"  {i+1}. {original['facility_name']}")
                logger.info(f"     원본: {original['address_raw']}")
                logger.info(f"     기존 전처리: {old_prep}")
                logger.info(f"     새 전처리: {new_prep}")
                logger.info(f"     주소 타입: {result['address_type']}")
                logger.info(f"     정규화 성공: {result['normalization_result']['normalization_success']}")
                logger.info("")
        
        # 실패한 케이스 분석
        if failed_results:
            logger.info(f"❌ 실패한 케이스 {len(failed_results)}개 분석:")
            for i, result in enumerate(failed_results[:3]):  # 처음 3개만 출력
                original = result["original_failed_data"]
                new_prep = result["new_preprocessing"]
                old_prep = result["old_preprocessing"]
                
                logger.info(f"  {i+1}. {original['facility_name']}")
                logger.info(f"     원본: {original['address_raw']}")
                logger.info(f"     기존 전처리: {old_prep}")
                logger.info(f"     새 전처리: {new_prep}")
                logger.info(f"     주소 타입: {result['address_type']}")
                logger.info("")
        
        # 전처리 개선 통계
        improved_count = 0
        for result in success_results + failed_results:
            new_prep = result["new_preprocessing"]
            old_prep = result["old_preprocessing"]
            if new_prep != old_prep:
                improved_count += 1
        
        total_tested = len(success_results) + len(failed_results)
        improvement_rate = (improved_count / total_tested * 100) if total_tested > 0 else 0
        
        logger.info(f"📊 전처리 개선 통계:")
        logger.info(f"   - 전체 테스트: {total_tested}개")
        logger.info(f"   - 전처리 개선: {improved_count}개 ({improvement_rate:.1f}%)")
        logger.info(f"   - 성공률: {len(success_results)}/{total_tested} ({len(success_results)/total_tested*100:.1f}%)")

def main():
    """메인 실행 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 현재 스크립트 위치에서 상대 경로로 계산
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[3]  # backend/services/data_collection/normalized/infra -> backend
    
    # 경로 설정
    data_path = project_root / "data" / "public-api" / "openseoul"
    failed_jsonl_path = project_root / "data" / "normalized" / "infra" / "failed_addresses.jsonl"
    output_dir = project_root / "data" / "normalized" / "infra" / "test_fail"
    
    logger.info(f"프로젝트 루트: {project_root}")
    logger.info(f"데이터 경로: {data_path}")
    logger.info(f"실패 데이터 파일: {failed_jsonl_path}")
    logger.info(f"출력 디렉토리: {output_dir}")
    
    # 테스터 초기화
    tester = FailedDataTester(data_path)
    
    # 실패 데이터 테스트 실행
    test_results = tester.test_failed_addresses(failed_jsonl_path, output_dir)
    
    # 결과 저장
    tester.save_test_results(output_dir, test_results)
    
    # 전처리 개선 효과 분석
    tester.analyze_preprocessing_improvements(test_results)
    
    logger.info("🎉 실패 데이터 정규화 테스트 완료!")

if __name__ == "__main__":
    main()
