"""
Vector Client
통합 벡터 데이터베이스 클라이언트
ChromaDB + 한국어 임베딩 + 주택 데이터 검색을 하나의 클래스로 통합
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from tqdm import tqdm

from .vector_config import vector_config
from .vector_embeddings import KoreanEmbedder
from .vector_collections import HousingCollection

logger = logging.getLogger(__name__)


class VectorClient:
    """통합 벡터 데이터베이스 클라이언트""" 
    # VectorClient()를 실행하면 자동으로 필요한 부품을 다 장착하는 것
    
    def __init__(self): # initial : 초기화 -. 초기 셋팅하기
        # self. : 이 인스턴스(VectorClient 객체)안에 .~이라는 속성을 저장해주어, 클래스 밖에서도 접근 가능하게 함..!
        # self가 없으면 클래스 밖에서 접근 불가. self.이 없는 변수는 함수 끝나면 사라짐
        self.config = vector_config # 설정값 불러오기
        # VectorClient 자신(client 객체) 안에 config라는 속성을 만들어 넣은 것
        self.embedder = KoreanEmbedder() # 한국어->숫자 임베딩 모델 불러오기
        self.collection = HousingCollection(self.embedder) # 주택데이터를 저장하고 찾는 창고 관리자 불러오기

    def load_csv_data(self, csv_path: str = None) -> None:
        """CSV 파일에서 주택 데이터 로드"""
        csv_path = csv_path or self.config.default_csv_path
        logger.info(f"Loading data from {csv_path}")
        
        # CSV 읽기
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=['주택명'])
        housing_data = df.to_dict('records')
        
        # 데이터 검증 및 정리
        valid_data = self.embedder.validate_housing_data(housing_data)
        
        # 벡터DB에 로드
        self.add_documents(valid_data)
    
    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = None) -> None:
        """문서들을 벡터DB에 추가"""
        batch_size = batch_size or self.config.batch_size
        
        # 임베딩 모델 로드
        if not self.embedder.is_loaded():
            self.embedder.load_model()
        
        logger.info(f"Adding {len(documents)} documents to vector database")
        
        with tqdm(total=len(documents), desc="Loading documents") as pbar:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    self.collection.add_documents(batch, batch_size=len(batch))
                    pbar.update(len(batch))
                except Exception as e:
                    logger.error(f"Failed to add batch: {e}")
                    pbar.update(len(batch))
        
        logger.info(f"Successfully loaded {self.collection.count()} documents")
    
    def search(
        self, 
        query: str, 
        n_results: int = None,
        hybrid: bool = False,
        district: Optional[str] = None,
        dong: Optional[str] = None,
        theme: Optional[str] = None,
        min_similarity: float = None,
        smart_search: bool = True
    ) -> List[Dict[str, Any]]:
        """주택 검색"""
        n_results = n_results or self.config.default_n_results
        min_similarity = min_similarity or self.config.default_similarity_threshold
        
        # 임베딩 모델 로드
        if not self.embedder.is_loaded():
            self.embedder.load_model()
        
        # 쿼리 임베딩 생성
        query_embedding = self.embedder.encode_text(query)
        
        # 필터 설정
        where_filter = {}
        where_document = None
        
        if district:
            where_filter['시군구'] = district
        if dong:
            where_filter['동명'] = dong
        if theme:
            where_document = {"$contains": theme}
        
        # 스마트 검색 (자동으로 지역 키워드 감지)
        if smart_search or hybrid:
            keywords = self._extract_keywords(query)
            if keywords:
                # 지하철역 키워드 우선 처리
                station_keywords = [k for k in keywords if k.endswith(self.config.station_pattern)]
                if station_keywords and not where_document:
                    station_conditions = [{"$contains": k} for k in station_keywords]
                    where_document = {"$or": station_conditions} if len(station_conditions) > 1 else station_conditions[0]
                    logger.info(f"Smart search: Auto-filtering by stations {station_keywords}")
                
                # 지역 키워드 처리 (지하철역이 아닌 경우)
                elif not station_keywords:
                    district_keywords = [k for k in keywords if any(x in k for x in self.config.location_patterns)]
                    dong_keywords = [k for k in keywords if "동" in k and k not in district_keywords]
                    
                    # 지역 필터가 명시적으로 설정되지 않았고 지역 키워드가 있으면 자동 적용
                    if not district and not dong and (district_keywords or dong_keywords):
                        if district_keywords:
                            where_filter['시군구'] = district_keywords[0]
                            logger.info(f"Smart search: Auto-filtering by district '{district_keywords[0]}'")
                        if dong_keywords:
                            where_filter['동명'] = dong_keywords[0]
                            logger.info(f"Smart search: Auto-filtering by dong '{dong_keywords[0]}'")
                
                # 테마 키워드 처리
                found_themes = [k for k in keywords if k in self.config.theme_keywords]
                
                if found_themes and not theme:
                    theme_conditions = [{"$contains": k} for k in found_themes]
                    if where_document:
                        # 기존 문서 필터와 테마 조건 결합
                        if isinstance(where_document, dict) and "$or" in where_document:
                            where_document["$or"].extend(theme_conditions)
                        else:
                            where_document = {"$or": [where_document] + theme_conditions}
                    else:
                        where_document = {"$or": theme_conditions} if len(theme_conditions) > 1 else theme_conditions[0]
                    logger.info(f"Smart search: Auto-filtering by themes {found_themes}")
        
        # 검색 실행
        results = self.collection.search(
            query_embedding=query_embedding,
            n_results=n_results,
            where_filter=where_filter if where_filter else None,
            where_document=where_document
        )
        
        # 최소 유사도 필터링
        filtered_results = [r for r in results if r['similarity'] >= min_similarity]
        
        return filtered_results
    
    def _extract_keywords(self, query: str) -> List[str]:
        """쿼리에서 키워드 추출"""
        keywords = []
        
        # 테마 키워드
        for keyword in self.config.theme_keywords:
            if keyword in query:
                keywords.append(keyword)
        
        # 지역 키워드 (지하철역 제외)
        words = query.split()
        for word in words:
            # 지하철역이 아닌 지역 키워드만 추출
            if any(suffix in word for suffix in self.config.location_patterns) and not word.endswith(self.config.station_pattern):
                keywords.append(word)
            # 지하철역은 별도 처리 (문서 내용 검색용)
            elif word.endswith(self.config.station_pattern):
                keywords.append(word)
        
        return list(set(keywords))
    
    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보"""
        return self.collection.get_statistics()
    
    def clear_database(self) -> None:
        """데이터베이스 초기화"""
        self.collection.clear()
        logger.info("Database cleared successfully")
    
    def get_info(self) -> Dict[str, Any]:
        """데이터베이스 정보"""
        self.collection.connect()
        collections = [col.name for col in self.collection.client.list_collections()]
        
        info = {
            "persist_directory": str(self.config.persist_directory),
            "embedding_model": self.config.embedding_model,
            "collections": collections,
            "total_collections": len(collections)
        }
        
        if self.config.housing_collection_name in collections:
            info["housing_collection"] = {
                "name": self.config.housing_collection_name,
                "count": self.collection.count()
            }
        
        return info
