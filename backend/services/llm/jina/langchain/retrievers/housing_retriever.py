"""
Housing Retriever Module
주택 정보 검색 모듈
"""

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class HousingRetriever:
    """
    주택 정보 검색을 위한 리트리버 클래스
    ChromaDB를 사용하여 의미 기반 검색 수행
    """
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "housing_data",
        k: int = 5
    ):
        """
        Initialize Housing Retriever
        
        Args:
            persist_directory: ChromaDB 저장 경로
            collection_name: 컬렉션 이름
            k: 검색할 문서 개수
        """
        if persist_directory is None:
            base_path = Path(__file__).parent.parent.parent.parent.parent
            persist_directory = str(base_path / "data" / "vector_db" / "chroma")
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.k = k
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="jhgan/ko-sbert-nli",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Load ChromaDB
        self._load_vector_db()
    
    def _load_vector_db(self):
        """Load ChromaDB from disk"""
        try:
            self.vector_db = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            logger.info(f"ChromaDB loaded from {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to load ChromaDB: {e}")
            raise
    
    def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        filter_dict: Optional[dict] = None
    ) -> List[Document]:
        """
        Retrieve relevant documents
        
        Args:
            query: 검색 쿼리
            k: 검색할 문서 개수 (None이면 기본값 사용)
            filter_dict: 메타데이터 필터 (예: {"시군구": "강남구"})
            
        Returns:
            관련 문서 리스트
        """
        k = k or self.k
        
        try:
            if filter_dict:
                results = self.vector_db.similarity_search(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                results = self.vector_db.similarity_search(query, k=k)
            
            logger.info(f"Retrieved {len(results)} documents for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []
    
    def retrieve_with_scores(
        self,
        query: str,
        k: Optional[int] = None
    ) -> List[tuple[Document, float]]:
        """
        Retrieve documents with similarity scores
        
        Args:
            query: 검색 쿼리
            k: 검색할 문서 개수
            
        Returns:
            (문서, 유사도 점수) 튜플 리스트
        """
        k = k or self.k
        
        try:
            results = self.vector_db.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Retrieval with scores failed: {e}")
            return []
    
    def as_langchain_retriever(self, **kwargs):
        """
        Convert to LangChain retriever format
        
        Returns:
            LangChain retriever object
        """
        search_kwargs = {"k": self.k}
        search_kwargs.update(kwargs)
        
        return self.vector_db.as_retriever(search_kwargs=search_kwargs)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_default_retriever(k: int = 5) -> HousingRetriever:
    """
    Get default housing retriever instance
    
    Args:
        k: Number of documents to retrieve
        
    Returns:
        HousingRetriever instance
    """
    return HousingRetriever(k=k)