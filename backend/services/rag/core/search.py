"""
벡터 검색기

다양한 모델로 임베딩된 문서에서 유사한 문서를 검색합니다.
"""

import time
import logging
from typing import List, Dict, Any, Optional

from ..config import EmbeddingModelType
from ..retrieval.vector_retriever import VectorRetriever as BaseVectorRetriever

logger = logging.getLogger(__name__)


class VectorRetriever:
    """벡터 검색을 수행하는 클래스"""
    
    def __init__(self, model_type: EmbeddingModelType, db_config: Dict[str, str] = None):
        self.model_type = model_type
        self.db_config = db_config or {
            'host': 'localhost',
            'port': '5432',
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }
        
        self._retriever = None
    
    def search(self, query: str, top_k: int = 5, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """쿼리에 대한 유사 문서를 검색합니다."""
        
        if not self._retriever:
            self._retriever = BaseVectorRetriever(
                model_type=self.model_type,
                db_config=self.db_config
            )
        
        try:
            results = self._retriever.search(
                query=query,
                top_k=top_k,
                min_similarity=min_similarity
            )
            
            logger.info(f"검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
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
        if self._retriever:
            self._retriever.close()
            self._retriever = None
