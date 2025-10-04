"""
Korean language embedder using ko-sbert-nli model
"""

from typing import List, Union, Dict, Any
import logging
from sentence_transformers import SentenceTransformer

from .base import BaseEmbedder

logger = logging.getLogger(__name__)


class KoreanEmbedder(BaseEmbedder):
    """Korean language embedder using jhgan/ko-sbert-nli model"""
    
    def __init__(self, model_name: str = "jhgan/ko-sbert-nli", device: str = None):
        super().__init__(model_name, device)
        
    def load_model(self) -> None:
        """Load the Korean SBERT model"""
        try:
            logger.info(f"Loading Korean embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            logger.info("Korean embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Korean embedding model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Encode Korean text(s) into embeddings"""
        if self.model is None:
            self.load_model()
        
        try:
            # Convert to list if single string
            is_single = isinstance(texts, str)
            if is_single:
                texts = [texts]
            
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                convert_to_tensor=False,
                normalize_embeddings=True  # Normalize for better similarity search
            )
            
            # Convert to list format
            embeddings = embeddings.tolist()
            
            # Return single embedding if input was single string
            if is_single:
                return embeddings[0]
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise
    
    def create_housing_text(self, housing_data: Dict[str, Any]) -> str:
        """Create optimized text representation for housing data"""
        parts = []
        
        # Add housing name
        if housing_data.get('주택명'):
            parts.append(f"주택명: {housing_data['주택명']}")
        
        # Add location information
        if housing_data.get('도로명주소'):
            parts.append(f"주소: {housing_data['도로명주소']}")
        
        if housing_data.get('시군구'):
            parts.append(f"지역: {housing_data['시군구']}")
            
        if housing_data.get('동명'):
            parts.append(f"동: {housing_data['동명']}")
        
        # Add detailed tags/features
        if housing_data.get('태그'):
            parts.append(f"특성: {housing_data['태그']}")
        
        return " ".join(parts)
    
    def embed_housing_data(self, housing_data: Dict[str, Any]) -> List[float]:
        """Create embedding for housing data"""
        text = self.create_housing_text(housing_data)
        return self.encode(text)
    
    def embed_housing_batch(self, housing_data_list: List[Dict[str, Any]], batch_size: int = 32) -> List[List[float]]:
        """Create embeddings for batch of housing data"""
        texts = [self.create_housing_text(data) for data in housing_data_list]
        return self.encode_batch(texts, batch_size)
