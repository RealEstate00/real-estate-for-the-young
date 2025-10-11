"""
LLM Model Factory
Ollama와 OpenAI 모델을 선택적으로 사용
"""

from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from typing import Literal, Optional
import os
import logging

logger = logging.getLogger(__name__)


ModelType = Literal["ollama", "openai"]


class ModelFactory:
    """
    LLM 모델 팩토리
    환경에 따라 Ollama 또는 OpenAI 선택
    """
    
    @staticmethod
    def create_llm(
        model_type: ModelType = "ollama",
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs
    ):
        """
        Create LLM instance
        
        Args:
            model_type: "ollama" or "openai"
            model_name: Model name (None for default)
            temperature: Creativity level (0.0 = deterministic)
            **kwargs: Additional model parameters
            
        Returns:
            LLM instance
        """
        if model_type == "ollama":
            return ModelFactory._create_ollama(model_name, temperature, **kwargs)
        elif model_type == "openai":
            return ModelFactory._create_openai(model_name, temperature, **kwargs)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    @staticmethod
    def _create_ollama(
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> Ollama:
        """
        Create Ollama LLM
        
        Recommended models for Korean:
        - llama3.2 (3B) - Fast, lightweight
        - gemma2:9b - Google model, good multilingual
        - eeve-korean-10.8b - Korean-specific
        - qwen2.5:7b - Good multilingual support
        """
        if model_name is None:
            model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        logger.info(f"Creating Ollama LLM with model: {model_name}")
        
        return Ollama(
            model=model_name,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            **kwargs
        )
    
    @staticmethod
    def _create_openai(
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> ChatOpenAI:
        """Create OpenAI LLM"""
        if model_name is None:
            model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        logger.info(f"Creating OpenAI LLM with model: {model_name}")
        
        return ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=api_key,
            **kwargs
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def get_default_llm(model_type: ModelType = "ollama"):
    """
    Get default LLM instance
    
    Args:
        model_type: "ollama" or "openai"
        
    Returns:
        LLM instance
    """
    return ModelFactory.create_llm(model_type=model_type)