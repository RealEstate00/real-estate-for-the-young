"""
Vector Database Service (Inha) - 간소화된 4파일 구조
"""

from .vector_client import VectorClient
from .vector_config import vector_config
from .vector_embeddings import KoreanEmbedder
from .vector_collections import HousingCollection

__all__ = ["VectorClient", "vector_config", "KoreanEmbedder", "HousingCollection"]

# 버전 정보
__version__ = "2.1.0"
__description__ = "Simplified 4-file Vector Database Service for Housing Search"
