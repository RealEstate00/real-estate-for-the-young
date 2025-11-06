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
from backend.services.api.utils.summarizer import summarize_title, summarize_conversation_batch

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


# summarize_conversation_batch 함수는 이제 backend/services/api/utils/summarizer.py에서
# mT5-base를 사용하여 구현됩니다. (Ollama 대신 구글 모델 사용)
# import는 상단에서 처리: from backend.services.api.utils.summarizer import summarize_conversation_batch


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
    title: Optional[str] = Field(default=None, description="대화 제목 (요약)")


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
    대화형 채팅 (RAG 시스템 사용, 대화 히스토리 기억 및 요약)
    
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
        
        # 대화 히스토리 처리: 10개마다 요약하고, 요약된 내용 + 최근 메시지 조합
        total_messages = len(request.messages)
        recent_message_count = 10  # 최근 메시지 개수
        summary_interval = 10  # 10개마다 요약
        
        # 메시지를 딕셔너리 형태로 변환
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # 요약이 필요한 구간 계산
        conversation_summaries = []  # 요약된 대화들
        recent_messages_for_context = []  # 최근 메시지들
        
        if total_messages > summary_interval:
            # 요약이 필요한 구간들 처리 (10개 이상인 경우)
            summary_start = 0
            while summary_start < total_messages - recent_message_count:
                summary_end = min(summary_start + summary_interval, total_messages - recent_message_count)
                batch_messages = messages_dict[summary_start:summary_end]
                
                if batch_messages:
                    summary = summarize_conversation_batch(batch_messages)
                    if summary:
                        conversation_summaries.append(summary)
                
                summary_start = summary_end
            
            # 최근 메시지들 (요약되지 않은 부분)
            recent_messages_for_context = messages_dict[-(recent_message_count + 1):-1]  # 마지막 질문 제외
        else:
            # 10개 미만일 때는 요약 없이 전체 대화 히스토리 사용 (마지막 질문 제외)
            recent_messages_for_context = messages_dict[:-1] if len(messages_dict) > 1 else []
        
        # 대화 히스토리 포맷팅
        history_parts = []
        
        # 요약된 내용 추가 (10개 이상일 때만)
        if conversation_summaries:
            history_parts.append("## 이전 대화 요약")
            for i, summary in enumerate(conversation_summaries, 1):
                history_parts.append(f"{i}. {summary}")
        
        # 최근 메시지 추가 (10개 미만일 때는 전체 히스토리, 10개 이상일 때는 최근 메시지)
        if recent_messages_for_context:
            if conversation_summaries:
                history_parts.append("\n## 최근 대화")
            elif total_messages <= summary_interval:
                # 10개 미만일 때는 "이전 대화 내용"으로 표시
                history_parts.append("## 이전 대화 내용")
            
            for msg in recent_messages_for_context:
                if msg["role"] == "user":
                    history_parts.append(f"사용자: {msg['content']}")
                elif msg["role"] == "assistant":
                    history_parts.append(f"어시스턴트: {msg['content']}")
        
        history_text = "\n".join(history_parts) if history_parts else ""
        
        # 디버깅: 히스토리 내용 로깅
        logger.info(f"Total messages: {total_messages}, History included: {len(recent_messages_for_context)} messages")
        
        # RAG 시스템으로 검색 및 컨텍스트 생성
        rag_response = rag_system.retrieve_and_augment(
            query=last_user_message,
            top_k=3,
            use_reranker=True
        )
        
        # 대화 히스토리를 포함한 프롬프트 생성
        context_text = rag_response.augmented_context.context_text if rag_response.augmented_context else ""
        
        # Ollama로 대화 히스토리 포함 답변 생성
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        if history_text:
            # 대화 히스토리가 있는 경우 - 이전 대화를 우선 참고하도록 구조 변경
            prompt = f"""당신은 청년 주거 정책 전문 상담사입니다. **반드시 이전 대화 내용을 먼저 확인하고**, 이를 바탕으로 참고 문서에서 관련 정보를 찾아 답변하세요.

## ⚠️ 매우 중요: 답변 전 필수 절차 (순서대로 반드시 수행하세요!)

### 1단계: 현재 질문 이해
- 현재 질문: "{last_user_message}"를 먼저 읽으세요

### 2단계: 이전 대화 내용 확인 (가장 중요! 정확성 필수!)
**이전 대화 내용을 반드시 읽고 다음을 확인하세요:**
- 사용자의 이름: (이전 대화에서 **실제로 언급되었을 때만** 찾아서 기억. 없으면 "정보 없음"으로 기록)
- 사용자의 거주지: (이전 대화에서 **실제로 언급되었을 때만** 찾아서 기억. 없으면 "정보 없음"으로 기록)
- 이전 질문 주제: (이전 대화에서 무엇을 물어봤는지)
- 이전 답변 내용: (이전에 무엇을 답변했는지)

**⚠️ 매우 중요**: 이전 대화에서 정보를 찾을 수 없으면 **절대로** 추측하거나 만들어내지 마세요. "정보 없음"으로 기록하고 답변에 반영하세요.

### 3단계: 현재 질문과 이전 대화 연결 (정확성 필수!)
- "얼마까지 지원해주는거야?" → 이전 대화에서 설명한 지원금의 구체 금액을 찾아 답변
- "내가 어디 사는지 기억해?" → **이전 대화에 실제로 거주지가 언급되어 있을 때만** "네, [거주지]에 거주하시는 것으로 기억하고 있습니다" 형태로 답변. **없으면** "이전 대화에서 거주지 정보를 확인할 수 없습니다"라고 답변
- "내 이름 기억하지?" → **이전 대화에 실제로 이름이 언급되어 있을 때만** 답변. **없으면** "이전 대화에서 이름 정보를 확인할 수 없습니다"라고 답변
- "다시 알려줘" → 이전 답변 내용을 재활용
- **⚠️ 절대 하지 말 것**: 예시나 다른 정보를 실제 정보처럼 사용하지 마세요. 반드시 이전 대화에서 실제로 언급된 정보만 사용하세요

### 4단계: 참고 문서 활용
- 참고 문서는 이전 대화 맥락에 맞는 정보만 선택적으로 사용
- 이전 대화와 관련 없는 정보는 무시하세요

## 현재 질문
사용자: {last_user_message}

## ⚠️ 매우 중요: 이전 대화 내용을 먼저 읽으세요!
다음 내용에서 **반드시** 다음 정보를 추출하고 기억하세요:

{history_text}

**위 이전 대화 내용에서 찾아야 할 정보:**
1. 사용자가 언급한 **이름** 
2. 사용자가 언급한 **거주지** 
3. 이전 질문 주제 (예: "월세 지원금", "전세 대출" 등)
4. 이전 답변 내용

**특히 주의사항:**
- "내가 어디 사는지 기억해?" 같은 질문에는 반드시 이전 대화에서 거주지를 찾아서 답변하세요
- **중요**: 이전 대화에서 실제로 거주지가 언급되었을 때만 거주지를 답변하세요. 이전 대화에 거주지 정보가 없으면 "이전 대화에서 거주지 정보를 확인할 수 없습니다"라고 답변하세요
- **중요**: 이전 대화에서 실제로 이름이 언급되었을 때만 이름을 답변하세요. 이전 대화에 이름 정보가 없으면 "이전 대화에서 이름을 확인할 수 없습니다"라고 답변하세요
- 이전 대화를 읽지 않고 "문서에 없는 정보"라고 답변하지 마세요
- **절대로** 이전 대화에 없는 정보를 임의로 만들어내지 마세요. 반드시 이전 대화 내용에서만 정보를 추출하세요

## 참고 문서 (이전 대화 맥락에 맞게 참고, 이전 대화 내용을 우선하세요)
{context_text}

## 답변 작성 규칙 (우선순위 순)
1. **이전 대화 맥락 우선 (최우선, 정확성 필수)**: 
   - 이전 대화에서 언급된 모든 정보(이름, 거주지, 질문 주제, 답변 내용)를 반드시 먼저 확인하고 활용하세요
   - **⚠️ 매우 중요**: 이전 대화 내용을 정확히 읽고, 실제로 언급된 정보만 사용하세요
   - "내가 어디 사는지 기억해?" → 이전 대화에서 사용자가 **실제로 거주지를 언급했을 때만** "네, [거주지]에 거주하시는 것으로 기억하고 있습니다"라고 답변. **거주지가 언급되지 않았으면** "죄송하지만 이전 대화에서 거주지 정보를 확인할 수 없습니다"라고 답변하세요
   - "내 이름 기억하지?" → 이전 대화에서 **실제로 이름이 언급되었을 때만** 답변. **이름이 언급되지 않았으면** "죄송하지만 이전 대화에서 이름 정보를 확인할 수 없습니다"라고 답변하세요
   - "얼마까지 지원해주는거야?" → 이전 대화에서 설명한 지원금/정책에 대한 구체적인 금액을 찾아서 답변
   - **절대로** 이전 대화에 없는 정보를 추측하거나 임의로 만들어내지 마세요
   - **절대로** 예시나 다른 대화의 정보를 사용하지 마세요

2. **연속성 유지 (중요: 정확성 우선)**: 
   - 이전 대화의 주제와 현재 질문의 연결점을 정확히 파악하세요
   - 이전에 제공한 정보는 그대로 활용하고, 추가 정보만 보완하세요
   - **절대로** 이전 대화에 없는 정보(이름, 거주지 등)를 추측하거나 임의로 만들어내지 마세요
   - 이전 대화에서 정보를 찾을 수 없으면 "이전 대화에서 [정보]를 확인할 수 없습니다"라고 명확히 말하세요

3. **정확성**: 
   - 참고 문서의 내용을 바탕으로 답변하되, 이전 대화 맥락에 맞게 선택하세요
   - 이전 대화와 관련 없는 정보는 제공하지 마세요

4. **구체성**: 
   - 이전 대화에서 언급된 내용에 대한 구체적인 금액이나 수치를 명시하세요

5. **일관성**: 
   - 이전 대화에서 언급된 이름, 거주지, 개인 정보를 일관되게 사용하세요

6. **친절성**: 한국어로 자연스럽고 친절하게 답변하세요

답변:"""
        else:
            # 대화 히스토리가 없는 경우 (첫 질문)
            prompt = f"""당신은 청년 주거 정책 전문 상담사입니다. 주어진 문서를 바탕으로 사용자의 질문에 정확하고 친절하게 답변해주세요.

## 참고 문서
{context_text}

## 사용자 질문
{last_user_message}

## 답변 작성 규칙
1. **정확성**: 참고 문서의 내용만을 기반으로 답변하고, 문서에 없는 내용은 추측하지 마세요
2. **구조화**: 명확한 섹션으로 나누어 체계적으로 작성하세요 (예: 신청 자격, 금리, 한도, 신청 방법 등)
3. **완전성**: 표나 리스트를 작성할 때 중간에 끊기지 않도록 완전하게 작성하세요
4. **구체성**: 조건, 금액, 금리, 절차 등 구체적인 수치와 정보를 명시하세요
5. **명확성**: 마크다운 형식을 사용하여 읽기 쉽게 작성하세요 (**, -, 1. 등)
6. **관련성**: 질문과 직접 관련된 정보만 제공하고, 불필요한 내용은 제외하세요
7. **친절성**: 한국어로 자연스럽고 친절하게 답변하세요

답변:"""
        
        import requests
        payload = {
            "model": "gemma3:4b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2000
            }
        }
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        
        result = response.json()
        answer = result.get("response", "").strip()
        
        # mT5-base를 사용하여 제목 요약 생성 (첫 번째 AI 답변인 경우에만)
        title = None
        # 첫 번째 사용자 질문인 경우 (len(user_messages) == 1)
        # 이 시점에서 AI 답변(answer)이 이미 생성되어 있으므로, 이를 기반으로 제목 생성
        if len(user_messages) == 1:  # 첫 번째 사용자 질문 = 첫 번째 AI 답변 생성 시점
            logger.info(f"첫 번째 사용자 질문 감지, 첫 번째 AI 답변 기반 제목 생성 시작. 응답 길이: {len(answer)}자")
            try:
                # 첫 번째 AI 답변을 mT5-base로 요약하여 25자 내외 제목 생성
                logger.info("mT5-base 요약 함수 호출 중...")
                title = summarize_title(answer, max_length=25)
                if title:
                    logger.info(f"✅ mT5-base 요약 성공 (첫 번째 AI 답변 기반): '{title}' ({len(title)}자)")
                else:
                    logger.warning("⚠️ mT5-base 요약 결과가 비어있습니다.")
            except Exception as e:
                logger.error(f"❌ mT5-base 요약 중 오류 발생: {e}", exc_info=True)
                # 실패 시 fallback: 첫 25자 사용
                title = answer[:25] if answer else None
                logger.info(f"Fallback 제목 사용: '{title}'")
        else:
            logger.debug(f"첫 번째 질문이 아님 (사용자 메시지 수: {len(user_messages)}), 제목 생성 스킵")
        
        # 소스 정보 추출
        sources = []
        for doc in rag_response.retrieved_documents[:5]:  # 상위 5개만
            metadata = doc.get("metadata", {})
            # source 필드 우선 사용, 없으면 metadata에서 source_doc_title, 그래도 없으면 title 또는 content
            source_title = (
                doc.get("source") or 
                metadata.get("source") or 
                metadata.get("source_doc_title") or 
                doc.get("title") or 
                (doc.get("content", "")[:50] if doc.get("content") else "문서")
            )
            district = doc.get("district", "") or metadata.get("district", "")
            address = doc.get("address", "") or metadata.get("address", "")
            
            # 빈 필드가 모두 없는 경우에만 제외
            if source_title or district or address:
                sources.append(SourceInfo(
                    title=source_title or "문서",
                    address=address,
                    district=district
                ))
        
        # 제목 생성 결과 로깅
        if title:
            logger.info(f"📌 최종 제목 반환: '{title}' ({len(title)}자)")
        else:
            logger.warning("⚠️ 제목이 None입니다. 프론트엔드에서 fallback 사용될 것입니다.")
        
        return ChatResponse(
            message=answer,
            sources=sources,
            title=title
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