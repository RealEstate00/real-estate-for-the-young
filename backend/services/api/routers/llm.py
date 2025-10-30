# backend/services/api/routers/llm.py
"""
LLM API Router
LLM 기능을 위한 FastAPI 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging

# 임시: ChromaDB에서 PgVector 마이그레이션 중 - import 주석 처리
# from backend.services.llm.inha.langchain.chains.housing_chain import recommend_housing
# from backend.services.llm.inha.langchain.chains.housing_agent import housing_assistant
from typing import Literal

# ModelType 정의
ModelType = Literal["ollama", "openai", "groq"]

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

# RAG Chain은 housing_chain.py에서 직접 import하여 사용


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    질문에 답변하기 (RAG Chain 사용)
    
    **사용 예시:**
```json
    {
        "question": "강남역 근처 청년주택 알려줘",
        "model_type": "ollama",
        "with_memory": false
    }
```
    """
    try:
        # 임시: ChromaDB에서 PgVector 마이그레이션 중 - 기능 임시 비활성화
        answer = f"죄송합니다. 현재 시스템을 업데이트 중입니다. 잠시 후 다시 시도해주세요. (질문: {request.question})"
        
        # 소스 정보는 RAG Chain에서 직접 제공하지 않으므로 빈 리스트
        sources = []
        
        return QuestionResponse(
            answer=answer,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-agent", response_model=QuestionResponse)
async def ask_question_with_agent(request: QuestionRequest):
    """
    Housing Agent를 사용한 질문 답변 (inha 브랜치 기능)
    
    **사용 예시:**
```json
    {
        "question": "강남구 청년주택 모두 보여줘",
        "model_type": "ollama",
        "with_memory": false
    }
```
    """
    try:
        # 임시: ChromaDB에서 PgVector 마이그레이션 중 - 기능 임시 비활성화
        answer = f"죄송합니다. 현재 시스템을 업데이트 중입니다. 잠시 후 다시 시도해주세요. (질문: {request.question})"
        
        # 소스 정보는 Agent에서 직접 제공하지 않으므로 빈 리스트
        sources = []
        
        return QuestionResponse(
            answer=answer,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in ask_question_with_agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest):
    """
    주택 추천하기
    """
    try:
        # 추천 로직 구현
        recommendation_text = f"{request.location} 지역의 {request.budget} 예산으로 {request.preferences} 조건에 맞는 주택을 추천합니다."
        
        # TODO: 실제 추천 로직 구현
        candidates = []
        
        return RecommendationResponse(
            recommendation=recommendation_text,
            candidates=candidates
        )
        
    except Exception as e:
        logger.error(f"Error in get_recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    대화형 채팅
    
    **사용 예시:**
```json
    {
        "messages": [
            {"role": "user", "content": "안녕하세요"},
            {"role": "assistant", "content": "안녕하세요! 주택 검색을 도와드리겠습니다."},
            {"role": "user", "content": "강남구 청년주택 알려줘"}
        ],
        "model_type": "ollama"
    }
```
    """
    try:
        # 마지막 사용자 메시지 추출
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_user_message = user_messages[-1].content
        
        # 임시: ChromaDB에서 PgVector 마이그레이션 중 - 기능 임시 비활성화
        answer = f"죄송합니다. 현재 시스템을 업데이트 중입니다. 잠시 후 다시 시도해주세요. (질문: {last_user_message})"
        
        # 소스 정보는 Agent에서 직접 제공하지 않으므로 빈 리스트
        sources = []
        
        return ChatResponse(
            message=answer,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {"status": "healthy", "service": "LLM API"}


@router.post("/clear-memory")
async def clear_memory(model_type: ModelType = "ollama"):
    """대화 기록 초기화"""
    try:
        # TODO: 메모리 초기화 로직 구현
        return {"message": "Memory cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))