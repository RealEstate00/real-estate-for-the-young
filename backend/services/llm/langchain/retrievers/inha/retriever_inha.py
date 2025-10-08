"""
Housing Retriever - 벡터 검색 전용
ChromaDB 기반 주택 검색 기능 제공

"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from typing import List, Any
from pydantic import Field
import logging

from backend.services.vector_db.inha.chromadb import HousingCollection, KoreanEmbedder, VectorConfig

logger = logging.getLogger(__name__)


class GroqHousingRetriever(BaseRetriever):
    """ChromaDB 기반 주택 검색 Retriever (MMR 우선)"""
    
    # Pydantic v2 필드 정의
    k: int = Field(default=5, description="최종 반환할 문서 개수")
    fetch_k: int = Field(default=15, description="MMR 계산을 위해 가져올 초기 문서 개수")
    lambda_mult: float = Field(default=0.9, description="유사도와 다양성 간 균형")
    min_similarity: float = Field(default=0.1, description="최소 유사도 임계값")
    use_mmr: bool = Field(default=True, description="MMR 사용 여부")
    
    # 내부 객체들 (Pydantic 필드가 아님)
    config: Any = Field(default=None, exclude=True)
    embedder: Any = Field(default=None, exclude=True)
    collection: Any = Field(default=None, exclude=True)

    def __init__(self, k: int = 5, fetch_k: int = 15, lambda_mult: float = 0.9, min_similarity: float = 0.1, use_mmr: bool = True, **kwargs):
        """
        Args:
            k: 최종 반환할 문서 개수
            fetch_k: MMR 계산을 위해 가져올 초기 문서 개수 (k보다 크게 설정)
            lambda_mult: 유사도와 다양성 간 균형 (0~1, 1에 가까울수록 유사도 우선)
            min_similarity: 최소 유사도 임계값
            use_mmr: True면 MMR 사용 (다양성), False면 유사도만 사용 (전체 검색)
        """
        super().__init__(k=k, fetch_k=fetch_k, lambda_mult=lambda_mult, min_similarity=min_similarity, use_mmr=use_mmr, **kwargs)
        
        # 내부 객체 초기화
        self.config = VectorConfig()
        self.embedder = KoreanEmbedder(config=self.config)
        self.collection = HousingCollection(self.embedder, self.config)

        logger.info(f"GroqHousingRetriever initialized with k={k}, fetch_k={fetch_k}, lambda_mult={lambda_mult}, min_similarity={min_similarity}, use_mmr={use_mmr}")


    def _get_relevant_documents(self, query: str) -> List[Document]:
        """검색 실행 및 Document 반환 (MMR 또는 유사도)"""
        search_type = "MMR" if self.use_mmr else "Similarity"
        logger.info(f"Searching with {search_type} for: '{query}'")

        try:
            # 임베딩 모델 로드
            if not self.embedder.is_loaded():
                self.embedder.load_model()

            # 쿼리 임베딩 생성
            query_embedding = self.embedder.encode_text(query)

            # ChromaDB 컬렉션 가져오기
            collection = self.collection.get_collection()

            # 검색 실행
            n_results = self.fetch_k if self.use_mmr else self.k
            include_embeddings = ['documents', 'metadatas', 'distances', 'embeddings'] if self.use_mmr else ['documents', 'metadatas', 'distances']

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=include_embeddings
            )

            # 결과 처리
            if results['ids'] and results['ids'][0]:
                if self.use_mmr:
                    # MMR 재정렬
                    processed_results = self._maximal_marginal_relevance(
                        query_embedding=query_embedding,
                        embedding_list=results['embeddings'][0],
                        documents=results['documents'][0],
                        metadatas=results['metadatas'][0],
                        distances=results['distances'][0],
                        k=self.k
                    )
                else:
                    # 유사도만 사용
                    processed_results = self._similarity_only(
                        documents=results['documents'][0],
                        metadatas=results['metadatas'][0],
                        distances=results['distances'][0]
                    )
            else:
                processed_results = []

            # Document 형태로 변환
            documents = []
            for result in processed_results:
                # 거리를 유사도로 변환 (코사인 거리: 0~2, 유사도: 0~1)
                similarity = 1 - (result['distance'] / 2)

                if similarity >= self.min_similarity:
                    doc = Document(
                        page_content=result['document'],
                        metadata={
                            **result['metadata'],
                            'similarity': similarity,
                            'source': 'housing_vector_db'
                        }
                    )
                    documents.append(doc)

            logger.info(f"Found {len(documents)} relevant documents via {search_type}")
            return documents

        except Exception as e:
            logger.error(f"{search_type} search failed: {e}")
            return []

    def _maximal_marginal_relevance(
        self,
        query_embedding,
        embedding_list,
        documents,
        metadatas,
        distances,
        k: int
    ) -> List[dict]:
        """MMR 알고리즘 구현 (문서 간 유사도 계산)"""
        import numpy as np

        if not embedding_list or len(embedding_list) == 0:
            # embeddings가 없으면 유사도 정렬만
            similarities = [1 - (d / 2) for d in distances]
            candidates = [
                {
                    'document': doc,
                    'metadata': meta,
                    'distance': dist,
                    'similarity': sim
                }
                for doc, meta, dist, sim in zip(documents, metadatas, distances, similarities)
            ]
            candidates.sort(key=lambda x: x['similarity'], reverse=True)
            return candidates[:k]

        # 거리를 유사도로 변환
        query_similarities = [1 - (d / 2) for d in distances]

        # numpy 배열로 변환
        embeddings = np.array(embedding_list)

        # 선택된 문서 인덱스
        selected_indices = []

        # MMR 반복 선택
        for _ in range(min(k, len(documents))):
            best_score = -float('inf')
            best_idx = None

            for idx in range(len(documents)):
                if idx in selected_indices:
                    continue

                # 쿼리 유사도
                query_sim = query_similarities[idx]

                # 이미 선택된 문서들과의 최대 유사도
                if selected_indices:
                    # 코사인 유사도 계산 (normalized embeddings이므로 내적만 계산)
                    selected_embeddings = embeddings[selected_indices]
                    current_embedding = embeddings[idx]

                    similarities_to_selected = np.dot(selected_embeddings, current_embedding)
                    max_sim_to_selected = np.max(similarities_to_selected)
                else:
                    max_sim_to_selected = 0

                # MMR 점수 = λ × (쿼리 유사도) - (1-λ) × (선택된 문서와의 유사도)
                mmr_score = self.lambda_mult * query_sim - (1 - self.lambda_mult) * max_sim_to_selected

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected_indices.append(best_idx)

        # 선택된 문서 반환
        return [
            {
                'document': documents[idx],
                'metadata': metadatas[idx],
                'distance': distances[idx],
                'similarity': query_similarities[idx]
            }
            for idx in selected_indices
        ]

    def _similarity_only(
        self,
        documents,
        metadatas,
        distances
    ) -> List[dict]:
        """유사도만 사용한 정렬 (MMR 없이)"""
        # 거리를 유사도로 변환
        similarities = [1 - (d / 2) for d in distances]

        # 유사도 기준으로 정렬
        results = [
            {
                'document': doc,
                'metadata': meta,
                'distance': dist,
                'similarity': sim
            }
            for doc, meta, dist, sim in zip(documents, metadatas, distances, similarities)
        ]

        # 유사도 내림차순 정렬
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results


# ============================================================================
# 테스트 및 사용 예시
# ============================================================================

"""
GroqHousingRetriever 사용 예시:

# 1. 다양한 옵션 탐색 (MMR 사용)
retriever = GroqHousingRetriever(k=5, use_mmr=True, lambda_mult=0.9)
docs = retriever.get_relevant_documents("강남구 청년주택 추천")

# 2. 조건에 맞는 모든 결과 (유사도만)
retriever = GroqHousingRetriever(k=20, use_mmr=False)
docs = retriever.get_relevant_documents("강남구 청년주택")

# 주의: search_housing tool은 backend/services/llm/utils/inha/housing_tools_inha.py로 이동되었습니다.
"""


