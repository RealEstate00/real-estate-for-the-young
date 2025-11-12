"""
벡터 검색기

다양한 모델로 임베딩된 문서에서 유사한 문서를 검색합니다.
주피터 노트북에서 바로 사용 가능하도록 간단하게 구현했습니다.
"""

import time
import logging
import os
import numpy as np
import psycopg2
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from ..models.config import EmbeddingModelType, get_model_config
from ..models.encoder import EmbeddingEncoder

logger = logging.getLogger(__name__)


def get_db_config_from_env() -> Dict[str, str]:
    """환경변수에서 DB 설정 가져오기"""
    load_dotenv()
    return {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5432'),
        'database': os.getenv('PG_DB', 'rey'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'post1234')
    }


class VectorRetriever:
    """
    벡터 검색을 수행하는 클래스
    
    EmbeddingEncoder를 사용하여 쿼리 임베딩을 생성하고,
    PostgreSQL의 pgvector를 사용하여 유사한 문서를 검색합니다.
    """
    
    def __init__(self, model_type: EmbeddingModelType, db_config: Dict[str, str] = None):
        """
        Args:
            model_type: 사용할 임베딩 모델 타입 (MULTILINGUAL_E5_LARGE 등)
            db_config: DB 연결 설정 (없으면 환경변수에서 가져옴)
        """
        self.model_type = model_type
        self.db_config = db_config or get_db_config_from_env()
        
        # EmbeddingEncoder 초기화 (임베딩 생성용)
        self.encoder = EmbeddingEncoder(model_type=model_type)
        self.config = get_model_config(model_type)
        
        # 모델별 테이블 매핑
        self.table_mapping = {
            EmbeddingModelType.MULTILINGUAL_E5_SMALL: 'embeddings_e5_small',
            EmbeddingModelType.MULTILINGUAL_E5_BASE: 'embeddings_e5_base',
            EmbeddingModelType.MULTILINGUAL_E5_LARGE: 'embeddings_e5_large',
            EmbeddingModelType.KAKAOBANK_DEBERTA: 'embeddings_kakaobank',
        }
        
        self._conn = None
        
        logger.info(f"VectorRetriever initialized: {self.config.display_name}")
    
    def _connect(self):
        """PostgreSQL 연결"""
        if self._conn and not self._conn.closed:
            return self._conn
        
        self._conn = psycopg2.connect(**self.db_config)
        return self._conn
    
    def _get_embedding_table(self) -> str:
        """모델 타입에 따라 테이블명 반환"""
        return self.table_mapping.get(
            self.model_type, 
            'embeddings_e5_large'  # 기본값
        )
    
    def search(self, query: str, top_k: int = 5, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """
        쿼리에 대한 유사 문서를 검색합니다.
        
        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 최대 결과 수
            min_similarity: 최소 유사도 임계값 (0.0 ~ 1.0)
        
        Returns:
            검색 결과 리스트 [{'content': str, 'similarity': float, 'chunk_id': int}]
        """
        try:
            # 1. 쿼리 임베딩 생성
            query_embedding = self.encoder.encode_query(query)
            query_embedding = np.array(query_embedding, dtype=np.float32)
            
            # 2. 벡터를 PostgreSQL 형식 문자열로 변환
            query_vec_str = "[" + ",".join(map(str, query_embedding.tolist())) + "]"
            
            # 3. 테이블명 가져오기
            embedding_table = self._get_embedding_table()
            
            # 4. PostgreSQL 연결
            conn = self._connect()
            cur = conn.cursor()
            
            # 5. SQL 쿼리 실행 (pgvector 유사도 검색)
            sql = f"""
            SELECT 
                dc.id AS chunk_id,
                dc.content,
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM vector_db.{embedding_table} e
            JOIN vector_db.document_chunks dc ON e.chunk_id = dc.id
            WHERE e.embedding IS NOT NULL
              AND (1 - (e.embedding <=> %s::vector)) >= %s
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
            """
            
            cur.execute(sql, (query_vec_str, query_vec_str, min_similarity, query_vec_str, top_k))
            rows = cur.fetchall()
            
            # 6. 결과 포맷팅
            results = []
            for row in rows:
                chunk_id, content, similarity = row
                results.append({
                    'chunk_id': chunk_id,
                    'content': content,
                    'similarity': float(similarity)
                })
            
            logger.info(f"검색 완료: {len(results)}개 결과 (쿼리: '{query[:50]}...')")
            return results
            
        except Exception as e:
            logger.error(f"검색 실패: {e}", exc_info=True)
            return []
    
    def search_multiple_queries(self, queries: List[str], top_k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """여러 쿼리에 대한 검색을 수행합니다."""
        
        results = {}
        
        for query in queries:
            logger.info(f"쿼리 검색 중: {query}")
            
            start_time = time.time()
            search_results = self.search(query, top_k)
            search_time = (time.time() - start_time) * 1000
            
            results[query] = {
                'results': search_results,
                'search_time_ms': search_time,
                'result_count': len(search_results)
            }
            
            logger.info(f"쿼리 '{query}' 완료: {len(search_results)}개 결과, {search_time:.2f}ms")
        
        return results
    
    def close(self):
        """리소스를 정리합니다."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
            logger.info("DB 연결 종료")
