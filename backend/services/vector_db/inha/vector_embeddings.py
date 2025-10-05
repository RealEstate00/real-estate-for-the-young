"""
Vector Embeddings
한국어 임베딩 및 텍스트 처리
"""

import logging
import pandas as pd
from typing import Dict, Any, List, Union
from sentence_transformers import SentenceTransformer

from .vector_config import vector_config

logger = logging.getLogger(__name__)


class KoreanEmbedder:
    """한국어 임베딩 처리 클래스"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or vector_config.embedding_model
        self.model = None
        
    def load_model(self) -> None:
        """임베딩 모델 로드"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
    
    def is_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.model is not None
    
    def encode_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """텍스트를 임베딩으로 변환"""
        if not self.is_loaded():
            self.load_model()
        
        is_single = isinstance(text, str)
        if is_single:
            text = [text]
        
        embeddings = self.model.encode(
            text, 
            convert_to_tensor=False, 
            normalize_embeddings=True
        ).tolist()
        
        return embeddings[0] if is_single else embeddings
    
    def create_housing_text(self, housing_data: Dict[str, Any]) -> str:
        """주택 데이터를 검색용 텍스트로 변환"""
        parts = []
        
        if housing_data.get('주택명'):
            parts.append(f"주택명: {housing_data['주택명']}")
        if housing_data.get('도로명주소'):
            parts.append(f"주소: {housing_data['도로명주소']}")
        if housing_data.get('시군구'):
            parts.append(f"지역: {housing_data['시군구']}")
        if housing_data.get('동명'):
            parts.append(f"동: {housing_data['동명']}")
        if housing_data.get('태그'):
            parts.append(f"특성: {housing_data['태그']}")
        
        return " ".join(parts)
    
    def parse_tags(self, tags_string: str) -> Dict[str, str]:
        """태그 문자열을 구조화된 메타데이터로 파싱"""
        parsed = {}
        if not tags_string:
            return parsed
        
        tag_parts = tags_string.split(', ')
        key_mapping = {
            '테마': 'theme', '지하철': 'subway', '자격요건': 'requirements',
            '마트': 'mart', '병원': 'hospital', '학교': 'school',
            '시설': 'facilities', '카페': 'cafe'
        }
        
        for part in tag_parts:
            if ':' in part:
                key, value = part.split(':', 1)
                key, value = key.strip(), value.strip()
                english_key = key_mapping.get(key, key)
                parsed[english_key] = value
        
        return parsed
    
    def embed_housing_data(self, housing_data: Dict[str, Any]) -> List[float]:
        """주택 데이터를 임베딩으로 변환"""
        text = self.create_housing_text(housing_data)
        return self.encode_text(text)
    
    def validate_housing_data(self, housing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """주택 데이터 검증 및 정리"""
        valid_data = []
        
        for i, record in enumerate(housing_data):
            try:
                # 필수 필드 확인
                if not record.get('주택명'):
                    logger.warning(f"Record {i}: Missing 주택명, skipping")
                    continue
                
                # 문자열 필드 정리
                for field in ['주택명', '지번주소', '도로명주소', '시군구', '동명', '태그']:
                    if pd.isna(record.get(field)):
                        record[field] = ''
                    else:
                        record[field] = str(record[field]).strip()
                
                valid_data.append(record)
                
            except Exception as e:
                logger.warning(f"Record {i}: Validation error - {e}, skipping")
                continue
        
        logger.info(f"Validated {len(valid_data)} out of {len(housing_data)} records")
        return valid_data
