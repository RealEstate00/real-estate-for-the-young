#!/usr/bin/env python3
"""
Units 중복 제거 및 데이터 품질 개선 모듈
- (notice_id, room_number, floor, area_m2) 조합으로 중복 검사
- 금액 컬럼 정규화 (원 단위 통일, 0→NULL)
- 1970-01-01 → NULL 변환
- 고유 unit_id 생성
"""

import json
import hashlib
from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict
from pathlib import Path


class UnitsDeduplicator:
    """Units 중복 제거 및 데이터 품질 개선 클래스"""
    
    @staticmethod
    def normalize_amount(amount: Any) -> Optional[int]:
        """금액 정규화: 0이면 NULL, 그 외는 원 단위로 통일"""
        if amount is None or amount == 0 or amount == "0":
            return None
        try:
            return int(amount)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def normalize_date(date_str: Any) -> Optional[str]:
        """날짜 정규화: 1970-01-01이면 NULL"""
        if not date_str or str(date_str) in ["1970-01-01", "1970-01-01T00:00:00", "nan"]:
            return None
        return str(date_str)

    @staticmethod
    def generate_unique_unit_id(notice_id: str, room_number: str, floor: int, area_m2: float) -> str:
        """고유한 unit_id 생성"""
        # 기존 unit_id 패턴 유지하면서 고유성 보장
        key = f"{notice_id}_{room_number}_{floor}_{area_m2}"
        hash_part = hashlib.md5(key.encode('utf-8')).hexdigest()[:12]
        return f"space_{hash_part}"

    @classmethod
    def deduplicate_units(cls, units: List[Dict[str, Any]], 
                         keep_original_ids: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        중복 제거 및 데이터 정규화
        
        Args:
            units: units 데이터 리스트
            keep_original_ids: True면 기존 unit_id 유지, False면 새로 생성
            
        Returns:
            (정리된 units 리스트, 통계 정보)
        """
        # 중복 검사를 위한 키: (notice_id, room_number, floor, area_m2)
        seen_combinations: Set[Tuple[str, str, int, float]] = set()
        unique_units = []
        duplicate_count = 0
        duplicate_details = []
        
        for unit in units:
            # 필수 필드 추출
            notice_id = unit.get('notice_id', '')
            room_number = unit.get('room_number', '')
            floor = unit.get('floor', 0)
            area_m2 = unit.get('area_m2', 0.0)
            
            # 중복 검사 키
            key = (notice_id, room_number, floor, area_m2)
            
            if key in seen_combinations:
                duplicate_count += 1
                duplicate_details.append({
                    'unit_id': unit.get('unit_id', 'N/A'),
                    'notice_id': notice_id,
                    'room_number': room_number,
                    'floor': floor,
                    'area_m2': area_m2
                })
                continue
                
            seen_combinations.add(key)
            
            # unit_id 생성 (기존 유지 또는 새로 생성)
            if keep_original_ids and unit.get('unit_id'):
                unit_id = unit.get('unit_id')
            else:
                unit_id = cls.generate_unique_unit_id(notice_id, room_number, floor, area_m2)
            
            # 데이터 정규화
            normalized_unit = {
                'unit_id': unit_id,
                'notice_id': notice_id,
                'unit_type': unit.get('unit_type'),
                'deposit': cls.normalize_amount(unit.get('deposit')),
                'rent': cls.normalize_amount(unit.get('rent')),
                'maintenance_fee': cls.normalize_amount(unit.get('maintenance_fee')),
                'area_m2': area_m2 if area_m2 > 0 else None,
                'floor': floor if floor > 0 else None,
                'room_number': room_number if room_number else None,
                'occupancy_available': unit.get('occupancy_available', False),
                'occupancy_available_at': cls.normalize_date(unit.get('occupancy_available_at')),
                'capacity': unit.get('capacity'),
                'created_at': unit.get('created_at'),
                'updated_at': unit.get('updated_at')
            }
            
            # None 값 제거 (선택적)
            normalized_unit = {k: v for k, v in normalized_unit.items() if v is not None}
            
            unique_units.append(normalized_unit)
        
        stats = {
            'original_count': len(units),
            'deduplicated_count': len(unique_units),
            'duplicate_count': duplicate_count,
            'duplicate_details': duplicate_details
        }
        
        return unique_units, stats

    @classmethod
    def analyze_data_quality(cls, units: List[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터 품질 분석"""
        if not units:
            return {}
        
        # 금액 분포
        deposits = [u.get('deposit', 0) for u in units if u.get('deposit')]
        rents = [u.get('rent', 0) for u in units if u.get('rent')]
        maintenance_fees = [u.get('maintenance_fee', 0) for u in units if u.get('maintenance_fee')]
        
        # 면적 분포
        areas = [u.get('area_m2', 0) for u in units if u.get('area_m2')]
        
        # NULL 비율 계산
        total_units = len(units)
        null_deposit = sum(1 for u in units if not u.get('deposit'))
        null_rent = sum(1 for u in units if not u.get('rent'))
        null_maintenance = sum(1 for u in units if not u.get('maintenance_fee'))
        
        return {
            'total_units': total_units,
            'deposit_stats': {
                'min': min(deposits) if deposits else None,
                'max': max(deposits) if deposits else None,
                'avg': sum(deposits) / len(deposits) if deposits else None,
                'null_count': null_deposit,
                'null_ratio': null_deposit / total_units * 100 if total_units > 0 else 0
            },
            'rent_stats': {
                'min': min(rents) if rents else None,
                'max': max(rents) if rents else None,
                'avg': sum(rents) / len(rents) if rents else None,
                'null_count': null_rent,
                'null_ratio': null_rent / total_units * 100 if total_units > 0 else 0
            },
            'maintenance_fee_stats': {
                'min': min(maintenance_fees) if maintenance_fees else None,
                'max': max(maintenance_fees) if maintenance_fees else None,
                'avg': sum(maintenance_fees) / len(maintenance_fees) if maintenance_fees else None,
                'null_count': null_maintenance,
                'null_ratio': null_maintenance / total_units * 100 if total_units > 0 else 0
            },
            'area_stats': {
                'min': min(areas) if areas else None,
                'max': max(areas) if areas else None,
                'avg': sum(areas) / len(areas) if areas else None
            }
        }

    @classmethod
    def process_units_file(cls, input_path: str, output_path: str = None, 
                          keep_original_ids: bool = False) -> Dict[str, Any]:
        """
        Units 파일 처리
        
        Args:
            input_path: 입력 파일 경로
            output_path: 출력 파일 경로 (None이면 입력 파일 덮어쓰기)
            keep_original_ids: 기존 unit_id 유지 여부
            
        Returns:
            처리 결과 통계
        """
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path
        
        # 파일 읽기
        with open(input_path, 'r', encoding='utf-8') as f:
            units = json.load(f)
        
        # 중복 제거
        deduplicated_units, dedup_stats = cls.deduplicate_units(units, keep_original_ids)
        
        # 데이터 품질 분석
        quality_stats = cls.analyze_data_quality(deduplicated_units)
        
        # 결과 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(deduplicated_units, f, ensure_ascii=False, indent=2)
        
        return {
            'deduplication': dedup_stats,
            'quality_analysis': quality_stats,
            'input_file': str(input_path),
            'output_file': str(output_path)
        }

    @classmethod
    def process_multiple_files(cls, file_paths: List[str], 
                              keep_original_ids: bool = False) -> Dict[str, Any]:
        """여러 파일 일괄 처리"""
        results = {}
        
        for file_path in file_paths:
            try:
                result = cls.process_units_file(file_path, keep_original_ids=keep_original_ids)
                results[file_path] = result
                print(f"✅ {file_path}: {result['deduplication']['original_count']} → {result['deduplication']['deduplicated_count']} (중복 {result['deduplication']['duplicate_count']}개 제거)")
            except Exception as e:
                print(f"❌ {file_path}: 오류 발생 - {e}")
                results[file_path] = {'error': str(e)}
        
        return results


def main():
    """CLI 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Units 중복 제거 및 데이터 품질 개선')
    parser.add_argument('input_files', nargs='+', help='처리할 units.json 파일 경로들')
    parser.add_argument('--keep-ids', action='store_true', help='기존 unit_id 유지')
    parser.add_argument('--output', help='출력 파일 경로 (단일 파일인 경우)')
    
    args = parser.parse_args()
    
    if len(args.input_files) == 1 and args.output:
        # 단일 파일 처리
        result = UnitsDeduplicator.process_units_file(
            args.input_files[0], 
            args.output, 
            keep_original_ids=args.keep_ids
        )
        print(f"\n=== 처리 완료 ===")
        print(f"입력: {result['input_file']}")
        print(f"출력: {result['output_file']}")
        print(f"중복 제거: {result['deduplication']['original_count']} → {result['deduplication']['deduplicated_count']}")
    else:
        # 다중 파일 처리
        results = UnitsDeduplicator.process_multiple_files(
            args.input_files, 
            keep_original_ids=args.keep_ids
        )
        
        print(f"\n=== 전체 처리 완료 ===")
        total_original = sum(r.get('deduplication', {}).get('original_count', 0) for r in results.values() if 'deduplication' in r)
        total_deduplicated = sum(r.get('deduplication', {}).get('deduplicated_count', 0) for r in results.values() if 'deduplication' in r)
        total_duplicates = sum(r.get('deduplication', {}).get('duplicate_count', 0) for r in results.values() if 'deduplication' in r)
        
        print(f"총 처리: {total_original} → {total_deduplicated} (중복 {total_duplicates}개 제거)")


if __name__ == "__main__":
    main()
