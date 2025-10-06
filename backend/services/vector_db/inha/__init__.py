"""
Vector Database Service (Inha) - All-in-One ChromaDB
"""

from .chromadb import (
    HousingVectorDB,
    VectorConfig,
    KoreanEmbedder,
    HousingCollection
)

__all__ = [
    "HousingVectorDB",
    "VectorConfig", 
    "KoreanEmbedder",
    "HousingCollection"
]

# 버전 정보
__version__ = "3.0.0"
__description__ = "All-in-One Housing Vector Database with Text Chunking"
