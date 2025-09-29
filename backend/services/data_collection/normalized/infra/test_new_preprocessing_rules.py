#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
새로운 주소 전처리 규칙 테스트 스크립트
"""

from backend.services.data_collection.normalized.infra.infra_normalizer_NoJusoAPI import preprocess_address

def test_new_preprocessing_rules():
    """새로운 전처리 규칙들을 테스트"""
    
    test_cases = [
        # 5-1. '*로n가' 패턴에서 띄어쓰기 제거
        {
            "input": "서울특별시 중구 을지로 6가 21-31",
            "expected": "서울특별시 중구 을지로6가 21-31",
            "description": "'*로n가' 패턴 띄어쓰기 제거"
        },
        
        # 5-2. 지번-부지번 뒤의 모든 한글 제거
        {
            "input": "서울특별시 성동구 성수동1가 685-20 서울숲 관리사무소",
            "expected": "서울특별시 성동구 성수동1가 685-20",
            "description": "지번-부지번 뒤 한글 제거"
        },
        {
            "input": "서울특별시 강서구 가양동 56-2번지 강서오토플랙스 자동차매매센터 102호",
            "expected": "서울특별시 강서구 가양동 56-2",
            "description": "번지 포함 지번 뒤 한글 제거"
        },
        {
            "input": "서울특별시 성동구 하왕십리동 998번지 왕십리KCC스위첸",
            "expected": "서울특별시 성동구 하왕십리동 998",
            "description": "번지 포함 지번 뒤 한글 제거"
        },
        {
            "input": "서울특별시 서대문구 북아현동 136-21번지 이편한세상신촌 119호",
            "expected": "서울특별시 서대문구 북아현동 136-21",
            "description": "번지 포함 지번 뒤 한글 제거"
        },
        
        # 5-3. 동이름 뒤의 숫자(지번)는 보존하고 그 뒤의 한글만 제거
        {
            "input": "서울특별시 용산구 한강로1가 64 대우 월드마크 용산",
            "expected": "서울특별시 용산구 한강로1가 64",
            "description": "동이름 뒤 지번 보존, 한글 제거"
        },
        {
            "input": "서울특별시 용산구 한강로3가 40-999 용산역",
            "expected": "서울특별시 용산구 한강로3가 40-999",
            "description": "동이름 뒤 지번 보존, 한글 제거"
        },
        
        # 5-4. 마침표와 점 제거
        {
            "input": "서울특별시 강남구 신사동 162-16번지 .17",
            "expected": "서울특별시 강남구 신사동 162-16",
            "description": "마침표와 점 제거"
        },
        
        # 정상적인 지번주소는 그대로 유지
        {
            "input": "서울특별시 용산구 한강로2가 112-3",
            "expected": "서울특별시 용산구 한강로2가 112-3",
            "description": "정상적인 지번주소 유지"
        }
    ]
    
    print("=" * 80)
    print("새로운 주소 전처리 규칙 테스트")
    print("=" * 80)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        input_addr = test_case["input"]
        expected = test_case["expected"]
        description = test_case["description"]
        
        result = preprocess_address(input_addr)
        
        is_success = result == expected
        if is_success:
            success_count += 1
            status = "PASS"
        else:
            status = "FAIL"
        
        print(f"\n{i}. {description}")
        print(f"   입력: {input_addr}")
        print(f"   예상: {expected}")
        print(f"   결과: {result}")
        print(f"   상태: {status}")
        
        if not is_success:
            print(f"   차이점: 예상과 다름")
    
    print("\n" + "=" * 80)
    print(f"테스트 결과: {success_count}/{total_count} 성공")
    print(f"성공률: {success_count/total_count*100:.1f}%")
    print("=" * 80)
    
    return success_count == total_count

if __name__ == "__main__":
    test_new_preprocessing_rules()
