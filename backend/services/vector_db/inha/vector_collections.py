"""
Vector Collections
ChromaDB 컬렉션 관리 및 검색
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.config import Settings

from .vector_config import vector_config
from .vector_embeddings import KoreanEmbedder

logger = logging.getLogger(__name__)


class HousingCollection:
    """주택 데이터 컬렉션 관리"""
    
    def __init__(self, embedder: KoreanEmbedder = None):
        self.config = vector_config
        self.embedder = embedder or KoreanEmbedder()
        self.client = None
        self.collection = None
        
        # 디렉토리 생성
        self.config.persist_directory.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> None:
        """ChromaDB 연결"""
        if self.client is None:
            logger.info(f"Connecting to ChromaDB at {self.config.persist_directory}")
            self.client = chromadb.PersistentClient(
                path=str(self.config.persist_directory),
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            logger.info("Connected to ChromaDB")
    
    def disconnect(self) -> None:
        """ChromaDB 연결 해제"""
        if self.client:
            self.client = None
            self.collection = None
            logger.info("Disconnected from ChromaDB")
    
    def get_collection(self):
        """컬렉션 가져오기 또는 생성"""
        if self.collection is None:
            self.connect()
            try:
                self.collection = self.client.get_collection(self.config.housing_collection_name)
                logger.info(f"Retrieved existing collection: {self.config.housing_collection_name}")
            except:
                # 커스텀 임베딩 함수 생성
                from chromadb.utils import embedding_functions
                embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.config.embedding_model
                )
                
                self.collection = self.client.create_collection(
                    name=self.config.housing_collection_name,
                    metadata={
                        "description": "Housing data embeddings",
                        "model": self.config.embedding_model
                    },
                    embedding_function=embedding_function
                )
                logger.info(f"Created new collection: {self.config.housing_collection_name}")
        return self.collection
    
    def prepare_document(self, housing_data: Dict[str, Any]) -> Dict[str, Any]:
        """주택 데이터를 벡터DB 문서로 준비"""
        # 고유 ID 생성
        id_string = f"{housing_data.get('주택명', '')}-{housing_data.get('도로명주소', '')}"
        doc_id = hashlib.md5(id_string.encode('utf-8')).hexdigest()
        
        # 텍스트 및 임베딩 생성
        document_text = self.embedder.create_housing_text(housing_data)
        embedding = self.embedder.encode_text(document_text)
        
        # 메타데이터 준비
        metadata = {
            "주택명": housing_data.get('주택명', ''),
            "지번주소": housing_data.get('지번주소', ''),
            "도로명주소": housing_data.get('도로명주소', ''),
            "시군구": housing_data.get('시군구', ''),
            "동명": housing_data.get('동명', ''),
            "태그": housing_data.get('태그', '')
        }
        
        # 태그 파싱 추가
        metadata.update(self.embedder.parse_tags(housing_data.get('태그', '')))
        
        return {
            'id': doc_id,
            'embedding': embedding,
            'metadata': metadata,
            'document': document_text
        }
    
    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = None) -> None:
        """문서들을 벡터DB에 추가"""
        collection = self.get_collection()
        batch_size = batch_size or self.config.batch_size
        
        logger.info(f"Adding {len(documents)} documents to vector database")
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # 배치 데이터 준비
            ids, embeddings, metadatas, documents_text = [], [], [], []
            
            for doc in batch:
                prepared = self.prepare_document(doc)
                ids.append(prepared['id'])
                embeddings.append(prepared['embedding'])
                metadatas.append(prepared['metadata'])
                documents_text.append(prepared['document'])
            
            # 컬렉션에 추가
            try:
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_text
                )
            except Exception as e:
                logger.error(f"Failed to add batch: {e}")
                continue
        
        logger.info(f"Successfully loaded {collection.count()} documents")
    
    def search(
        self, 
        query_embedding: List[float],
        n_results: int = None,
        where_filter: Dict = None,
        where_document: Dict = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색 실행"""
        collection = self.get_collection()
        n_results = n_results or self.config.default_n_results
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results * 2,  # 여유분 확보
                where=where_filter,
                where_document=where_document,
                include=['metadatas', 'documents', 'distances']
            )
            
            # 결과 포맷팅
            formatted_results = []
            for i in range(len(results['ids'][0])):
                distance = results['distances'][0][i]
                similarity = max(-1.0, min(1.0, 1 - distance))  # 코사인 유사도로 변환
                
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity': similarity
                }
                formatted_results.append(result)
            
            # 유사도 기준 정렬 후 상위 n_results 반환
            formatted_results.sort(key=lambda x: x['similarity'], reverse=True)
            return formatted_results[:n_results]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def count(self) -> int:
        """컬렉션 내 문서 수 반환"""
        collection = self.get_collection()
        return collection.count()
    
    def clear(self) -> None:
        """컬렉션 초기화"""
        self.connect()
        try:
            existing_collections = [col.name for col in self.client.list_collections()]
            if self.config.housing_collection_name in existing_collections:
                self.client.delete_collection(self.config.housing_collection_name)
                self.collection = None
                logger.info(f"Cleared collection: {self.config.housing_collection_name}")
            else:
                logger.info("Collection does not exist, nothing to clear")
        except Exception as e:
            logger.warning(f"Failed to clear collection: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """컬렉션 통계 정보"""
        collection = self.get_collection()
        
        try:
            all_docs = collection.get(include=['metadatas'])
            
            if not all_docs['metadatas']:
                return {"total_count": 0}
            
            # 통계 분석
            districts, themes = {}, {}
            
            for metadata in all_docs['metadatas']:
                # 지역 통계
                district = metadata.get('시군구', '')
                if district:
                    districts[district] = districts.get(district, 0) + 1
                
                # 테마 통계
                theme = metadata.get('theme', '')
                if theme:
                    for part in theme.split():
                        themes[part] = themes.get(part, 0) + 1
            
            return {
                "total_count": len(all_docs['metadatas']),
                "districts": dict(sorted(districts.items(), key=lambda x: x[1], reverse=True)),
                "themes": dict(sorted(themes.items(), key=lambda x: x[1], reverse=True))
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise
