# backend/services/api/routers/llm.py
"""
LLM API Router
LLM 기능을 위한 FastAPI 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging

from backend.services.llm.langchain.chains.rag_chain import HousingRAGChain, create_rag_chain
from backend.services.llm.models.model_factory import ModelType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM"])


# =============================================================================
# Request/Response Models
# =============================================================================

class QuestionRequest(BaseModel):
    """질문 요청 모델"""
    question: str = Field(..., description="사용자 질문")
    model_type: ModelType = Field(default="ollama", description="사용할 모델 타입")
    with_memory: bool = Field(default=False, description="대화 기록 사용 여부")


class SourceInfo(BaseModel):
    """출처 정보 모델"""
    title: str = Field(..., description="주택명")
    address: str = Field(..., description="주소")
    district: str = Field(..., description="시군구")


class QuestionResponse(BaseModel):
    """질문 응답 모델"""
    answer: str = Field(..., description="생성된 답변")
    sources: List[SourceInfo] = Field(default=[], description="참고 문서")


class RecommendationRequest(BaseModel):
    """추천 요청 모델"""
    location: str = Field(..., description="희망 위치", example="강남구")
    budget: str = Field(..., description="예산 범위", example="월세 50만원 이하")
    preferences: str = Field(..., description="선호 조건", example="지하철역 근처")
    model_type: ModelType = Field(default="ollama", description="사용할 모델 타입")


class CandidateInfo(BaseModel):
    """추천 후보 정보"""
    title: str
    address: str
    district: str


class RecommendationResponse(BaseModel):
    """추천 응답 모델"""
    recommendation: str = Field(..., description="추천 설명")
    candidates: List[CandidateInfo] = Field(..., description="추천 후보 목록")


class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str = Field(..., description="역할 (user/assistant)")
    content: str = Field(..., description="메시지 내용")


class ChatRequest(BaseModel):
    """채팅 요청"""
    messages: List[ChatMessage] = Field(..., description="대화 히스토리")
    model_type: ModelType = Field(default="ollama", description="모델 타입")


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str = Field(..., description="AI 응답")
    sources: List[SourceInfo] = Field(default=[], description="참고 문서")


# =============================================================================
# Dependency: RAG Chain Instance
# =============================================================================

_rag_instances: Dict[str, HousingRAGChain] = {}


def get_rag_chain(
    model_type: ModelType = "ollama",
    with_memory: bool = False
) -> HousingRAGChain:
    """
    Get or create RAG chain instance (singleton per model type)
    
    Args:
        model_type: Model type to use
        with_memory: Enable conversation memory
        
    Returns:
        HousingRAGChain instance
    """
    key = f"{model_type}_{with_memory}"
    
    if key not in _rag_instances:
        logger.info(f"Creating new RAG chain: {key}")
        _rag_instances[key] = create_rag_chain(
            model_type=model_type,
            with_memory=with_memory
        )
    
    return _rag_instances[key]


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    질문에 답변하기
    
    **사용 예시:**
```json
    {
        "question": "강남역 근처 청년주택 알려줘",
        "model_type": "ollama",
        "with_memory": false
    }