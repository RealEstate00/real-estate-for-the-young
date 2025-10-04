"""
Vector Database Service Module

This module provides vector database functionality using ChromaDB
for housing data embeddings and similarity search.
"""

from .client import VectorDBClient
from .embeddings.korean import KoreanEmbedder
from .collections.housing import HousingCollection

__all__ = [
    "VectorDBClient",
    "KoreanEmbedder", 
    "HousingCollection"
]
