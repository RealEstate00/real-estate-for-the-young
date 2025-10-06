"""
Vector Database Configuration
간소화된 벡터 데이터베이스 설정
"""

from pathlib import Path
from typing import Optional


class VectorConfig:
    """벡터 데이터베이스 설정"""
    
    def __init__(self):
        # ChromaDB 설정
        self.persist_directory = Path("backend/data/chroma_db/inha")
        
        # 임베딩 모델 설정
        self.embedding_model = "jhgan/ko-sbert-nli"
        
        # 컬렉션 설정
        self.housing_collection_name = "housing_embeddings"
        
        # 성능 설정
        self.batch_size = 32
        self.max_results = 50
        
        # 디바이스 설정
        self.device: Optional[str] = None
        
        # CSV 파일 경로
        self.default_csv_path = "backend/data/raw/for_vectorDB/housing_vector_data.csv"
        
        # 검색 설정
        self.default_similarity_threshold = 0.1
        self.default_n_results = 10
        
        # 테마 키워드
        self.theme_keywords = ["청년", "신혼", "육아", "시니어", "예술", "반려동물", "여성안심"]
        
        # 지역 키워드 패턴
        self.location_patterns = ["구", "동", "시", "군"]
        self.station_pattern = "역"


# 전역 설정 인스턴스
vector_config = VectorConfig()
