"""
LLM Factory - LLM 초기화 및 싱글톤 관리

다양한 LLM 제공자를 지원하고 싱글톤 패턴으로 인스턴스를 관리합니다.
"""

from enum import Enum
from typing import Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class LLMType(Enum):
    """지원하는 LLM 타입"""
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    OPENAI_GPT4O = "openai_gpt4o"
    OLLAMA_GEMMA3 = "ollama_gemma3"
    GROQ_LLAMA3 = "groq_llama3"


class LLMFactory:
    """LLM 팩토리 (싱글톤)"""
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_llm(cls, llm_type: LLMType, **kwargs) -> Any:
        """
        LLM 인스턴스 반환 (싱글톤)
        
        Args:
            llm_type: LLM 타입
            **kwargs: LLM별 추가 설정
            
        Returns:
            LLM 인스턴스
        """
        cache_key = f"{llm_type.value}_{hash(str(sorted(kwargs.items())))}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls._create_llm(llm_type, **kwargs)
            
        return cls._instances[cache_key]
    
    @classmethod
    def _create_llm(cls, llm_type: LLMType, **kwargs) -> Any:
        """LLM 인스턴스 생성"""
        
        if llm_type == LLMType.OPENAI_GPT4O_MINI:
            return cls._create_openai_llm("gpt-4o-mini", **kwargs)
        elif llm_type == LLMType.OPENAI_GPT4O:
            return cls._create_openai_llm("gpt-4o", **kwargs)
        elif llm_type == LLMType.OLLAMA_GEMMA3:
            return cls._create_ollama_llm("gemma3:4b", **kwargs)
        elif llm_type == LLMType.GROQ_LLAMA3:
            return cls._create_groq_llm("llama-3.3-70b-versatile", **kwargs)
        else:
            raise ValueError(f"지원하지 않는 LLM 타입: {llm_type}")
    
    @classmethod
    def _create_openai_llm(cls, model: str, **kwargs):
        """OpenAI LLM 생성"""
        try:
            from langchain_openai import ChatOpenAI
            
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
            
            return ChatOpenAI(
                model=model,
                api_key=api_key,
                temperature=kwargs.get("temperature", 0),
                max_tokens=kwargs.get("max_tokens", None),
                **{k: v for k, v in kwargs.items() if k not in ["api_key", "temperature", "max_tokens"]}
            )
            
        except ImportError:
            raise ImportError("langchain_openai 패키지가 설치되지 않았습니다")
    
    @classmethod
    def _create_ollama_llm(cls, model: str, **kwargs):
        """Ollama LLM 생성"""
        try:
            from langchain_ollama import ChatOllama
            
            return ChatOllama(
                model=model,
                temperature=kwargs.get("temperature", 0),
                base_url=kwargs.get("base_url", "http://localhost:11434"),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "base_url"]}
            )
            
        except ImportError:
            raise ImportError("langchain_ollama 패키지가 설치되지 않았습니다")
    
    @classmethod
    def _create_groq_llm(cls, model: str, **kwargs):
        """Groq LLM 생성"""
        try:
            from langchain_groq import ChatGroq
            
            api_key = kwargs.get("api_key") or os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY가 설정되지 않았습니다")
            
            return ChatGroq(
                model=model,
                api_key=api_key,
                temperature=kwargs.get("temperature", 0),
                max_tokens=kwargs.get("max_tokens", None),
                **{k: v for k, v in kwargs.items() if k not in ["api_key", "temperature", "max_tokens"]}
            )
            
        except ImportError:
            raise ImportError("langchain_groq 패키지가 설치되지 않았습니다")
    
    @classmethod
    def clear_cache(cls):
        """캐시 초기화"""
        cls._instances.clear()


# 편의 함수
def get_llm(llm_type: LLMType, **kwargs) -> Any:
    """
    LLM 인스턴스 반환
    
    Args:
        llm_type: LLM 타입
        **kwargs: LLM별 추가 설정
        
    Returns:
        LLM 인스턴스
    """
    return LLMFactory.get_llm(llm_type, **kwargs)


def get_default_llm() -> Any:
    """
    기본 LLM 반환 (환경변수 기반)
    
    Returns:
        기본 LLM 인스턴스
    """
    # 환경변수에서 기본 LLM 설정 확인
    default_provider = os.getenv("AGENT_PROVIDER", "openai").lower()
    default_model = os.getenv("AGENT_MODEL", "gpt-4o-mini")
    
    if default_provider == "openai":
        if "gpt-4o-mini" in default_model:
            return get_llm(LLMType.OPENAI_GPT4O_MINI)
        elif "gpt-4o" in default_model:
            return get_llm(LLMType.OPENAI_GPT4O)
    elif default_provider == "ollama":
        return get_llm(LLMType.OLLAMA_GEMMA3)
    elif default_provider == "groq":
        return get_llm(LLMType.GROQ_LLAMA3)
    
    # 기본값: OpenAI GPT-4o-mini
    logger.warning(f"알 수 없는 LLM 설정 ({default_provider}/{default_model}), 기본값 사용")
    return get_llm(LLMType.OPENAI_GPT4O_MINI)
