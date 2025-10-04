"""
Vector Database Configuration
"""

from pathlib import Path
from typing import Optional


class VectorDBConfig:
    """ChromaDB configuration settings"""
    
    def __init__(self):
        # ChromaDB settings
        self.persist_directory = Path("./data/chroma_db")
        
        # Embedding model settings
        self.embedding_model = "jhgan/ko-sbert-nli"
        
        # Collection settings
        self.housing_collection_name = "housing_embeddings"
        
        # Performance settings
        self.batch_size = 32
        self.max_results = 50
        
        # Device settings
        self.device: Optional[str] = None


# Global config instance
vector_db_config = VectorDBConfig()
