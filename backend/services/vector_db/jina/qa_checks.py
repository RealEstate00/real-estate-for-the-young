#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QA 및 품질 검사 모듈
검색 결과의 품질을 검증하고 개선합니다.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class QualityCheck:
    """품질 검사 결과"""
    check_name: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any]

class QualityChecker:
    """품질 검사 클래스"""
    
    def __init__(self):
        # 검사 패턴들
        self.patterns = {
            'korean_text': re.compile(r'[가-힣]'),
            'english_text': re.compile(r'[a-zA-Z]'),
            'numbers': re.compile(r'\d+'),
            'special_chars': re.compile(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-]'),
            'urls': re.compile(r'https?://\S+'),
            'emails': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone_numbers': re.compile(r'\b\d{2,3}-\d{3,4}-\d{4}\b'),
        }
    
    def check_content_quality(self, content: str) -> List[QualityCheck]:
        """콘텐츠 품질 검사"""
        checks = []
        
        if not content or not content.strip():
            checks.append(QualityCheck(
                check_name="empty_content",
                passed=False,
                score=0.0,
                message="콘텐츠가 비어있습니다.",
                details={}
            ))
            return checks
        
        # 1. 텍스트 길이 검사
        content_length = len(content.strip())
        if content_length < 10:
            checks.append(QualityCheck(
                check_name="content_too_short",
                passed=False,
                score=0.0,
                message=f"콘텐츠가 너무 짧습니다: {content_length}자",
                details={"length": content_length}
            ))
        elif content_length < 50:
            checks.append(QualityCheck(
                check_name="content_short",
                passed=True,
                score=0.5,
                message=f"콘텐츠가 다소 짧습니다: {content_length}자",
                details={"length": content_length}
            ))
        else:
            checks.append(QualityCheck(
                check_name="content_length_ok",
                passed=True,
                score=1.0,
                message=f"콘텐츠 길이가 적절합니다: {content_length}자",
                details={"length": content_length}
            ))
        
        # 2. 언어 구성 검사
        korean_chars = len(self.patterns['korean_text'].findall(content))
        english_chars = len(self.patterns['english_text'].findall(content))
        total_chars = len(content)
        
        if total_chars > 0:
            korean_ratio = korean_chars / total_chars
            if korean_ratio > 0.3:  # 한국어가 30% 이상
                checks.append(QualityCheck(
                    check_name="korean_content_ok",
                    passed=True,
                    score=1.0,
                    message=f"한국어 콘텐츠 비율이 적절합니다: {korean_ratio:.1%}",
                    details={"korean_ratio": korean_ratio}
                ))
            else:
                checks.append(QualityCheck(
                    check_name="korean_content_low",
                    passed=False,
                    score=0.3,
                    message=f"한국어 콘텐츠 비율이 낮습니다: {korean_ratio:.1%}",
                    details={"korean_ratio": korean_ratio}
                ))
        
        # 3. 특수 문자 검사
        special_chars = len(self.patterns['special_chars'].findall(content))
        if special_chars > len(content) * 0.1:  # 특수문자가 10% 이상
            checks.append(QualityCheck(
                check_name="too_many_special_chars",
                passed=False,
                score=0.2,
                message=f"특수문자가 너무 많습니다: {special_chars}개",
                details={"special_char_count": special_chars}
            ))
        else:
            checks.append(QualityCheck(
                check_name="special_chars_ok",
                passed=True,
                score=1.0,
                message="특수문자 비율이 적절합니다.",
                details={"special_char_count": special_chars}
            ))
        
        # 4. 반복 문자 검사
        repeated_chars = len(re.findall(r'(.)\1{3,}', content))
        if repeated_chars > 0:
            checks.append(QualityCheck(
                check_name="repeated_chars",
                passed=False,
                score=0.3,
                message=f"반복 문자가 있습니다: {repeated_chars}개",
                details={"repeated_char_count": repeated_chars}
            ))
        else:
            checks.append(QualityCheck(
                check_name="no_repeated_chars",
                passed=True,
                score=1.0,
                message="반복 문자가 없습니다.",
                details={}
            ))
        
        return checks
    
    def check_search_result_quality(self, search_result: Dict[str, Any]) -> List[QualityCheck]:
        """검색 결과 품질 검사"""
        checks = []
        
        # 1. 필수 필드 검사
        required_fields = ['chunk_id', 'content', 'document_title', 'section_title']
        missing_fields = [field for field in required_fields if not search_result.get(field)]
        
        if missing_fields:
            checks.append(QualityCheck(
                check_name="missing_required_fields",
                passed=False,
                score=0.0,
                message=f"필수 필드가 누락되었습니다: {missing_fields}",
                details={"missing_fields": missing_fields}
            ))
        else:
            checks.append(QualityCheck(
                check_name="required_fields_ok",
                passed=True,
                score=1.0,
                message="모든 필수 필드가 있습니다.",
                details={}
            ))
        
        # 2. 콘텐츠 품질 검사
        content = search_result.get('content', '')
        content_checks = self.check_content_quality(content)
        checks.extend(content_checks)
        
        # 3. 유사도 점수 검사
        similarity = search_result.get('similarity', 0)
        if similarity > 0.8:
            checks.append(QualityCheck(
                check_name="high_similarity",
                passed=True,
                score=1.0,
                message=f"높은 유사도: {similarity:.3f}",
                details={"similarity": similarity}
            ))
        elif similarity > 0.5:
            checks.append(QualityCheck(
                check_name="medium_similarity",
                passed=True,
                score=0.7,
                message=f"중간 유사도: {similarity:.3f}",
                details={"similarity": similarity}
            ))
        else:
            checks.append(QualityCheck(
                check_name="low_similarity",
                passed=False,
                score=0.3,
                message=f"낮은 유사도: {similarity:.3f}",
                details={"similarity": similarity}
            ))
        
        return checks
    
    def check_search_results_consistency(self, search_results: List[Dict[str, Any]]) -> List[QualityCheck]:
        """검색 결과 일관성 검사"""
        checks = []
        
        if not search_results:
            checks.append(QualityCheck(
                check_name="no_search_results",
                passed=False,
                score=0.0,
                message="검색 결과가 없습니다.",
                details={}
            ))
            return checks
        
        # 1. 결과 수 검사
        result_count = len(search_results)
        if result_count < 3:
            checks.append(QualityCheck(
                check_name="few_results",
                passed=True,
                score=0.6,
                message=f"검색 결과가 적습니다: {result_count}개",
                details={"result_count": result_count}
            ))
        else:
            checks.append(QualityCheck(
                check_name="sufficient_results",
                passed=True,
                score=1.0,
                message=f"충분한 검색 결과: {result_count}개",
                details={"result_count": result_count}
            ))
        
        # 2. 유사도 점수 분포 검사
        similarities = [result.get('similarity', 0) for result in search_results]
        if similarities:
            avg_similarity = sum(similarities) / len(similarities)
            max_similarity = max(similarities)
            min_similarity = min(similarities)
            
            if max_similarity - min_similarity > 0.5:  # 점수 차이가 크면
                checks.append(QualityCheck(
                    check_name="similarity_variance_high",
                    passed=True,
                    score=0.7,
                    message=f"유사도 점수 분산이 큽니다: {min_similarity:.3f}~{max_similarity:.3f}",
                    details={
                        "avg_similarity": avg_similarity,
                        "min_similarity": min_similarity,
                        "max_similarity": max_similarity
                    }
                ))
            else:
                checks.append(QualityCheck(
                    check_name="similarity_variance_ok",
                    passed=True,
                    score=1.0,
                    message=f"유사도 점수 분산이 적절합니다: {min_similarity:.3f}~{max_similarity:.3f}",
                    details={
                        "avg_similarity": avg_similarity,
                        "min_similarity": min_similarity,
                        "max_similarity": max_similarity
                    }
                ))
        
        # 3. 문서 다양성 검사
        document_ids = set(result.get('document_id') for result in search_results)
        unique_documents = len(document_ids)
        
        if unique_documents == 1:
            checks.append(QualityCheck(
                check_name="single_document",
                passed=True,
                score=0.5,
                message="모든 결과가 같은 문서에서 나왔습니다.",
                details={"unique_documents": unique_documents}
            ))
        elif unique_documents < len(search_results) * 0.5:
            checks.append(QualityCheck(
                check_name="low_document_diversity",
                passed=True,
                score=0.7,
                message=f"문서 다양성이 낮습니다: {unique_documents}개 문서",
                details={"unique_documents": unique_documents}
            ))
        else:
            checks.append(QualityCheck(
                check_name="good_document_diversity",
                passed=True,
                score=1.0,
                message=f"문서 다양성이 좋습니다: {unique_documents}개 문서",
                details={"unique_documents": unique_documents}
            ))
        
        return checks
    
    def calculate_overall_quality_score(self, checks: List[QualityCheck]) -> float:
        """전체 품질 점수 계산"""
        if not checks:
            return 0.0
        
        passed_checks = [check for check in checks if check.passed]
        total_score = sum(check.score for check in checks)
        max_score = len(checks)
        
        if max_score == 0:
            return 0.0
        
        return total_score / max_score
    
    def generate_quality_report(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """품질 보고서 생성"""
        all_checks = []
        
        # 개별 결과 품질 검사
        for i, result in enumerate(search_results):
            result_checks = self.check_search_result_quality(result)
            for check in result_checks:
                check.details['result_index'] = i
            all_checks.extend(result_checks)
        
        # 전체 결과 일관성 검사
        consistency_checks = self.check_search_results_consistency(search_results)
        all_checks.extend(consistency_checks)
        
        # 점수 계산
        overall_score = self.calculate_overall_quality_score(all_checks)
        
        # 통계
        passed_checks = [check for check in all_checks if check.passed]
        failed_checks = [check for check in all_checks if not check.passed]
        
        # 문제점 분석
        issues = []
        for check in failed_checks:
            if check.check_name in ['empty_content', 'content_too_short']:
                issues.append("콘텐츠 품질 문제")
            elif check.check_name in ['low_similarity']:
                issues.append("검색 정확도 문제")
            elif check.check_name in ['missing_required_fields']:
                issues.append("데이터 구조 문제")
        
        return {
            'overall_score': overall_score,
            'total_checks': len(all_checks),
            'passed_checks': len(passed_checks),
            'failed_checks': len(failed_checks),
            'issues': list(set(issues)),
            'checks': [
                {
                    'name': check.check_name,
                    'passed': check.passed,
                    'score': check.score,
                    'message': check.message,
                    'details': check.details
                }
                for check in all_checks
            ],
            'timestamp': datetime.now().isoformat()
        }

def main():
    """메인 함수 - 테스트용"""
    checker = QualityChecker()
    
    # 테스트 데이터
    test_content = "서울시 청년 주택 지원 사업에 대한 안내입니다. 19세부터 39세까지의 청년을 대상으로 월세 지원을 제공합니다."
    
    # 콘텐츠 품질 검사
    print("=== 콘텐츠 품질 검사 ===")
    content_checks = checker.check_content_quality(test_content)
    for check in content_checks:
        status = "✓" if check.passed else "✗"
        print(f"{status} {check.check_name}: {check.message} (점수: {check.score:.1f})")
    
    # 검색 결과 품질 검사
    print("\n=== 검색 결과 품질 검사 ===")
    test_result = {
        'chunk_id': 'test_chunk_1',
        'content': test_content,
        'document_title': '청년 주택 지원 가이드',
        'section_title': '지원 대상',
        'similarity': 0.85
    }
    
    result_checks = checker.check_search_result_quality(test_result)
    for check in result_checks:
        status = "✓" if check.passed else "✗"
        print(f"{status} {check.check_name}: {check.message} (점수: {check.score:.1f})")
    
    # 전체 품질 보고서
    print("\n=== 품질 보고서 ===")
    report = checker.generate_quality_report([test_result])
    print(f"전체 점수: {report['overall_score']:.2f}")
    print(f"통과한 검사: {report['passed_checks']}/{report['total_checks']}")
    print(f"문제점: {', '.join(report['issues']) if report['issues'] else '없음'}")

if __name__ == "__main__":
    main()
