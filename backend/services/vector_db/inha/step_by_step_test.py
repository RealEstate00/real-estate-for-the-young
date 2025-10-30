#!/usr/bin/env python3
"""
단계별 임베딩 테스트 - 체계적인 검증 방식
"""

import json
import logging
import csv
from datetime import datetime
from typing import List, Dict, Any, Tuple
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StepByStepEmbeddingTest:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': '5432', 
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }
    
    def step1_environment_check(self):
        """1단계: 환경 및 의존성 확인"""
        logger.info("🔍 1단계: 환경 및 의존성 확인")
        
        results = {
            'pgvector_extension': False,
            'sentence_transformers': False,
            'test_models': []
        }
        
        try:
            # PgVector 확장 확인
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            if cur.fetchone():
                results['pgvector_extension'] = True
                logger.info("✅ PgVector 확장 확인됨")
            else:
                logger.error("❌ PgVector 확장 없음")
            
            cur.close()
            conn.close()
            
            # sentence-transformers 확인
            try:
                from sentence_transformers import SentenceTransformer
                results['sentence_transformers'] = True
                logger.info("✅ sentence-transformers 사용 가능")
                
                # 사용 가능한 모델들 테스트
                test_models = [
                    "jhgan/ko-sbert-nli",
                    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                ]
                
                for model_name in test_models:
                    try:
                        model = SentenceTransformer(model_name)
                        test_emb = model.encode("테스트")
                        results['test_models'].append({
                            'name': model_name,
                            'dimension': len(test_emb)
                        })
                        logger.info(f"✅ {model_name}: {len(test_emb)}차원")
                        del model  # 메모리 해제
                    except Exception as e:
                        logger.warning(f"⚠️ {model_name} 실패: {e}")
                        
            except ImportError:
                logger.error("❌ sentence-transformers 없음")
                
        except Exception as e:
            logger.error(f"환경 확인 실패: {e}")
        
        return results
    
    def step2_vector_operations_test(self):
        """2단계: 벡터 연산 기본 테스트"""
        logger.info("🔍 2단계: 벡터 연산 기본 테스트")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # 테스트 테이블 생성
            test_table = "test_vector_ops"
            cur.execute(f"""
                DROP TABLE IF EXISTS housing.{test_table} CASCADE;
                CREATE TABLE housing.{test_table} (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    embedding vector(768)
                );
            """)
            
            # 테스트 벡터 삽입 (올바른 형식으로)
            test_vector1 = [0.1, 0.2, 0.3] + [0.0] * 765  # 768차원
            test_vector2 = [0.4, 0.5, 0.6] + [0.0] * 765  # 768차원
            
            cur.execute(f"""
                INSERT INTO housing.{test_table} (content, embedding) VALUES 
                ('document 1', %s),
                ('document 2', %s)
            """, (test_vector1, test_vector2))
            
            conn.commit()
            
            # 벡터 유사도 계산 테스트
            cur.execute(f"""
                SELECT content, 1 - (embedding <=> %s::vector) as similarity
                FROM housing.{test_table}
                ORDER BY embedding <=> %s::vector
                LIMIT 2
            """, (test_vector1, test_vector1))
            
            results = cur.fetchall()
            logger.info(f"벡터 유사도 계산 테스트 완료: {len(results)}개 결과")
            
            for content, sim in results:
                logger.info(f"  {content}: {sim:.3f}")
            
            # 정리
            cur.execute(f"DROP TABLE housing.{test_table}")
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("✅ 2단계 완료: 벡터 연산 정상")
            return True
            
        except Exception as e:
            logger.error(f"❌ 2단계 실패: {e}")
            return False
    
    def step3_real_embedding_test(self, model_name: str):
        """3단계: 실제 임베딩 모델 테스트"""
        logger.info(f"🔍 3단계: 실제 임베딩 테스트 ({model_name})")
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # 모델 로드
            model = SentenceTransformer(model_name)
            logger.info(f"모델 로드 완료: {model_name}")
            
            # 테스트 문서
            test_docs = [
                "신혼부부 임차보증금 이자지원 신청 방법을 안내합니다.",
                "청년 전세대출 조건과 금리 정보를 제공합니다.",
                "서울시 월세 지원 자격 요건을 확인하세요."
            ]
            
            # 임베딩 생성
            embeddings = []
            for doc in test_docs:
                emb = model.encode(doc)
                embeddings.append(emb.tolist())
                logger.info(f"임베딩 차원: {len(emb)}")
            
            # DB에 저장 및 검색 테스트
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            test_table = "test_real_embedding"
            cur.execute(f"""
                DROP TABLE IF EXISTS housing.{test_table} CASCADE;
                CREATE TABLE housing.{test_table} (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    embedding vector({len(embeddings[0])})
                );
            """)
            
            # 문서 삽입
            for i, (doc, emb) in enumerate(zip(test_docs, embeddings)):
                cur.execute(f"""
                    INSERT INTO housing.{test_table} (content, embedding) 
                    VALUES (%s, %s)
                """, (doc, emb))
            
            conn.commit()
            
            # 검색 테스트
            query = "신혼부부 임차보증금"
            query_embedding = model.encode(query).tolist()
            
            cur.execute(f"""
                SELECT content, 1 - (embedding <=> %s::vector) as similarity
                FROM housing.{test_table}
                ORDER BY embedding <=> %s::vector
                LIMIT 3
            """, (query_embedding, query_embedding))
            
            search_results = cur.fetchall()
            
            logger.info(f"검색 쿼리: '{query}'")
            for content, sim in search_results:
                logger.info(f"  {content}: {sim:.3f}")
            
            # 정리
            cur.execute(f"DROP TABLE housing.{test_table}")
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("✅ 3단계 완료: 실제 임베딩 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 3단계 실패: {e}")
            return False
    
    def step4_evaluation_method_test(self):
        """4단계: 평가 방법 테스트"""
        logger.info("🔍 4단계: 평가 방법 테스트")
        
        # 개선된 평가 방법 제안
        evaluation_methods = {
            "keyword_match": {
                "description": "단순 키워드 매칭",
                "pros": "빠르고 직관적",
                "cons": "의미적 유사도 무시"
            },
            "semantic_similarity": {
                "description": "의미적 유사도 기반",
                "pros": "더 정확한 평가",
                "cons": "계산 복잡도 높음"
            },
            "hybrid": {
                "description": "키워드 + 유사도 조합",
                "pros": "균형잡힌 평가",
                "cons": "가중치 조정 필요"
            }
        }
        
        logger.info("평가 방법 비교:")
        for method, info in evaluation_methods.items():
            logger.info(f"  {method}: {info['description']}")
            logger.info(f"    장점: {info['pros']}")
            logger.info(f"    단점: {info['cons']}")
        
        return evaluation_methods
    
    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        logger.info("🚀 단계별 임베딩 테스트 시작\n")
        
        # 1단계: 환경 확인
        env_results = self.step1_environment_check()
        
        # 2단계: 벡터 연산
        vector_ops_ok = self.step2_vector_operations_test()
        
        # 3단계: 실제 임베딩 (사용 가능한 모델로)
        embedding_ok = False
        if env_results['test_models']:
            for model_info in env_results['test_models']:
                if self.step3_real_embedding_test(model_info['name']):
                    embedding_ok = True
                    break
        
        # 4단계: 평가 방법 검토
        self.step4_evaluation_method_test()
        
        # 결과 요약
        logger.info("\n📊 최종 테스트 결과:")
        logger.info(f"  환경 설정: {'✅' if env_results['pgvector_extension'] and env_results['sentence_transformers'] else '❌'}")
        logger.info(f"  벡터 연산: {'✅' if vector_ops_ok else '❌'}")
        logger.info(f"  임베딩 테스트: {'✅' if embedding_ok else '❌'}")
        
        if all([env_results['pgvector_extension'], env_results['sentence_transformers'], vector_ops_ok, embedding_ok]):
            logger.info("\n🎉 모든 테스트 통과! 시스템 준비 완료")
        else:
            logger.warning("\n⚠️ 일부 문제 발견. 위 단계들을 점검하세요.")

def main():
    tester = StepByStepEmbeddingTest()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
