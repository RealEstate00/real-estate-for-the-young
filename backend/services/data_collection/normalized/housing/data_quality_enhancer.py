#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터 품질 개선 모듈
정규화 과정에서 자동으로 실행되는 데이터 품질 개선 작업들

기능:
1. Units 중복 제거 (notice_id, room_number, floor, area_m2)
2. 금액 정규화 (만원 단위 누락 수정, 0→NULL)
3. Building type 코드 매핑 (한글→code_master)
4. Platform 키 통일 (platform_id→code)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# 프로젝트 루트를 Python path에 추가
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.libs.utils.amount_normalizer import AmountNormalizer
from backend.libs.utils.building_type_mapper import BuildingTypeMapper
from backend.libs.utils.platform_mapper import PlatformMapper


# ==========================================================
# 1. 메인 데이터 품질 개선 클래스
# ==========================================================

class DataQualityEnhancer:
    """데이터 품질 개선 클래스"""
    
    def __init__(self):
        """초기화"""
        self.amount_normalizer = AmountNormalizer()
        self.building_type_mapper = BuildingTypeMapper()
        self.platform_mapper = PlatformMapper()
        
        # 태그 타입 매핑 정의
        self.tag_type_mapping = {
            # 기존 매핑
            "테마": "theme",
            "대상": "target", 
            "입주조건": "eligibility",
            "시설": "facility",
            "자격요건": "eligibility",
            "지하철": "transport",
            "버스": "transport",
            "마트": "facility",
            "병원": "facility", 
            "학교": "facility",
            "카페": "facility"
        }
    
    # ==========================================================
    # 2. 공개 메서드 - 메인 데이터 품질 개선 기능
    # ==========================================================
    
    def enhance_units_data(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Units 데이터 품질 개선"""
        print("🔧 Units 데이터 품질 개선 시작...")
        
        # 1) 중복 제거
        units = self._deduplicate_units(units)
        
        # 2) 금액 정규화
        units = self._normalize_amounts(units)
        
        print(f"✅ Units 데이터 품질 개선 완료: {len(units)}개 단위")
        return units
    
    def enhance_notices_data(self, notices: List[Dict[str, Any]], 
                           platforms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Notices 데이터 품질 개선"""
        print("🔧 Notices 데이터 품질 개선 시작...")
        
        # 1) Building type 코드 매핑
        notices = self._map_building_types(notices)
        
        # 2) Platform 키 통일
        notices = self._unify_platform_keys(notices, platforms)
        
        print(f"✅ Notices 데이터 품질 완료: {len(notices)}개 공고")
        return notices
    
    def enhance_platforms_data(self, platforms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Platforms 데이터 품질 개선"""
        print("🔧 Platforms 데이터 품질 개선 시작...")
        
        # Platform 키 통일
        platforms = self._unify_platform_structure(platforms)
        
        print(f"✅ Platforms 데이터 품질 완료: {len(platforms)}개 플랫폼")
        return platforms
    
    def enhance_notice_tags_data(self, notice_tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Notice tags 데이터 품질 개선 (라벨/값 뒤집힘 수정)"""
        print("🔧 Notice tags 데이터 품질 개선 시작...")
        
        enhanced_tags = []
        mapped_count = 0
        misc_count = 0
        
        for tag in notice_tags:
            # 기존 구조 유지하면서 tag_type 매핑 적용
            enhanced_tag = tag.copy()
            
            # tag 필드를 tag_type으로 사용 (cohouse 데이터 구조)
            tag_name = tag.get('tag', '')
            if tag_name in self.tag_type_mapping:
                enhanced_tag['tag_type'] = self.tag_type_mapping[tag_name]
                mapped_count += 1
            elif tag_name and tag_name not in ['theme', 'target', 'eligibility', 'facility', 'transport', 'misc']:
                # 매핑되지 않은 경우 misc로 분류
                enhanced_tag['tag_type'] = 'misc'
                misc_count += 1
            
            enhanced_tags.append(enhanced_tag)
        
        print(f"    ✅ {mapped_count}개 태그 타입 매핑됨")
        print(f"    🗑️ {misc_count}개 misc로 분류됨")
        print(f"✅ Notice tags 데이터 품질 완료: {len(enhanced_tags)}개 태그")
        return enhanced_tags
    
    def validate_data_quality(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """데이터 품질 검증 및 분석"""
        print("🔍 데이터 품질 검증 중...")
        
        validation_results = {
            'units': self._validate_units(data.get('units', [])),
            'notices': self._validate_notices(data.get('notices', [])),
            'platforms': self._validate_platforms(data.get('platforms', [])),
            'addresses': self._validate_addresses(data.get('addresses', []))
        }
        
        # Units 데이터 품질 분석 추가 (units_deduplicator.py 로직)
        units = data.get('units', [])
        if units:
            validation_results['units']['quality_analysis'] = self._analyze_units_quality(units)
        
        # 전체 품질 점수 계산
        total_issues = sum(
            result.get('issues', 0) for result in validation_results.values()
        )
        total_records = sum(
            result.get('total_records', 0) for result in validation_results.values()
        )
        
        quality_score = max(0, 100 - (total_issues / max(total_records, 1)) * 100)
        validation_results['overall'] = {
            'quality_score': quality_score,
            'total_issues': total_issues,
            'total_records': total_records
        }
        
        print(f"✅ 데이터 품질 검증 완료: {quality_score:.1f}점")
        return validation_results
    
    # ==========================================================
    # 3. Units 데이터 품질 개선 - 내부 메서드
    # ==========================================================
    
    def _deduplicate_units(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Units 중복 제거 및 고유 unit_id 생성"""
        print("  📋 Units 중복 제거 중...")
        
        seen_keys = set()
        unique_units = []
        duplicates_removed = 0
        
        for unit in units:
            # 중복 검사 키: (notice_id, room_number, floor, area_m2)
            key = (
                unit.get('notice_id'),
                unit.get('room_number'),
                unit.get('floor'),
                unit.get('area_m2')
            )
            
            if key not in seen_keys:
                seen_keys.add(key)
                
                # 고유 unit_id 생성 (units_deduplicator.py 로직 적용)
                unit_id = self._generate_unique_unit_id(
                    unit.get('notice_id', ''),
                    unit.get('room_number', ''),
                    unit.get('floor', 0),
                    unit.get('area_m2', 0.0)
                )
                unit['unit_id'] = unit_id
                
                unique_units.append(unit)
            else:
                duplicates_removed += 1
        
        if duplicates_removed > 0:
            print(f"    ✅ {duplicates_removed}개 중복 제거됨")
        else:
            print(f"    ✅ 중복 없음")
        
        return unique_units
    
    def _generate_unique_unit_id(self, notice_id: str, room_number: str, floor: int, area_m2: float) -> str:
        """고유한 unit_id 생성 (units_deduplicator.py 로직)"""
        import hashlib
        key = f"{notice_id}_{room_number}_{floor}_{area_m2}"
        hash_part = hashlib.md5(key.encode('utf-8')).hexdigest()[:12]
        return f"space_{hash_part}"
    
    def _normalize_amounts(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """금액 정규화"""
        print("  💰 금액 정규화 중...")
        
        normalized_units = []
        anomalies_fixed = 0
        
        for unit in units:
            # 보증금 정규화
            deposit = unit.get('deposit')
            if deposit is not None:
                original_deposit = deposit
                normalized_deposit = self.amount_normalizer.normalize_amount(deposit, 'deposit')
                if normalized_deposit != deposit:
                    anomalies_fixed += 1
                    # 원본 단위 정보 보관
                    unit['deposit_scale'] = self._get_amount_scale(original_deposit, normalized_deposit)
                unit['deposit'] = normalized_deposit
            
            # 월임대료 정규화
            rent = unit.get('rent')
            if rent is not None:
                original_rent = rent
                normalized_rent = self.amount_normalizer.normalize_amount(rent, 'rent')
                if normalized_rent != rent:
                    anomalies_fixed += 1
                    # 원본 단위 정보 보관
                    unit['rent_scale'] = self._get_amount_scale(original_rent, normalized_rent)
                unit['rent'] = normalized_rent
            
            # 관리비 정규화
            maintenance_fee = unit.get('maintenance_fee')
            if maintenance_fee is not None:
                original_maintenance = maintenance_fee
                normalized_maintenance = self.amount_normalizer.normalize_amount(maintenance_fee, 'maintenance_fee')
                if normalized_maintenance != maintenance_fee:
                    anomalies_fixed += 1
                    # 원본 단위 정보 보관
                    unit['maintenance_fee_scale'] = self._get_amount_scale(original_maintenance, normalized_maintenance)
                unit['maintenance_fee'] = normalized_maintenance
            
            # 0 값을 NULL로 변환
            if unit.get('deposit') == 0:
                unit['deposit'] = None
            if unit.get('rent') == 0:
                unit['rent'] = None
            if unit.get('maintenance_fee') == 0:
                unit['maintenance_fee'] = None
            
            # 1970-01-01 날짜를 NULL로 변환
            if unit.get('occupancy_available_at') == '1970-01-01':
                unit['occupancy_available_at'] = None
            
            normalized_units.append(unit)
        
        if anomalies_fixed > 0:
            print(f"    ✅ {anomalies_fixed}개 금액 이상값 수정됨")
        else:
            print(f"    ✅ 금액 정규화 완료")
        
        return normalized_units
    
    def _get_amount_scale(self, original: Any, normalized: Any) -> str:
        """금액 스케일 정보 추출"""
        if original is None or normalized is None:
            return '원'
        
        try:
            original_val = float(original)
            normalized_val = float(normalized)
            
            if original_val == 0:
                return '원'
            elif normalized_val / original_val >= 10000:
                return '만원'
            elif normalized_val / original_val >= 100000000:
                return '억원'
            else:
                return '원'
        except (ValueError, TypeError):
            return '원'
    
    # ==========================================================
    # 4. Notices 데이터 품질 개선 - 내부 메서드
    # ==========================================================
    
    def _map_building_types(self, notices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Building type 코드 매핑 (면적 정보 포함 시 null 처리)"""
        print("  🏢 Building type 코드 매핑 중...")
        
        mapped_count = 0
        nulled_count = 0
        
        for notice in notices:
            building_type = notice.get('building_type')
            if building_type:
                # 면적 정보가 포함된 경우 null 처리
                if self._is_area_info(building_type):
                    notice['building_type'] = None
                    nulled_count += 1
                    continue
                
                # 정상적인 building type인 경우 매핑 시도
                mapped_code = self.building_type_mapper.get_building_type_code(building_type)
                if mapped_code:
                    notice['building_type'] = mapped_code
                    mapped_count += 1
                else:
                    # 매핑되지 않는 경우 null 처리
                    notice['building_type'] = None
                    nulled_count += 1
        
        print(f"    ✅ {mapped_count}개 building type 매핑됨")
        print(f"    🗑️ {nulled_count}개 면적정보/null 처리됨")
        return notices
    
    def _is_area_info(self, building_type: str) -> bool:
        """면적 정보가 포함된 building_type인지 확인"""
        if not building_type or not isinstance(building_type, str):
            return False
        
        # 면적 관련 키워드들
        area_keywords = [
            'm²', '㎡', 'm2', '평', '전용', '공급', '면적', 
            '/', '~', '이상', '이하', '범위'
        ]
        
        # 숫자와 면적 단위가 함께 있는 경우
        import re
        if re.search(r'\d+\.?\d*\s*(m²|㎡|m2|평)', building_type):
            return True
        
        # 면적 관련 키워드가 포함된 경우
        for keyword in area_keywords:
            if keyword in building_type:
                return True
        
        return False
    
    def _unify_platform_keys(self, notices: List[Dict[str, Any]], 
                            platforms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Platform 키 통일"""
        print("  🔗 Platform 키 통일 중...")
        
        # Platform 코드 매핑 생성
        platform_code_map = {}
        for platform in platforms:
            old_code = platform.get('platform_id', platform.get('code', ''))
            new_code = platform.get('code', old_code)
            platform_code_map[old_code] = new_code
        
        updated_count = 0
        
        for notice in notices:
            old_platform_id = notice.get('platform_id')
            if old_platform_id in platform_code_map:
                new_platform_id = platform_code_map[old_platform_id]
                if new_platform_id != old_platform_id:
                    notice['platform_id'] = new_platform_id
                    updated_count += 1
        
        print(f"    ✅ {updated_count}개 platform_id 업데이트됨")
        return notices
    
    # ==========================================================
    # 5. Platforms 데이터 품질 개선 - 내부 메서드
    # ==========================================================
    
    def _unify_platform_structure(self, platforms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Platform 구조 통일"""
        print("  🔧 Platform 구조 통일 중...")
        
        unified_platforms = []
        
        for platform in platforms:
            # platform_id를 code로 통일
            if 'platform_id' in platform and 'code' not in platform:
                platform['code'] = platform.pop('platform_id')
            
            # 코드마스터 호환 코드 추가
            code = platform.get('code', '')
            platform['platform_code'] = f'platform_{code}'
            
            unified_platforms.append(platform)
        
        print(f"    ✅ {len(unified_platforms)}개 platform 구조 통일됨")
        return unified_platforms
    
    # ==========================================================
    # 6. 데이터 검증 - 내부 메서드
    # ==========================================================
    
    def _validate_units(self, units: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Units 데이터 검증"""
        issues = 0
        total_records = len(units)
        
        # 중복 검사
        seen_keys = set()
        for unit in units:
            key = (
                unit.get('notice_id'),
                unit.get('room_number'),
                unit.get('floor'),
                unit.get('area_m2')
            )
            if key in seen_keys:
                issues += 1
            else:
                seen_keys.add(key)
        
        # 금액 범위 검사
        for unit in units:
            deposit = unit.get('deposit')
            if deposit is not None and (deposit < 0 or deposit > 5000000000):
                issues += 1
            
            rent = unit.get('rent')
            if rent is not None and (rent < 0 or rent > 100000000):
                issues += 1
        
        return {
            'total_records': total_records,
            'issues': issues,
            'duplicates': len(units) - len(seen_keys)
        }
    
    def _analyze_units_quality(self, units: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Units 데이터 품질 분석 (units_deduplicator.py 로직)"""
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
    
    def _validate_notices(self, notices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Notices 데이터 검증"""
        issues = 0
        total_records = len(notices)
        
        # Building type 매핑 검사
        unmapped_building_types = 0
        for notice in notices:
            building_type = notice.get('building_type')
            if building_type and not self.building_type_mapper.get_building_type_code(building_type):
                unmapped_building_types += 1
                issues += 1
        
        return {
            'total_records': total_records,
            'issues': issues,
            'unmapped_building_types': unmapped_building_types
        }
    
    def _validate_platforms(self, platforms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Platforms 데이터 검증"""
        issues = 0
        total_records = len(platforms)
        
        # 코드 통일 검사
        for platform in platforms:
            if 'platform_id' in platform and 'code' not in platform:
                issues += 1
        
        return {
            'total_records': total_records,
            'issues': issues
        }
    
    def _validate_addresses(self, addresses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Addresses 데이터 검증"""
        issues = 0
        total_records = len(addresses)
        
        # 위도/경도 범위 검사
        for address in addresses:
            lat = address.get('latitude')
            if lat is not None and (lat < -90 or lat > 90):
                issues += 1
            
            lng = address.get('longitude')
            if lng is not None and (lng < -180 or lng > 180):
                issues += 1
        
        return {
            'total_records': total_records,
            'issues': issues
        }


# ==========================================================
# 7. 유틸리티 함수
# ==========================================================

def print_quality_report(validation_results: dict) -> None:
    """데이터 품질 보고서 출력"""
    print(f"\n📊 데이터 품질 보고서")
    print(f"=" * 50)
    
    overall = validation_results.get('overall', {})
    quality_score = overall.get('quality_score', 0)
    total_issues = overall.get('total_issues', 0)
    total_records = overall.get('total_records', 0)
    
    print(f"🎯 전체 품질 점수: {quality_score:.1f}/100")
    print(f"📈 총 레코드: {total_records:,}개")
    print(f"⚠️  총 이슈: {total_issues:,}개")
    
    # 각 테이블별 상세 정보
    for table_name, result in validation_results.items():
        if table_name == 'overall':
            continue
        
        issues = result.get('issues', 0)
        records = result.get('total_records', 0)
        status = "✅" if issues == 0 else "⚠️"
        
        print(f"  {status} {table_name}: {records:,}개 레코드, {issues:,}개 이슈")
        
        # 특별한 이슈들 표시
        if table_name == 'units' and result.get('duplicates', 0) > 0:
            print(f"    - 중복 제거: {result['duplicates']}개")
        if table_name == 'notices' and result.get('unmapped_building_types', 0) > 0:
            print(f"    - 매핑되지 않은 building type: {result['unmapped_building_types']}개")
        
        # Units 품질 분석 정보 표시
        if table_name == 'units' and 'quality_analysis' in result:
            analysis = result['quality_analysis']
            print(f"    - 보증금: {analysis['deposit_stats']['null_ratio']:.1f}% NULL")
            print(f"    - 월임대료: {analysis['rent_stats']['null_ratio']:.1f}% NULL")
            print(f"    - 관리비: {analysis['maintenance_fee_stats']['null_ratio']:.1f}% NULL")
    
    print(f"=" * 50)


# ==========================================================
# 8. 모듈 테스트
# ==========================================================

if __name__ == "__main__":
    """모듈 테스트"""
    print("데이터 품질 개선 모듈 테스트")
    
    # 테스트 데이터
    test_units = [
        {
            'notice_id': 'test_1',
            'room_number': '101',
            'floor': 1,
            'area_m2': 30.5,
            'deposit': 5000,  # 의심스러운 낮은 값
            'rent': 50,       # 의심스러운 낮은 값
            'maintenance_fee': 0
        },
        {
            'notice_id': 'test_1',  # 중복
            'room_number': '101',
            'floor': 1,
            'area_m2': 30.5,
            'deposit': 50000000,
            'rent': 500000,
            'maintenance_fee': 50000
        }
    ]
    
    test_notices = [
        {
            'id': 'test_1',
            'building_type': '다세대주택',
            'platform_id': 'co'
        }
    ]
    
    test_platforms = [
        {
            'platform_id': 'co',
            'name': '공동체주택',
            'url': 'https://example.com'
        }
    ]
    
    # 테스트 실행
    enhancer = DataQualityEnhancer()
    
    print("\n1. Units 데이터 품질 개선 테스트")
    enhanced_units = enhancer.enhance_units_data(test_units)
    print(f"   결과: {len(enhanced_units)}개 단위")
    
    print("\n2. Platforms 데이터 품질 개선 테스트")
    enhanced_platforms = enhancer.enhance_platforms_data(test_platforms)
    print(f"   결과: {len(enhanced_platforms)}개 플랫폼")
    
    print("\n3. Notices 데이터 품질 개선 테스트")
    enhanced_notices = enhancer.enhance_notices_data(test_notices, enhanced_platforms)
    print(f"   결과: {len(enhanced_notices)}개 공고")
    
    print("\n4. 데이터 품질 검증 테스트")
    test_data = {
        'units': enhanced_units,
        'notices': enhanced_notices,
        'platforms': enhanced_platforms,
        'addresses': []
    }
    validation_results = enhancer.validate_data_quality(test_data)
    print_quality_report(validation_results)
    
    print("\n✅ 모든 테스트 완료")