#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
금액 정규화 유틸리티 모듈
- 이상치 감지 및 수정 (만원 단위 누락)
- 0→NULL 변환
- 1970-01-01→NULL 변환
"""

import re
from typing import Optional, Dict, Any, List

class AmountNormalizer:
    """금액 정규화 클래스"""
    
    # 이상치 임계값 설정
    THRESHOLDS = {
        "deposit": 100000,      # 보증금: 10만원 미만은 이상치
        "rent": 10000,          # 월세: 1만원 미만은 이상치
        "maintenance_fee": 10000  # 관리비: 1만원 미만은 이상치
    }
    
    @classmethod
    def detect_anomaly(cls, amount: int, amount_type: str) -> bool:
        """금액 이상치 감지"""
        if amount is None or amount == 0:
            return False
        
        threshold = cls.THRESHOLDS.get(amount_type, 0)
        return amount < threshold
    
    @classmethod
    def fix_anomaly(cls, amount: int, amount_type: str) -> Optional[int]:
        """금액 이상치 수정 (만원 단위 복원)"""
        if amount is None or amount == 0:
            return None
        
        if cls.detect_anomaly(amount, amount_type):
            # 만원 단위로 복원
            return amount * 10000
        
        return amount
    
    @classmethod
    def normalize_amount(cls, amount: Any, amount_type: str) -> Optional[int]:
        """금액 정규화 (이상치 수정 + 0→NULL)"""
        if amount is None or amount == 0:
            return None
        
        # 정수로 변환
        try:
            amount_int = int(amount)
        except (ValueError, TypeError):
            return None
        
        # 이상치 수정
        fixed_amount = cls.fix_anomaly(amount_int, amount_type)
        
        # 0이면 NULL 반환
        return fixed_amount if fixed_amount != 0 else None
    
    @classmethod
    def normalize_date(cls, date_str: Any) -> Optional[str]:
        """날짜 정규화: 1970-01-01이면 NULL"""
        if not date_str or str(date_str) in ["1970-01-01", "1970-01-01T00:00:00", "nan"]:
            return None
        return str(date_str)
    
    @classmethod
    def normalize_unit(cls, unit: Dict[str, Any]) -> Dict[str, Any]:
        """단일 unit 데이터 정규화"""
        normalized_unit = unit.copy()
        
        # 금액 필드 정규화
        amount_fields = {
            'deposit': 'deposit',
            'rent': 'rent', 
            'maintenance_fee': 'maintenance_fee'
        }
        
        for field, amount_type in amount_fields.items():
            if field in normalized_unit:
                normalized_unit[field] = cls.normalize_amount(
                    normalized_unit[field], amount_type
                )
        
        # 날짜 필드 정규화
        date_fields = ['occupancy_available_at', 'posted_at', 'last_modified', 
                      'apply_start_at', 'apply_end_at', 'created_at', 'updated_at']
        
        for field in date_fields:
            if field in normalized_unit:
                normalized_unit[field] = cls.normalize_date(normalized_unit[field])
        
        return normalized_unit
    
    @classmethod
    def normalize_units(cls, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """units 리스트 정규화"""
        return [cls.normalize_unit(unit) for unit in units]
    
    @classmethod
    def analyze_quality(cls, units: List[Dict[str, Any]], platform: str = "") -> Dict[str, Any]:
        """데이터 품질 분석"""
        analysis = {
            "total_units": len(units),
            "platform": platform,
            "amounts": {},
            "null_ratios": {},
            "anomalies": {}
        }
        
        # 금액 분포 분석
        amount_fields = {
            'deposit': 'deposit',
            'rent': 'rent',
            'maintenance_fee': 'maintenance_fee'
        }
        
        for field, amount_type in amount_fields.items():
            amounts = [u.get(field, 0) for u in units if u.get(field)]
            
            analysis["amounts"][field] = {
                "count": len(amounts),
                "min": min(amounts) if amounts else None,
                "max": max(amounts) if amounts else None,
                "avg": sum(amounts) / len(amounts) if amounts else None
            }
            
            # NULL 비율
            null_count = sum(1 for u in units if not u.get(field))
            analysis["null_ratios"][field] = null_count / len(units) * 100
            
            # 이상치 감지
            anomalies = [a for a in amounts if cls.detect_anomaly(a, amount_type)]
            analysis["anomalies"][field] = {
                "count": len(anomalies),
                "values": anomalies[:5]  # 처음 5개만
            }
        
        return analysis
    
    @classmethod
    def print_analysis(cls, analysis: Dict[str, Any]) -> None:
        """분석 결과 출력"""
        platform = analysis.get("platform", "")
        print(f"\n=== {platform} 데이터 품질 분석 ===")
        
        for field, data in analysis["amounts"].items():
            if data["count"] > 0:
                print(f"{field}: {data['count']}개 (범위: {data['min']:,} ~ {data['max']:,}원)")
            else:
                print(f"{field}: 0개")
        
        print("NULL 비율:")
        for field, ratio in analysis["null_ratios"].items():
            print(f"  {field}: {ratio:.1f}%")
        
        print("이상치:")
        for field, anomaly_data in analysis["anomalies"].items():
            if anomaly_data["count"] > 0:
                print(f"  {field}: {anomaly_data['count']}개 {anomaly_data['values']}...")


def normalize_krw_amount(amount_str: str) -> Optional[int]:
    """한국 원화 금액 파싱 (기존 함수와 호환)"""
    if not amount_str or str(amount_str) == 'nan':
        return None
    
    amount_str = str(amount_str).strip()
    
    # 만원 단위 처리
    if '만원' in amount_str:
        numbers = re.findall(r'[\d,]+', amount_str.replace('만원', ''))
        if numbers:
            try:
                return int(numbers[0].replace(',', '')) * 10000
            except:
                pass
    
    # 억원 단위 처리
    elif '억원' in amount_str:
        numbers = re.findall(r'[\d,]+', amount_str.replace('억원', ''))
        if numbers:
            try:
                return int(numbers[0].replace(',', '')) * 100000000
            except:
                pass
    
    # 일반 원 단위 처리
    else:
        numbers = re.findall(r'[\d,]+', amount_str.replace('원', ''))
        if numbers:
            try:
                return int(numbers[0].replace(',', ''))
            except:
                pass
    
    return None


# 편의 함수들
def normalize_amount(amount: Any, amount_type: str) -> Optional[int]:
    """금액 정규화 편의 함수"""
    return AmountNormalizer.normalize_amount(amount, amount_type)

def normalize_date(date_str: Any) -> Optional[str]:
    """날짜 정규화 편의 함수"""
    return AmountNormalizer.normalize_date(date_str)

def normalize_units(units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """units 정규화 편의 함수"""
    return AmountNormalizer.normalize_units(units)

def analyze_quality(units: List[Dict[str, Any]], platform: str = "") -> Dict[str, Any]:
    """품질 분석 편의 함수"""
    return AmountNormalizer.analyze_quality(units, platform)
