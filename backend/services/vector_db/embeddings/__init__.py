"""
Embedding models for vector database
"""

from .base import BaseEmbedder
from .korean import KoreanEmbedder

__all__ = ["BaseEmbedder", "KoreanEmbedder"]
