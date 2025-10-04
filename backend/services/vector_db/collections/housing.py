"""
Housing collection for vector database
"""

import hashlib
from typing import Dict, Any, List, Optional
import logging

from .base import BaseCollection
from ..config import vector_db_config

logger = logging.getLogger(__name__)


class HousingCollection(BaseCollection):
    """Collection for housing data embeddings"""
    
    def __init__(self, client, embedder):
        super().__init__(
            client=client,
            embedder=embedder,
            collection_name=vector_db_config.housing_collection_name
        )
    
    def get_collection_metadata(self) -> Dict[str, Any]:
        """Get metadata for the housing collection"""
        return {
            "description": "Housing data embeddings for similarity search",
            "embedding_model": self.embedder.model_name,
            "data_source": "housing_vector_data.csv",
            "version": "1.0"
        }
    
    def prepare_document(self, housing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare housing data for storage"""
        
        # Generate unique ID based on housing name and address
        id_string = f"{housing_data.get('주택명', '')}-{housing_data.get('도로명주소', '')}"
        doc_id = hashlib.md5(id_string.encode('utf-8')).hexdigest()
        
        # Generate embedding
        embedding = self.embedder.embed_housing_data(housing_data)
        
        # Create document text for storage
        document_text = self.embedder.create_housing_text(housing_data)
        
        # Prepare metadata (all searchable fields)
        metadata = {
            "주택명": housing_data.get('주택명', ''),
            "지번주소": housing_data.get('지번주소', ''),
            "도로명주소": housing_data.get('도로명주소', ''),
            "시군구": housing_data.get('시군구', ''),
            "동명": housing_data.get('동명', ''),
            "태그": housing_data.get('태그', '')
        }
        
        # Parse tags for better filtering
        tags_info = self._parse_tags(housing_data.get('태그', ''))
        metadata.update(tags_info)
        
        return {
            'id': doc_id,
            'embedding': embedding,
            'metadata': metadata,
            'document': document_text
        }
    
    def _parse_tags(self, tags_string: str) -> Dict[str, Any]:
        """Parse tags string into structured metadata"""
        parsed = {}
        
        if not tags_string:
            return parsed
        
        # Split by comma and parse each tag
        tag_parts = tags_string.split(', ')
        
        for part in tag_parts:
            if ':' in part:
                key, value = part.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Map Korean keys to English for easier filtering
                key_mapping = {
                    '테마': 'theme',
                    '지하철': 'subway',
                    '자격요건': 'requirements',
                    '마트': 'mart',
                    '병원': 'hospital',
                    '학교': 'school',
                    '시설': 'facilities',
                    '카페': 'cafe'
                }
                
                english_key = key_mapping.get(key, key)
                parsed[english_key] = value
                
                # Also keep original Korean key
                parsed[key] = value
        
        return parsed
    
    def search_by_location(
        self, 
        query: str, 
        district: Optional[str] = None,
        dong: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search housing by location"""
        
        where_filter = {}
        
        if district:
            where_filter['시군구'] = district
            
        if dong:
            where_filter['동명'] = dong
        
        return self.search_similar(
            query=query,
            n_results=n_results,
            where=where_filter if where_filter else None
        )
    
    def search_by_keyword(
        self,
        query: str,
        min_similarity: float = 0.2,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Smart hybrid search: keyword matching + vector search"""
        
        # 1. 키워드 추출
        keywords = self._extract_keywords(query)
        logger.info(f"Extracted keywords: {keywords}")
        
        # 2. 키워드 기반 필터링 시도
        keyword_results = []
        
        if keywords:
            # 테마 키워드 우선 처리
            theme_keywords = ["청년", "신혼", "육아", "시니어", "예술", "반려동물", "여성안심"]
            found_themes = [k for k in keywords if k in theme_keywords]
            
            if found_themes:
                # 테마 기반 검색
                keyword_results = self.search_by_theme(
                    query=query,
                    theme_keywords=found_themes,
                    n_results=n_results * 2
                )
                logger.info(f"Theme-based search found {len(keyword_results)} results")
            
            # 지역 키워드 처리
            if not keyword_results:
                district_keywords = [k for k in keywords if any(x in k for x in ["구", "시", "군"])]
                dong_keywords = [k for k in keywords if "동" in k and k not in district_keywords]
                
                if district_keywords or dong_keywords:
                    district = district_keywords[0] if district_keywords else None
                    dong = dong_keywords[0] if dong_keywords else None
                    
                    keyword_results = self.search_by_location(
                        query=query,
                        district=district,
                        dong=dong,
                        n_results=n_results * 2
                    )
                    logger.info(f"Location-based search found {len(keyword_results)} results")
        
        # 3. 키워드 결과가 없으면 일반 벡터 검색
        if not keyword_results:
            logger.info("No keyword matches, falling back to vector search")
            vector_results = self.search_similar(query=query, n_results=n_results * 2)
        else:
            vector_results = keyword_results
        
        # 4. 최소 유사도 필터링
        filtered_results = [
            result for result in vector_results 
            if result['similarity'] >= min_similarity
        ]
        
        # 5. 결과가 너무 적으면 임계값을 낮춰서 재검색
        if len(filtered_results) < 3 and min_similarity > 0.1:
            logger.warning(f"Low similarity results, lowering threshold from {min_similarity} to 0.1")
            filtered_results = [
                result for result in vector_results 
                if result['similarity'] >= 0.1
            ]
        
        # 6. 여전히 결과가 없으면 키워드 무시하고 벡터 검색
        if not filtered_results:
            logger.warning("No results with keyword filtering, trying pure vector search")
            vector_results = self.search_similar(query=query, n_results=n_results)
            filtered_results = [
                result for result in vector_results 
                if result['similarity'] >= 0.0  # 모든 결과 포함
            ]
        
        return filtered_results[:n_results]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        keywords = []
        
        # 지하철역 키워드
        subway_keywords = ["역", "지하철", "전철"]
        for keyword in subway_keywords:
            if keyword in query:
                # "홍대입구역"과 같은 역명 추출
                words = query.split()
                for word in words:
                    if "역" in word:
                        keywords.append(word)
        
        # 지역명 키워드
        district_keywords = ["구", "동", "시", "군"]
        for keyword in district_keywords:
            if keyword in query:
                words = query.split()
                for word in words:
                    if any(dk in word for dk in district_keywords):
                        keywords.append(word)
        
        # 주택 유형 키워드
        housing_keywords = ["주택", "아파트", "빌라", "원룸", "투룸", "쉐어하우스", "공동체주택"]
        for keyword in housing_keywords:
            if keyword in query:
                keywords.append(keyword)
        
        # 테마 키워드
        theme_keywords = ["청년", "신혼", "육아", "시니어", "예술", "반려동물", "여성안심"]
        for keyword in theme_keywords:
            if keyword in query:
                keywords.append(keyword)
        
        return list(set(keywords))  # 중복 제거
    
    def search_by_theme(
        self, 
        query: str, 
        theme_keywords: Optional[List[str]] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search housing by theme"""
        
        where_document = None
        if theme_keywords:
            # Create document filter for theme keywords
            theme_conditions = []
            for keyword in theme_keywords:
                theme_conditions.append({"$contains": keyword})
            
            if len(theme_conditions) == 1:
                where_document = theme_conditions[0]
            else:
                where_document = {"$or": theme_conditions}
        
        return self.search_similar(
            query=query,
            n_results=n_results,
            where_document=where_document
        )
    
    def search_by_requirements(
        self, 
        query: str, 
        requirement_type: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search housing by requirements"""
        
        where_filter = {}
        if requirement_type:
            where_filter['requirements'] = {"$contains": requirement_type}
        
        return self.search_similar(
            query=query,
            n_results=n_results,
            where=where_filter if where_filter else None
        )
    
    def get_housing_statistics(self) -> Dict[str, Any]:
        """Get statistics about housing data"""
        collection = self._get_collection()
        
        try:
            # Get all documents to analyze
            all_docs = collection.get(include=['metadatas'])
            
            if not all_docs['metadatas']:
                return {"total_count": 0}
            
            # Analyze metadata
            districts = {}
            themes = {}
            requirements = {}
            
            for metadata in all_docs['metadatas']:
                # Count districts
                district = metadata.get('시군구', '')
                if district:
                    districts[district] = districts.get(district, 0) + 1
                
                # Count themes
                theme = metadata.get('theme', '')
                if theme:
                    theme_parts = theme.split()
                    for part in theme_parts:
                        themes[part] = themes.get(part, 0) + 1
                
                # Count requirements
                req = metadata.get('requirements', '')
                if req:
                    requirements[req] = requirements.get(req, 0) + 1
            
            return {
                "total_count": len(all_docs['metadatas']),
                "districts": dict(sorted(districts.items(), key=lambda x: x[1], reverse=True)),
                "themes": dict(sorted(themes.items(), key=lambda x: x[1], reverse=True)),
                "requirements": dict(sorted(requirements.items(), key=lambda x: x[1], reverse=True))
            }
            
        except Exception as e:
            logger.error(f"Failed to get housing statistics: {e}")
            raise
