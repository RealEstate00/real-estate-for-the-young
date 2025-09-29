#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
주소 전처리 디버깅 스크립트
"""

from backend.services.data_collection.normalized.infra.infra_normalizer_NoJusoAPI import preprocess_address

def debug_preprocessing():
    """주소 전처리 과정을 단계별로 디버깅"""
    
    test_cases = [
        "서울특별시 성동구 성수동1가 685-20 서울숲 관리사무소",
        "서울특별시 용산구 한강로2가 112-3"
    ]
    
    for test_case in test_cases:
        print(f"\n입력: {test_case}")
        result = preprocess_address(test_case)
        print(f"결과: {result}")
        print("-" * 50)

if __name__ == "__main__":
    debug_preprocessing()


