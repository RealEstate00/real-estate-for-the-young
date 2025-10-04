"""
Base embedder class for vector database
"""

from abc import ABC, abstractmethod
from typing import List, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Base class for embedding models"""
    
    def __init__(self, model_name: str, device: str = None):
        self.model_name = model_name
        self.device = device
        self.model = None
        
    @abstractmethod
    def load_model(self) -> None:
        """Load the embedding model"""
        pass
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Encode text(s) into embeddings"""
        pass
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Encode texts in batches for memory efficiency"""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch)
            
            # Handle single text vs batch
            if isinstance(batch_embeddings[0], float):
                embeddings.append(batch_embeddings)
            else:
                embeddings.extend(batch_embeddings)
                
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        if self.model is None:
            self.load_model()
        
        # Test with a simple text
        test_embedding = self.encode("test")
        return len(test_embedding)
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None
