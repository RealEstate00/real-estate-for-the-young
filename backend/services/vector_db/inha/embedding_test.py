#!/usr/bin/env python3
"""
임베딩 모델 테스트 스크립트
여러 임베딩 모델과 차원수를 테스트하여 최적의 조합을 찾습니다.
"""

import json
import logging
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_community.embeddings import HuggingFaceEmbeddings
# SQLAlchemy 호환성 문제로 인해 필요시에만 import
try:
    # 데이터베이스 연결 및 SQL 실행에 사용되는 SQLAlchemy의 주요 함수 import
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except Exception as e:
    print(f"SQLAlchemy import 문제: {e}")
    SQLALCHEMY_AVAILABLE = False

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('embedding_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 테스트 쿼리와 예상 키워드
TEST_QUERIES = [
    {
        "query": "신혼부부 임차보증금 이자지원 신청 방법",
        "expected_keywords": ["신혼부부", "임차보증금", "이자지원", "신청", "방법", "절차", "서류"]
    },
    {
        "query": "청년 전세대출 조건과 금리",
        "expected_keywords": ["청년", "전세대출", "조건", "금리", "소득", "한도", "자격"]
    },
    {
        "query": "서울시 월세 지원 자격 요건",
        "expected_keywords": ["서울시", "월세", "지원", "자격", "요건", "대상", "조건"]
    },
    {
        "query": "버팀목 전세자금 대출 한도",
        "expected_keywords": ["버팀목", "전세자금", "대출", "한도", "금액", "소득기준"]
    },
    {
        "query": "주거급여 수급자 임차급여 신청",
        "expected_keywords": ["주거급여", "수급자", "임차급여", "신청", "자격", "조건"]
    },
    {
        "query": "서울형 주택바우처 지원 대상",
        "expected_keywords": ["서울형", "주택바우처", "지원", "대상", "자격", "신청"]
    },
    {
        "query": "전세보증금 반환보증 보증료 지원",
        "expected_keywords": ["전세보증금", "반환보증", "보증료", "지원", "신청", "대상"]
    },
    {
        "query": "긴급 복지 주거 지원 신청 절차",
        "expected_keywords": ["긴급", "복지", "주거", "지원", "신청", "절차", "조건"]
    },
    {
        "query": "청년 임차보증금 이자 지원 FAQ",
        "expected_keywords": ["청년", "임차보증금", "이자", "지원", "자격", "신청", "조건"]
    },
    {
        "query": "신혼부부 대출 연장 조건",
        "expected_keywords": ["신혼부부", "대출", "연장", "조건", "기간", "신청", "방법"]
    }
]

# 테스트할 임베딩 모델 설정 (차원별 구성: 384, 768, 1024)
MODEL_CONFIGS = [
    # 384차원 모델들 (빠른 속도, 적은 메모리)
    {"model": "intfloat/multilingual-e5-small", "dim": 384},
    {"model": "sentence-transformers/all-MiniLM-L6-v2", "dim": 384},
    {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "dim": 384},
    
    # 768차원 모델들 (균형잡힌 성능)
    {"model": "jhgan/ko-sbert-nli", "dim": 768},  # 한국어 특화
    {"model": "intfloat/multilingual-e5-base", "dim": 768},  # 검증된 성능
    {"model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", "dim": 768},
    {"model": "kakaobank/kf-deberta-base", "dim": 768},  # 한국 금융 특화
    
    # 1024차원 모델들 (최고 성능, 많은 메모리)
    {"model": "jinaai/jina-embeddings-v4", "dim": 1024},  # 최신 검색 최적화
    {"model": "intfloat/multilingual-e5-large", "dim": 1024},  # 대용량 고성능
    {"model": "BAAI/bge-large-en-v1.5", "dim": 1024},  # 검증된 대용량 모델
]

class EmbeddingTester:
    def __init__(self, db_url: str = "postgresql://postgres:post1234@localhost:5432/rey"):
        """임베딩 테스터 초기화"""
        self.db_url = db_url
        
        # psycopg2로 직접 연결 정보 파싱
        import psycopg2
        self.conn_params = {
            'host': 'localhost',
            'port': '5432', 
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }
        
        # 결과 저장용
        self.results = []
        
    def load_json_data(self, json_path: str) -> List[Dict]:
        """JSON 데이터 로드"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"로드된 문서 수: {len(data)}")
        return data
    
    def get_embedding_dimension(self, model_name: str) -> int:
        """모델의 임베딩 차원 확인 (LangChain 사용)"""
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
            # 테스트 문장으로 차원 확인
            test_embedding = embeddings.embed_query("테스트")
            return len(test_embedding)
        except Exception as e:
            logger.error(f"모델 {model_name} 차원 확인 실패: {e}")
            return 768  # 기본값
    
    def create_vector_table(self, dim: int, table_name: str = "test_documents"):
        """테스트용 벡터 테이블 생성"""
        import psycopg2
        
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()
        
        try:
            # 기존 테이블 삭제
            cur.execute(f"DROP TABLE IF EXISTS housing.{table_name} CASCADE")
            
            # 새 테이블 생성
            create_sql = f"""
            CREATE TABLE housing.{table_name} (
                id VARCHAR(255) PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector({dim}),
                metadata JSONB DEFAULT '{{}}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
            cur.execute(create_sql)
            
            # 인덱스 생성
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding 
            ON housing.{table_name} 
            USING hnsw (embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 64)
            """
            cur.execute(index_sql)
            
            conn.commit()
            logger.info(f"테이블 housing.{table_name} 생성 완료 (차원: {dim})")
            
        finally:
            cur.close()
            conn.close()
    
    def insert_documents(self, documents: List[Dict], model_name: str, table_name: str = "test_documents"):
        """문서들을 임베딩하여 DB에 삽입 (LangChain 사용)"""
        logger.info(f"모델 {model_name}로 문서 임베딩 시작...")
        
        try:
            import psycopg2
            import psycopg2.extras
            
            # LangChain HuggingFaceEmbeddings 사용
            embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
            
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()
            
            try:
                for i, doc in enumerate(documents):
                    if i % 100 == 0:
                        logger.info(f"진행률: {i}/{len(documents)}")
                    
                    # LangChain으로 임베딩 생성
                    embedding = embeddings.embed_query(doc['content'])
                    
                    # 메타데이터 준비
                    metadata = {
                        'source': doc.get('source', ''),
                        'original_id': doc.get('id', '')
                    }
                    
                    # 삽입 쿼리
                    insert_sql = f"""
                        INSERT INTO housing.{table_name} (id, content, embedding, metadata)
                        VALUES (%s, %s, %s::vector, %s::jsonb)
                    """
                    
                    cur.execute(insert_sql, (
                        doc['id'],
                        doc['content'],
                        embedding,
                        json.dumps(metadata, ensure_ascii=False)
                    ))
                
                conn.commit()
                logger.info(f"문서 삽입 완료: {len(documents)}개")
                
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            logger.error(f"문서 삽입 실패: {e}")
            raise
    
    def search_documents(self, query: str, model_name: str, table_name: str = "test_documents", top_k: int = 10) -> List[Dict]:
        """벡터 검색 수행 (LangChain 사용)"""
        try:
            # LangChain HuggingFaceEmbeddings 사용
            embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
            query_embedding = embeddings.embed_query(query)
            
            # psycopg2 직접 사용으로 변경 (벡터 연산 문제 해결)
            import psycopg2
            
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()
            
            # 벡터 검색 쿼리 (올바른 형식으로)
            search_sql = f"""
                SELECT id, content, metadata, 
                       1 - (embedding <=> %s::vector) as similarity
                FROM housing.{table_name}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            
            cur.execute(search_sql, (query_embedding, query_embedding, top_k))
            results = cur.fetchall()
            
            search_results = []
            for row in results:
                # 메타데이터 처리 - 이미 dict일 수 있음
                metadata = row[2] if row[2] else {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                search_results.append({
                    'id': row[0],
                    'content': row[1], 
                    'metadata': metadata,
                    'similarity': float(row[3])
                })
            
            cur.close()
            conn.close()
            
            logger.info(f"검색 결과: {len(search_results)}개")
            return search_results
                
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            return []
    
    def evaluate_search_results(self, search_results: List[Dict], expected_keywords: List[str]) -> Tuple[int, float]:
        """검색 결과 평가 (개선된 방식)"""
        if not search_results:
            logger.warning("검색 결과가 없습니다")
            return 0, 0.0
        
        # 상위 3개 결과만 평가 (더 정확한 평가)
        top_results = search_results[:3]
        logger.info(f"평가할 검색 결과: {len(top_results)}개")
        
        # 각 결과의 유사도와 내용 출력
        for i, result in enumerate(top_results):
            logger.info(f"  결과 {i+1}: 유사도 {result['similarity']:.3f} - {result['content'][:100]}...")
        
        # 모든 검색 결과의 내용을 합치기
        all_content = " ".join([result['content'] for result in top_results])
        
        # 예상 키워드가 몇 개나 포함되어 있는지 확인
        matched_keywords = []
        for keyword in expected_keywords:
            if keyword in all_content:
                matched_keywords.append(keyword)
                logger.info(f"  매칭 키워드: '{keyword}'")
        
        matched_count = len(matched_keywords)
        total_count = len(expected_keywords)
        score = (matched_count / total_count) * 100 if total_count > 0 else 0
        
        logger.info(f"키워드 매칭: {matched_count}/{total_count} ({score:.1f}%)")
        
        return matched_count, score
    
    def run_test(self, json_path: str):
        """전체 테스트 실행"""
        logger.info("=== 임베딩 모델 테스트 시작 ===")
        
        # JSON 데이터 로드
        documents = self.load_json_data(json_path)
        
        for model_config in MODEL_CONFIGS:
            model_name = model_config["model"]
            expected_dim = model_config["dim"]
            
            logger.info(f"\n[테스트] 모델: {model_name}, 예상 차원: {expected_dim}")
            
            try:
                # 실제 차원 확인
                actual_dim = self.get_embedding_dimension(model_name)
                logger.info(f"실제 차원: {actual_dim}")
                
                # 테스트용 테이블 생성 (실제 차원 사용)
                table_name = f"test_docs_{actual_dim}_{int(time.time())}"
                self.create_vector_table(actual_dim, table_name)
                
                # 문서 임베딩 및 삽입
                self.insert_documents(documents, model_name, table_name)
                
                # 각 테스트 쿼리에 대해 검색 수행
                query_results = []
                for i, test_case in enumerate(TEST_QUERIES):
                    logger.info(f"쿼리 {i+1}/10: {test_case['query']}")
                    
                    # 검색 수행
                    search_results = self.search_documents(
                        test_case['query'], 
                        model_name, 
                        table_name
                    )
                    
                    # 결과 평가
                    matched_count, score = self.evaluate_search_results(
                        search_results, 
                        test_case['expected_keywords']
                    )
                    
                    query_result = {
                        'model_name': model_name,
                        'dimension': actual_dim,
                        'query_index': i,
                        'query': test_case['query'],
                        'expected_keywords': test_case['expected_keywords'],
                        'matched_count': matched_count,
                        'total_keywords': len(test_case['expected_keywords']),
                        'score': score,
                        'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    query_results.append(query_result)
                    self.results.append(query_result)
                    
                    logger.info(f"  매칭된 키워드: {matched_count}/{len(test_case['expected_keywords'])} ({score:.2f}%)")
                
                # 테스트용 테이블 정리
                import psycopg2
                conn = psycopg2.connect(**self.conn_params)
                cur = conn.cursor()
                try:
                    cur.execute(f"DROP TABLE IF EXISTS housing.{table_name} CASCADE")
                    conn.commit()
                finally:
                    cur.close()
                    conn.close()
                
                logger.info(f"[완료] {model_name} 테스트 완료")
                
            except Exception as e:
                logger.error(f"[에러] {model_name} 테스트 실패: {e}")
                continue
        
        # 결과 저장
        self.save_results()
        logger.info("=== 모든 테스트 완료 ===")
    
    def save_results(self):
        """결과를 CSV 파일로 저장"""
        if not self.results:
            logger.warning("저장할 결과가 없습니다.")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"embedding_test_results_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'model_name', 'dimension', 'query_index', 'query', 
                'expected_keywords', 'matched_count', 'total_keywords', 
                'score', 'test_time'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                # expected_keywords를 문자열로 변환
                result_copy = result.copy()
                result_copy['expected_keywords'] = ','.join(result['expected_keywords'])
                writer.writerow(result_copy)
        
        logger.info(f"결과가 {csv_filename}에 저장되었습니다.")
        
        # 요약 통계 출력
        self.print_summary()
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        df = pd.DataFrame(self.results)
        
        logger.info("\n=== 테스트 결과 요약 ===")
        
        # 모델별 평균 점수
        model_scores = df.groupby(['model_name', 'dimension'])['score'].agg(['mean', 'std', 'count']).round(2)
        logger.info("\n모델별 평균 점수:")
        print(model_scores)
        
        # 최고 성능 모델
        best_model = df.loc[df['score'].idxmax()]
        logger.info(f"\n최고 성능:")
        logger.info(f"  모델: {best_model['model_name']}")
        logger.info(f"  차원: {best_model['dimension']}")
        logger.info(f"  쿼리: {best_model['query']}")
        logger.info(f"  점수: {best_model['score']:.2f}%")

def main():
    """메인 함수"""
    json_path = "backend/data/normalized/finance_support/서울시_주거복지사업_pgvector_ready_clecd ..aned.json"
    
    if not Path(json_path).exists():
        logger.error(f"JSON 파일을 찾을 수 없습니다: {json_path}")
        return
    
    tester = EmbeddingTester()
    tester.run_test(json_path)

if __name__ == "__main__":
    main()
