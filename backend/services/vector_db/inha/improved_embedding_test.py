#!/usr/bin/env python3
"""
개선된 임베딩 테스트 스크립트
더 정확한 평가 방식과 단계별 검증
"""

import json
import logging
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImprovedEmbeddingTester:
    def __init__(self, db_url: str = "postgresql://postgres:post1234@localhost:5432/rey"):
        """개선된 임베딩 테스터 초기화"""
        self.db_connection = {
            'host': 'localhost',
            'port': '5432',
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }
        
    def test_basic_embedding_operations(self):
        """1단계: 기본 임베딩 작업 테스트"""
        logger.info("=== 1단계: 기본 임베딩 작업 테스트 ===")
        
        try:
            # 간단한 테스트 문서
            test_docs = [
                {"id": "test_1", "content": "신혼부부 임차보증금 이자지원 신청 방법에 대해 설명합니다."},
                {"id": "test_2", "content": "청년 전세대출 조건과 금리 정보를 제공합니다."},
                {"id": "test_3", "content": "서울시 월세 지원 자격 요건을 확인하세요."}
            ]
            
            # sentence-transformers 테스트 (실제 모델 없이 구조만 확인)
            logger.info("임베딩 모델 로드 테스트...")
            
            # PgVector 테이블 생성 테스트
            conn = psycopg2.connect(**self.db_connection)
            cur = conn.cursor()
            
            # 테스트용 임시 테이블
            test_table = "test_embedding_operations"
            cur.execute(f"""
                DROP TABLE IF EXISTS housing.{test_table} CASCADE;
                CREATE TABLE housing.{test_table} (
                    id VARCHAR(255) PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(768)
                );
            """)
            conn.commit()
            logger.info(f"테스트 테이블 housing.{test_table} 생성 완료")
            
            # 더미 임베딩 데이터 삽입 테스트
            dummy_embedding = [0.1] * 768  # 768차원 더미 벡터
            
            for doc in test_docs:
                cur.execute(f"""
                    INSERT INTO housing.{test_table} (id, content, embedding)
                    VALUES (%s, %s, %s)
                """, (doc['id'], doc['content'], dummy_embedding))
            
            conn.commit()
            logger.info(f"{len(test_docs)}개 테스트 문서 삽입 완료")
            
            # 벡터 검색 테스트 (코사인 유사도)
            cur.execute(f"""
                SELECT id, content, 
                       1 - (embedding <=> %s) as similarity
                FROM housing.{test_table}
                ORDER BY embedding <=> %s
                LIMIT 3
            """, (dummy_embedding, dummy_embedding))
            
            results = cur.fetchall()
            logger.info(f"벡터 검색 테스트 성공: {len(results)}개 결과")
            for result in results:
                logger.info(f"  - {result[0]}: {result[2]:.3f}")
            
            # 정리
            cur.execute(f"DROP TABLE IF EXISTS housing.{test_table} CASCADE")
            conn.commit()
            
            cur.close()
            conn.close()
            
            logger.info("✅ 1단계 테스트 완료: 기본 임베딩 작업 정상")
            return True
            
        except Exception as e:
            logger.error(f"❌ 1단계 테스트 실패: {e}")
            return False
    
    def test_embedding_model_loading(self):
        """2단계: 임베딩 모델 로딩 테스트"""
        logger.info("=== 2단계: 임베딩 모델 로딩 테스트 ===")
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # 테스트할 모델들
            test_models = [
                "jhgan/ko-sroberta-multitask",
                "jhgan/ko-sbert-nli"
            ]
            
            results = {}
            
            for model_name in test_models:
                try:
                    logger.info(f"모델 로딩 중: {model_name}")
                    model = SentenceTransformer(model_name)
                    
                    # 테스트 문장으로 임베딩 생성
                    test_text = "신혼부부 임차보증금 이자지원"
                    embedding = model.encode(test_text)
                    
                    results[model_name] = {
                        'dimension': len(embedding),
                        'embedding_sample': embedding[:5].tolist(),  # 처음 5개 값만
                        'status': 'success'
                    }
                    
                    logger.info(f"✅ {model_name}: {len(embedding)}차원")
                    
                except Exception as e:
                    results[model_name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    logger.error(f"❌ {model_name} 실패: {e}")
            
            # 결과 요약
            successful_models = [name for name, result in results.items() if result['status'] == 'success']
            logger.info(f"성공한 모델: {successful_models}")
            
            return len(successful_models) > 0
            
        except ImportError:
            logger.error("sentence-transformers가 설치되지 않았습니다")
            return False
        except Exception as e:
            logger.error(f"모델 로딩 테스트 실패: {e}")
            return False
    
    def test_vector_search_accuracy(self):
        """3단계: 벡터 검색 정확도 테스트"""
        logger.info("=== 3단계: 벡터 검색 정확도 테스트 ===")
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # 간단한 테스트 데이터
            test_documents = [
                {"id": "doc_1", "content": "신혼부부 임차보증금 이자지원 신청 방법과 절차를 안내합니다."},
                {"id": "doc_2", "content": "청년 전세대출 조건, 금리, 소득 기준 등의 정보를 제공합니다."},
                {"id": "doc_3", "content": "서울시 월세 지원 자격 요건과 대상에 대해 설명합니다."},
                {"id": "doc_4", "content": "버팀목 전세자금 대출 한도와 금액 정보입니다."},
                {"id": "doc_5", "content": "주거급여 수급자 임차급여 신청 조건을 확인하세요."}
            ]
            
            # 테스트 쿼리와 예상 결과
            test_cases = [
                {
                    "query": "신혼부부 임차보증금 이자지원 신청",
                    "expected_doc_id": "doc_1",
                    "min_similarity": 0.7
                },
                {
                    "query": "청년 전세대출 조건과 금리",
                    "expected_doc_id": "doc_2", 
                    "min_similarity": 0.7
                }
            ]
            
            # 모델 로드
            model = SentenceTransformer("jhgan/ko-sroberta-multitask")
            
            # DB 연결
            conn = psycopg2.connect(**self.db_connection)
            cur = conn.cursor()
            
            # 테스트 테이블 생성
            test_table = "test_accuracy"
            cur.execute(f"""
                DROP TABLE IF EXISTS housing.{test_table} CASCADE;
                CREATE TABLE housing.{test_table} (
                    id VARCHAR(255) PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(768)
                );
            """)
            
            # 문서 임베딩 및 삽입
            for doc in test_documents:
                embedding = model.encode(doc['content']).tolist()
                cur.execute(f"""
                    INSERT INTO housing.{test_table} (id, content, embedding)
                    VALUES (%s, %s, %s)
                """, (doc['id'], doc['content'], embedding))
            
            conn.commit()
            
            # 검색 테스트
            passed_tests = 0
            total_tests = len(test_cases)
            
            for test_case in test_cases:
                query_embedding = model.encode(test_case['query']).tolist()
                
                cur.execute(f"""
                    SELECT id, content, 
                           1 - (embedding <=> %s) as similarity
                    FROM housing.{test_table}
                    ORDER BY embedding <=> %s
                    LIMIT 1
                """, (query_embedding, query_embedding))
                
                result = cur.fetchone()
                
                if result:
                    doc_id, content, similarity = result
                    
                    logger.info(f"쿼리: '{test_case['query']}'")
                    logger.info(f"  예상 문서: {test_case['expected_doc_id']}")
                    logger.info(f"  실제 결과: {doc_id} (유사도: {similarity:.3f})")
                    
                    # 정확도 검증
                    if (doc_id == test_case['expected_doc_id'] and 
                        similarity >= test_case['min_similarity']):
                        logger.info(f"  ✅ 테스트 통과")
                        passed_tests += 1
                    else:
                        logger.warning(f"  ⚠️ 테스트 실패 (유사도 부족 또는 문서 불일치)")
                else:
                    logger.error(f"  ❌ 검색 결과 없음")
            
            # 정리
            cur.execute(f"DROP TABLE IF EXISTS housing.{test_table} CASCADE")
            conn.commit()
            cur.close()
            conn.close()
            
            accuracy = (passed_tests / total_tests) * 100
            logger.info(f"검색 정확도: {passed_tests}/{total_tests} ({accuracy:.1f}%)")
            
            return accuracy >= 50  # 50% 이상이면 성공으로 간주
            
        except Exception as e:
            logger.error(f"벡터 검색 정확도 테스트 실패: {e}")
            return False
    
    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        logger.info("🚀 개선된 임베딩 테스트 시작")
        
        test_results = {
            'basic_operations': self.test_basic_embedding_operations(),
            'model_loading': self.test_embedding_model_loading(), 
            'search_accuracy': self.test_vector_search_accuracy()
        }
        
        # 결과 요약
        logger.info("\n=== 테스트 결과 요약 ===")
        for test_name, result in test_results.items():
            status = "✅ 통과" if result else "❌ 실패"
            logger.info(f"{test_name}: {status}")
        
        all_passed = all(test_results.values())
        
        if all_passed:
            logger.info("\n🎉 모든 테스트 통과! 임베딩 시스템이 정상 작동합니다.")
        else:
            logger.warning("\n⚠️ 일부 테스트 실패. 시스템 점검이 필요합니다.")
        
        return test_results

def main():
    """메인 함수"""
    tester = ImprovedEmbeddingTester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()

