# backend/services/api/routers/llm.py
"""
RAG API Router
RAG 시스템을 사용한 LLM 기능을 위한 FastAPI 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging
import os

from backend.services.rag.rag_system import RAGSystem
from backend.services.rag.models.config import EmbeddingModelType
from backend.services.rag.generation.generator import OllamaGenerator, GenerationConfig
from backend.services.rag.retrieval.reranker import KeywordReranker
from backend.services.rag.augmentation.formatters import EnhancedPromptFormatter

from typing import Literal

# ModelType 정의
ModelType = Literal["ollama", "openai", "groq"]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM"])

# RAG 시스템 인스턴스 (싱글톤 패턴)
_rag_system: Optional[RAGSystem] = None


def get_db_config() -> dict:
    """데이터베이스 설정 가져오기"""
    return {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5432'),
        'database': os.getenv('PG_DB', 'rey'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'post1234')
    }


def get_model_type_from_env() -> EmbeddingModelType:
    """환경 변수에서 임베딩 모델 타입 가져오기"""
    model_name = os.getenv('RAG_EMBEDDING_MODEL', 'E5_SMALL').upper()
    mapping = {
        "E5_SMALL": EmbeddingModelType.MULTILINGUAL_E5_SMALL,
        "E5_BASE": EmbeddingModelType.MULTILINGUAL_E5_BASE,
        "E5_LARGE": EmbeddingModelType.MULTILINGUAL_E5_LARGE,
        "KAKAO": EmbeddingModelType.KAKAOBANK_DEBERTA
    }
    return mapping.get(model_name, EmbeddingModelType.MULTILINGUAL_E5_SMALL)


def get_rag_system() -> RAGSystem:
    """RAG 시스템 인스턴스 가져오기 (싱글톤, 환경 변수 변경 시 재생성)"""
    global _rag_system
    
    # 환경 변수에서 현재 모델 타입 가져오기
    current_model_type = get_model_type_from_env()
    
    # 인스턴스가 없거나 모델 타입이 변경된 경우 재생성
    if _rag_system is None or _rag_system.retriever.model_type != current_model_type:
        # 기존 인스턴스가 있으면 로그 출력
        if _rag_system is not None:
            logger.info(f"Model type changed, recreating RAG system: {_rag_system.retriever.model_type.value} -> {current_model_type.value}")
        
        # DB 설정 가져오기
        db_config = get_db_config()
        
        # LLM Generator 초기화
        # Ollama URL 환경 변수에서 읽기 (도커에서는 host.docker.internal 사용)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm_generator = OllamaGenerator(
            base_url=ollama_url,
            default_model="gemma3:4b"
        )
        
        # RAG 시스템 초기화
        _rag_system = RAGSystem(
            model_type=current_model_type,
            db_config=db_config,
            reranker=KeywordReranker(
                use_llm_extraction=False  # Regex 사용 (속도 향상: LLM 호출 제거)
            ),
            formatter=EnhancedPromptFormatter(),
            llm_generator=llm_generator,
            enable_generation=True
        )
        logger.info(f"RAG System initialized with {current_model_type.value}")
    
    return _rag_system


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
# Dependency: RAG System Instance
# =============================================================================

# RAG 시스템은 get_rag_system() 함수를 통해 싱글톤으로 관리됩니다


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest, rag_system: RAGSystem = Depends(get_rag_system)):
    """
    질문에 답변하기 (RAG 시스템 사용)
    
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
        # RAG 시스템으로 전체 파이프라인 실행 (top_k=3으로 속도 개선)
        response = rag_system.generate_answer(
            query=request.question,
            top_k=3,  # 비교 자료 기준으로 3개 사용 (속도 개선)
            use_reranker=True,
            generation_config=GenerationConfig(
                model="gemma3:4b",
                temperature=0.7,
                max_tokens=2000,
                timeout=180  # 타임아웃 180초 (LLM 응답 대기 시간 증가)
            )
        )
        
        # 소스 정보 추출 (상위 1개만)
        sources = []
        if response.retrieved_documents and len(response.retrieved_documents) > 0:
            doc = response.retrieved_documents[0]  # 상위 1개만
            metadata = doc.get("metadata", {})
            # source 필드 우선 사용, 없으면 metadata에서 source_doc_title, 그래도 없으면 title 또는 content
            source_title = (
                doc.get("source") or 
                metadata.get("source") or 
                metadata.get("source_doc_title") or 
                doc.get("title") or 
                (doc.get("content", "")[:50] if doc.get("content") else "문서")
            )
            sources.append(SourceInfo(
                title=source_title or "문서",
                address=doc.get("address", ""),
                district=doc.get("district", "")
            ))
        
        return QuestionResponse(
            answer=response.generated_answer.answer if response.generated_answer else "",
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in ask_question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-agent", response_model=ChatResponse)
async def ask_question_with_agent(request: QuestionRequest, rag_system: RAGSystem = Depends(get_rag_system)):
    """
    RAG 시스템을 사용한 질문 답변 (리랭킹 포함)
    
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
        # 병목 현상 분석 (환경 변수로 활성화)
        import os
        enable_profiling = os.getenv("RAG_PROFILING", "false").lower() == "true"
        
        if enable_profiling:
            from backend.services.rag.profiler import RAGProfiler
            profiler = RAGProfiler(enable_detailed_logging=True)
            profile = profiler.profile_full_pipeline(
                rag_system=rag_system,
                query=request.question,
                top_k=3,
                use_reranker=True,
                generation_config=GenerationConfig(
                    model="gemma3:4b",
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=180
                )
            )
            profiler.print_profile(profile)
            # 프로파일링 후에도 정상 응답 반환
            response = rag_system.generate_answer(
                query=request.question,
                top_k=3,
                use_reranker=True,
                generation_config=GenerationConfig(
                    model="gemma3:4b",
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=180
                )
            )
        else:
            # RAG 시스템으로 전체 파이프라인 실행 (리랭킹 포함, top_k=3으로 속도 개선)
            try:
                response = rag_system.generate_answer(
                    query=request.question,
                    top_k=3,  # 비교 자료 기준으로 3개 사용 (속도 개선)
                    use_reranker=True,  # 리랭킹 사용 (이미 Regex로 최적화됨)
                    generation_config=GenerationConfig(
                        model="gemma3:4b",
                        temperature=0.7,
                        max_tokens=1500,  # 2000 → 1500으로 감소 (생성 시간 단축)
                        timeout=120  # 180 → 120초로 감소 (적절한 타임아웃)
                    )
                )
            except Exception as gen_error:
                logger.error(f"Generation error: {gen_error}", exc_info=True)
                # 타임아웃 또는 생성 오류 시 기본 메시지 반환
                if "시간 초과" in str(gen_error) or "timeout" in str(gen_error).lower():
                    answer_text = "죄송합니다. 답변 생성 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
                else:
                    answer_text = f"죄송합니다. 답변 생성 중 문제가 발생했습니다: {str(gen_error)}"
                # 기본 소스 정보라도 제공
                sources = []
                return ChatResponse(message=answer_text, sources=sources)
        
        # 생성된 답변이 없는 경우 에러 메시지
        if not response.generated_answer:
            logger.error("Generated answer is None. RAG pipeline may have failed.")
            answer_text = "죄송합니다. 답변 생성에 실패했습니다. 데이터베이스 연결을 확인해주세요."
        elif not response.generated_answer.answer or len(response.generated_answer.answer.strip()) == 0:
            logger.warning("Generated answer is empty. Check if Ollama is running and accessible.")
            answer_text = "죄송합니다. 답변이 생성되지 않았습니다. Ollama 서버가 실행 중인지 확인해주세요."
        else:
            answer_text = response.generated_answer.answer.strip()
        
        # 소스 정보 추출 (상위 1개만)
        sources = []
        if response.retrieved_documents and len(response.retrieved_documents) > 0:
            doc = response.retrieved_documents[0]  # 상위 1개만
            metadata = doc.get("metadata", {})
            # source 필드 우선 사용, 없으면 metadata에서 source_doc_title, 그래도 없으면 title 또는 content
            source_title = (
                doc.get("source") or 
                metadata.get("source") or 
                metadata.get("source_doc_title") or 
                doc.get("title") or 
                (doc.get("content", "")[:50] if doc.get("content") else "문서")
            )
            sources.append(SourceInfo(
                title=source_title or "문서",
                address=doc.get("address", ""),
                district=doc.get("district", "")
            ))
        
        return ChatResponse(
            message=answer_text,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in ask_question_with_agent: {e}", exc_info=True)
        # 에러 메시지를 더 상세하게 로깅
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 사용자에게 친절한 에러 메시지 반환
        error_message = "죄송합니다. 답변 생성 중 문제가 발생했습니다."
        if "database" in str(e).lower() or "postgres" in str(e).lower():
            error_message = "데이터베이스 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요."
        elif "timeout" in str(e).lower() or "시간 초과" in str(e):
            error_message = "답변 생성 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        elif "ollama" in str(e).lower():
            error_message = "Ollama 서버 연결에 문제가 있습니다. 서버가 실행 중인지 확인해주세요."
        
        return ChatResponse(
            message=error_message,
            sources=[]
        )


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
async def chat(request: ChatRequest, rag_system: RAGSystem = Depends(get_rag_system)):
    """
    대화형 채팅 (RAG 시스템 사용)
    
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
        
        # RAG 시스템으로 전체 파이프라인 실행 (top_k=3으로 속도 개선)
        response = rag_system.generate_answer(
            query=last_user_message,
            top_k=3,  # 비교 자료 기준으로 3개 사용 (속도 개선)
            use_reranker=True,
            generation_config=GenerationConfig(
                model="gemma3:4b",
                temperature=0.7,
                max_tokens=2000,
                timeout=180  # 타임아웃 180초 (LLM 응답 대기 시간 증가)
            )
        )
        
        # 소스 정보 추출
        sources = []
        for doc in response.retrieved_documents[:5]:  # 상위 5개만
            metadata = doc.get("metadata", {})
            # source 필드 우선 사용, 없으면 metadata에서 source_doc_title, 그래도 없으면 title 또는 content
            source_title = (
                doc.get("source") or 
                metadata.get("source") or 
                metadata.get("source_doc_title") or 
                doc.get("title") or 
                (doc.get("content", "")[:50] if doc.get("content") else "문서")
            )
            sources.append(SourceInfo(
                title=source_title or "문서",
                address=doc.get("address", ""),
                district=doc.get("district", "")
            ))
        
        return ChatResponse(
            message=response.generated_answer.answer if response.generated_answer else "",
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
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