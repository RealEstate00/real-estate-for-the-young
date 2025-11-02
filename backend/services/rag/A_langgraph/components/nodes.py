"""
LangGraph 노드 함수들

각 Agent를 독립 노드로 분리하여 디버깅과 확장성을 향상시킵니다.
모든 노드는 RecommendationState를 입력받고 업데이트된 State를 반환합니다.
"""

import time
import logging
import re
from typing import Dict, Any, Literal

from .state import RecommendationState
# from ..agents.feedback_agent import FeedbackAgent  # 현재 미구현으로 주석처리
from ..agents.recommendation_agent import RecommendationAgent

logger = logging.getLogger(__name__)


def classify_query_node(state: RecommendationState) -> Dict[str, Any]:
    """
    질문 분류 노드 - LLM(Ollama Gemma 3 4b)으로 사용자 질문을 집/금융/그외로 분류
    
    Ollama의 gemma:3b 모델만 사용하여 분류합니다.

    Returns:
        query_type: housing / finance / general
        metadata: 분류 정보 포함
    """
    import time
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    start_time = time.time()
    try:
        user_request = state.get("user_request", "")

        system_prompt = (
            "너는 사용자의 질문이 어떤 카테고리인지 판별하는 시스템이야. "
            "아래 세 카테고리 중 하나로만 분류해서 한국어 또는 영어로 한 단어(housing, finance, general)만 반드시 출력해.\n"
            "1. housing: 주택(집, 매물, 원룸, 아파트, 임대, 전세, 월세 등)에 관한 질문\n"
            "2. finance: 금융/대출(대출, 금리, 청년, 전세대출, 주택담보대출 등)에 관한 질문\n"
            "3. general: 그 외의 모든 질문\n"
            "질문 예시:\n"
            "- '강남 전세 추천해줘' → housing\n"
            "- '청년 전세자금 대출 금리 알려줘' → finance\n"
            "- '오늘 날씨 어때?' → general\n"
            "다음 질문의 카테고리를 housing, finance, general 중 하나로만 답변해라.\n"
            "질문: '{question}'"
        ).format(question=user_request)

        llm = ChatOllama(
            model="gemma:3b",     # 반드시 Ollama gemma:3b만
            temperature=0
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"질문: {user_request}")
        ]

        response = llm.invoke(messages)
        llm_output = response.content.strip().lower()
        # 라벨 정제
        if "housing" in llm_output:
            query_type = "housing"
        elif "finance" in llm_output:
            query_type = "finance"
        elif "general" in llm_output:
            query_type = "general"
        else:
            query_type = "general"

        metadata = state.get("metadata", {})
        metadata["query_classification"] = {
            "query_type": query_type,
            "llm_output": llm_output,
            "original_query": user_request,
            "classification_time_ms": (time.time() - start_time) * 1000,
            "llm_model": "ollama/gemma:3b",
            "confidence": "llm"
        }

        logger.info(f"Ollama(gemma:3b) 기반 질문 분류: '{user_request}' -> {query_type} (LLM결과: {llm_output})")

        return {
            "query_type": query_type,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Ollama(gemma:3b) 기반 Query classification node 오류: {e}")

        metadata = state.get("metadata", {})
        metadata["query_classification"] = {
            "query_type": "general",
            "error": str(e),
            "classification_time_ms": (time.time() - start_time) * 1000,
            "llm_model": "ollama/gemma:3b",
            "confidence": "error"
        }

        return {
            "query_type": "general",
            "metadata": metadata
        }


def general_llm_node(state: RecommendationState) -> Dict[str, Any]:
    """
    일반 질문 LLM 답변 노드 - housing/finance와 관련없는 질문에 대한 직접 답변
    
    Ollama의 gemma:3b 모델을 사용하여 일반적인 질문에 답변합니다.
    
    Returns:
        final_answer: LLM의 답변
        metadata: 답변 생성 정보
    """
    import time
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    start_time = time.time()
    try:
        user_request = state.get("user_request", "")

        system_prompt = (
            "너는 도움이 되는 AI 어시스턴트야. "
            "사용자의 질문에 정확하고 친절하게 답변해줘. "
            "부동산이나 금융 관련 전문적인 질문이 아닌 일반적인 질문에 답변하고 있어. "
            "한국어로 자연스럽고 이해하기 쉽게 답변해줘."
        )

        llm = ChatOllama(
            model="gemma:3b",
            temperature=0.7  # 일반 답변은 조금 더 창의적으로
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request)
        ]

        response = llm.invoke(messages)
        llm_answer = response.content.strip()

        metadata = state.get("metadata", {})
        metadata["general_llm"] = {
            "model": "ollama/gemma:3b",
            "response_time_ms": (time.time() - start_time) * 1000,
            "original_query": user_request,
            "answer_length": len(llm_answer)
        }

        logger.info(f"일반 질문 LLM 답변 완료: '{user_request}' -> {len(llm_answer)}자 답변")

        return {
            "final_answer": llm_answer,
            "metadata": metadata,
            "iteration": state.get("iteration", 0)
        }

    except Exception as e:
        logger.error(f"일반 질문 LLM 노드 오류: {e}")
        
        metadata = state.get("metadata", {})
        metadata["general_llm"] = {
            "error": str(e),
            "response_time_ms": (time.time() - start_time) * 1000
        }

        return {
            "final_answer": "죄송합니다. 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.",
            "metadata": metadata,
            "iteration": state.get("iteration", 0)
        }


def housing_search_node(state: RecommendationState) -> Dict[str, Any]:
    """
    Housing Agent 노드 - 주택 매물 검색
    
    독립 노드로 분리하여 디버깅과 확장성 향상
    """
    start_time = time.time()
    
    try:
        # Agent 인스턴스는 그래프 빌드 시 주입 (의존성 주입)
        housing_agent = state.get("_agents", {}).get("housing")
        if not housing_agent:
            raise ValueError("HousingAgent가 state에 없습니다. 그래프 빌드 시 주입 필요")
        
        result = housing_agent.search(state["user_request"])
        
        # 메타데이터에 실행 정보 저장 (디버깅용)
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
        
        metadata["agent_execution"]["housing"] = {
            "execution_time_ms": (time.time() - start_time) * 1000,
            "candidates_count": len(result.get("candidates", [])),
            "success": "error" not in result
        }
        
        return {
            "candidates": result.get("candidates", []),
            "housing_result": result,  # 원본 결과도 저장 (디버깅용)
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Housing search node 실행 중 오류: {e}")
        
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
            
        metadata["agent_execution"]["housing"] = {
            "execution_time_ms": (time.time() - start_time) * 1000,
            "candidates_count": 0,
            "success": False,
            "error": str(e)
        }
        
        return {
            "candidates": [],
            "housing_result": {"error": str(e)},
            "metadata": metadata
        }


def loan_search_node(state: RecommendationState) -> Dict[str, Any]:
    """
    Loan Agent 노드 - 대출 관련 정보 검색
    
    독립 노드로 분리하여 디버깅과 확장성 향상
    """
    start_time = time.time()
    
    try:
        loan_agent = state.get("_agents", {}).get("loan")
        if not loan_agent:
            raise ValueError("LoanAgent가 state에 없습니다. 그래프 빌드 시 주입 필요")
        
        result = loan_agent.search_loan_info(state["user_request"])
        
        # 메타데이터에 실행 정보 저장 (디버깅용)
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
        
        metadata["agent_execution"]["loan"] = {
            "execution_time_ms": result.get("execution_time_ms", 0),
            "search_path": result.get("search_path", []),
            "results_count": len(result.get("results", [])),
            "query_variants": result.get("metadata", {}).get("query_variants", []),
            "success": "error" not in result
        }
        
        return {
            "loan_info": result.get("result", ""),
            "loan_results": result.get("results", []),
            "loan_metadata": result.get("metadata", {}),
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Loan search node 실행 중 오류: {e}")
        
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
            
        metadata["agent_execution"]["loan"] = {
            "execution_time_ms": (time.time() - start_time) * 1000,
            "search_path": [],
            "results_count": 0,
            "success": False,
            "error": str(e)
        }
        
        return {
            "loan_info": f"대출 정보 검색 중 오류 발생: {str(e)}",
            "loan_results": [],
            "loan_metadata": {},
            "metadata": metadata
        }


# RTMS Agent는 현재 미구현으로 주석처리
# def rtms_search_node(state: RecommendationState) -> Dict[str, Any]:
#     """
#     RTMS Agent 노드 - 실거래가 점수 계산
#     
#     독립 노드로 분리하여 디버깅과 확장성 향상
#     """
#     start_time = time.time()
#     
#     try:
#         rtms_agent = state.get("_agents", {}).get("rtms")
#         if not rtms_agent:
#             raise ValueError("RTMSAgent가 state에 없습니다. 그래프 빌드 시 주입 필요")
#         
#         # candidates가 있어야 점수 계산 가능
#         candidates = state.get("candidates", [])
#         if not candidates:
#             # candidates가 없으면 빈 점수 반환
#             logger.warning("RTMS 점수 계산: candidates가 없습니다")
#             return {"rtms_scores": {}}
#         
#         scores = rtms_agent.calculate_scores(candidates)
#         
#         # 메타데이터에 실행 정보 저장 (디버깅용)
#         metadata = state.get("metadata", {})
#         if "agent_execution" not in metadata:
#             metadata["agent_execution"] = {}
#         
#         metadata["agent_execution"]["rtms"] = {
#             "execution_time_ms": (time.time() - start_time) * 1000,
#             "scores_count": len(scores),
#             "candidates_processed": len(candidates),
#             "success": True
#         }
#         
#         return {
#             "rtms_scores": scores,
#             "metadata": metadata
#         }
#         
#     except Exception as e:
#         logger.error(f"RTMS search node 실행 중 오류: {e}")
#         
#         metadata = state.get("metadata", {})
#         if "agent_execution" not in metadata:
#             metadata["agent_execution"] = {}
#             
#         metadata["agent_execution"]["rtms"] = {
#             "execution_time_ms": (time.time() - start_time) * 1000,
#             "scores_count": 0,
#             "success": False,
#             "error": str(e)
#         }
#         
#         return {
#             "rtms_scores": {},
#             "metadata": metadata
#         }


def generate_recommendations_node(state: RecommendationState) -> Dict[str, Any]:
    """
    최종 추천 생성 노드
    
    여러 Agent의 결과를 종합하여 최종 추천 리스트 생성
    """
    start_time = time.time()
    
    try:
        recommendation_agent = RecommendationAgent()
        
        # 현재는 종합 점수 없이 후보를 선별 (RTMS 점수는 미구현으로 제외)
        recommendations = recommendation_agent.select_top_n(
            candidates=state.get("candidates", []),
            # rtms_scores=state.get("rtms_scores", {}),  # 현재 미구현
            loan_info=state.get("loan_info", ""),
            top_n=10
        )
        
        # 추천 요약 생성
        summary = recommendation_agent.generate_summary(recommendations)
        
        # 메타데이터 업데이트
        metadata = state.get("metadata", {})
        metadata["recommendation_count"] = len(recommendations)
        metadata["recommendation_summary"] = summary
        metadata["generation_time_ms"] = (time.time() - start_time) * 1000
        
        # 반복 횟수 증가
        iteration = state.get("iteration", 0) + 1
        
        return {
            "recommendations": recommendations,
            "metadata": metadata,
            "iteration": iteration
        }
        
    except Exception as e:
        logger.error(f"Recommendation generation node 실행 중 오류: {e}")
        
        metadata = state.get("metadata", {})
        metadata["recommendation_count"] = 0
        metadata["generation_error"] = str(e)
        metadata["generation_time_ms"] = (time.time() - start_time) * 1000
        
        return {
            "recommendations": [],
            "metadata": metadata,
            "iteration": state.get("iteration", 0)
        }


# 피드백 에이전트는 현재 미구현으로 주석처리
# def process_feedback_node(state: RecommendationState) -> Dict[str, Any]:
#     """
#     피드백 처리 노드
#     
#     사용자 피드백을 분석하고 재추천 필요성 판단
#     """
#     start_time = time.time()
#     
#     try:
#         user_feedback = state.get("user_feedback")
#         if not user_feedback:
#             # 피드백 없으면 스킵
#             logger.info("피드백이 없어 피드백 처리를 스킵합니다")
#             return {}
#         
#         feedback_agent = FeedbackAgent()
#         
#         # 피드백 분석
#         feedback_analysis = feedback_agent.analyze(
#             feedback=user_feedback,
#             previous_recommendations=state.get("recommendations", []),
#             conversation_history=state.get("conversation_history", [])
#         )
#         
#         # 메타데이터 업데이트
#         metadata = state.get("metadata", {})
#         metadata["feedback_weights"] = feedback_analysis.get("adjusted_weights", {})
#         metadata["feedback_analysis"] = feedback_analysis
#         metadata["feedback_processing_time_ms"] = (time.time() - start_time) * 1000
#         
#         # 재추천 필요 여부에 따라 iteration 증가
#         if feedback_analysis.get("needs_rerun", False):
#             iteration = state.get("iteration", 0) + 1
#         else:
#             iteration = state.get("iteration", 0)
#         
#         return {
#             "metadata": metadata,
#             "iteration": iteration
#         }
#         
#     except Exception as e:
#         logger.error(f"Feedback processing node 실행 중 오류: {e}")
#         
#         metadata = state.get("metadata", {})
#         metadata["feedback_error"] = str(e)
#         metadata["feedback_processing_time_ms"] = (time.time() - start_time) * 1000
#         
#         return {
#             "metadata": metadata
#         }


# 나중에 확장 예정:
# def infra_search_node(state: RecommendationState) -> Dict[str, Any]:
#     """Infra Agent 노드 - 인프라 점수 계산 (PostGIS)"""
#     infra_agent = state.get("_agents", {}).get("infra")
#     candidates = state.get("candidates", [])
#     scores = infra_agent.calculate_scores(candidates)
#     return {"infra_scores": scores}

# def calculate_scores_node(state: RecommendationState) -> Dict[str, Any]:
#     """종합 점수 계산 노드"""
#     scoring_agent = ScoringAgent()
#     final_scores = scoring_agent.calculate(
#         candidates=state["candidates"],
#         infra_scores=state.get("infra_scores", {}),
#         rtms_scores=state.get("rtms_scores", {})
#     )
#     return {"final_scores": final_scores}
