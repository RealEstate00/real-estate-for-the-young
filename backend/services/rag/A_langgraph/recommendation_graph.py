"""
Multi-Agent 추천 그래프

LangGraph를 사용하여 여러 Agent들을 조율하는 추천 시스템의 메인 그래프입니다.
각 Agent를 독립 노드로 분리하여 병렬 실행과 디버깅을 지원합니다.
"""

from typing import Dict, List, Optional, Any
import logging

from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph

from .components.state import RecommendationState, create_initial_state
from .components.nodes import (
    classify_query_node,
    general_llm_node,
    housing_search_node,
    loan_search_node,
    # rtms_search_node,  # 현재 미구현으로 주석처리
    generate_recommendations_node,
    # process_feedback_node  # 현재 미구현으로 주석처리
)

logger = logging.getLogger(__name__)


def build_recommendation_graph(
    housing_agent=None,
    loan_agent=None,
    rtms_agent=None
) -> CompiledGraph:
    """
    Multi-Agent 추천 그래프 빌드
    
    Args:
        housing_agent: HousingAgent 인스턴스
        loan_agent: LoanAgent 인스턴스
        rtms_agent: RTMSAgent 인스턴스
    
    Returns:
        컴파일된 LangGraph
    
    설계 원칙:
    - 각 Agent를 독립 노드로 분리
    - Agent 인스턴스를 state에 주입하여 노드에서 사용
    - 병렬 실행 가능하도록 설계
    """
    
    workflow = StateGraph(RecommendationState)
    
    # 각 노드를 추가 (질문 분류 노드가 시작점)
    workflow.add_node("classify", classify_query_node)
    workflow.add_node("general_llm", general_llm_node)  # 일반 질문 LLM 답변
    workflow.add_node("housing_search", housing_search_node)
    workflow.add_node("loan_search", loan_search_node)
    # workflow.add_node("rtms_search", rtms_search_node)  # 현재 미구현으로 주석처리
    workflow.add_node("recommend", generate_recommendations_node)
    # workflow.add_node("feedback", process_feedback_node)  # 현재 미구현으로 주석처리
    
    # 진입점: 질문 분류부터 시작
    workflow.set_entry_point("classify")
    
    # 조건부 라우팅: 분류 결과에 따라 적절한 노드로 라우팅
    def route_after_classification(state: RecommendationState) -> str:
        """분류 결과에 따라 다음 노드 결정"""
        query_type = state.get("query_type", "general")
        
        if query_type == "housing":
            return "housing_search"  # housing 전용 검색
        elif query_type == "finance":
            return "loan_search"     # finance 전용 검색
        else:
            # general 질문은 LLM이 직접 답변
            return "general_llm"
    
    workflow.add_conditional_edges(
        "classify",
        route_after_classification,
        {
            "housing_search": "housing_search",
            "loan_search": "loan_search", 
            "general_llm": "general_llm"
        }
    )
    
    # housing_search와 loan_search 완료 후 추천 생성
    workflow.add_edge("housing_search", "recommend")
    workflow.add_edge("loan_search", "recommend")
    
    # general_llm은 바로 종료 (추천 시스템 거치지 않음)
    workflow.add_edge("general_llm", END)
    
    # 추천 생성 후 종료 (피드백 노드는 현재 미구현)
    workflow.add_edge("recommend", END)
    
    # RTMS 관련 라우팅은 현재 미구현으로 주석처리
    # def route_after_search(state: RecommendationState) -> str:
    #     """모든 검색 노드 완료 확인"""
    #     # 기본적으로 loan_search와 rtms_search가 모두 완료되면 recommend로 이동
    #     has_loan_info = "loan_info" in state
    #     has_rtms_scores = "rtms_scores" in state
    #     
    #     if has_loan_info and has_rtms_scores:
    #         return "recommend"
    #     return "recommend"  # 일부 실패해도 추천 진행
    # 
    # # loan_search 완료 후 조건부 라우팅
    # workflow.add_conditional_edges(
    #     "loan_search",
    #     route_after_search,
    #     {
    #         "recommend": "recommend"
    #     }
    # )
    # 
    # # rtms_search 완료 후 조건부 라우팅
    # workflow.add_conditional_edges(
    #     "rtms_search", 
    #     route_after_search,
    #     {
    #         "recommend": "recommend"
    #     }
    # )
    
    # 나중에 확장 예정:
    # workflow.add_node("infra_search", infra_search_node)
    # workflow.add_node("score", calculate_scores_node)
    # workflow.add_edge("housing_search", "infra_search")
    # workflow.add_edge("infra_search", "score")
    # workflow.add_edge("score", "recommend")
    
    # 피드백 루프는 현재 미구현으로 주석처리
    # def should_rerun(state: RecommendationState) -> str:
    #     """재추천 필요성 판단"""
    #     if state.get("user_feedback"):
    #         feedback_analysis = state.get("metadata", {}).get("feedback_analysis", {})
    #         if feedback_analysis.get("needs_rerun", False):
    #             logger.info("피드백에 따라 재추천을 시작합니다")
    #             return "housing_search"  # 다시 검색부터
    #     return "end"
    # 
    # workflow.add_conditional_edges(
    #     "feedback",
    #     should_rerun,
    #     {
    #         "housing_search": "housing_search",  # 재추천
    #         "end": END                            # 종료
    #     }
    # )
    
    # 그래프 컴파일
    compiled_graph = workflow.compile()
    
    # Agent 인스턴스를 그래프에 주입하는 래퍼 함수
    def inject_agents(state_input: Dict) -> Dict:
        """Agent 인스턴스를 state에 주입"""
        if "_agents" not in state_input:
            state_input["_agents"] = {}
            
        if housing_agent:
            state_input["_agents"]["housing"] = housing_agent
        if loan_agent:
            state_input["_agents"]["loan"] = loan_agent
        # if rtms_agent:  # 현재 미구현으로 주석처리
        #     state_input["_agents"]["rtms"] = rtms_agent
            
        return state_input
    
    # 원본 invoke를 래핑하여 Agent 주입
    original_invoke = compiled_graph.invoke
    
    def wrapped_invoke(state_input: Dict) -> Dict:
        """Agent 인스턴스 주입 후 그래프 실행"""
        try:
            state_with_agents = inject_agents(state_input)
            return original_invoke(state_with_agents)
        except Exception as e:
            logger.error(f"그래프 실행 중 오류 발생: {e}")
            # 오류 발생 시 기본 응답 반환
            return {
                **state_input,
                "recommendations": [],
                "metadata": {
                    "error": str(e),
                    "agent_execution": {}
                }
            }
    
    compiled_graph.invoke = wrapped_invoke
    
    return compiled_graph


# 싱글톤 그래프 (선택사항)
_compiled_graph = None


def get_recommendation_graph(
    housing_agent=None,
    loan_agent=None, 
    rtms_agent=None
) -> CompiledGraph:
    """
    컴파일된 그래프 반환 (싱글톤 패턴)
    
    Args:
        housing_agent: HousingAgent 인스턴스
        loan_agent: LoanAgent 인스턴스
        rtms_agent: RTMSAgent 인스턴스
    
    Returns:
        컴파일된 그래프
    """
    global _compiled_graph
    
    # Agent가 제공되면 새로 빌드
    if housing_agent or loan_agent or rtms_agent:
        _compiled_graph = build_recommendation_graph(
            housing_agent=housing_agent,
            loan_agent=loan_agent,
            rtms_agent=rtms_agent
        )
    elif _compiled_graph is None:
        # Agent 없이 호출되면 기본 그래프 생성 (테스트용)
        _compiled_graph = build_recommendation_graph()
    
    return _compiled_graph


def recommend_housing(
    user_request: str,
    conversation_history: List[Dict] = None,
    user_feedback: Dict = None,
    housing_agent=None,
    loan_agent=None,
    rtms_agent=None
) -> Dict:
    """
    주거 매물 추천 (메인 함수)
    
    Args:
        user_request: 사용자 요청 (예: "강남구 원룸 추천해줘")
        conversation_history: 대화 히스토리
        user_feedback: 사용자 피드백 
            {
                "type": "like/dislike/text/action",
                "target_ids": [매물 ID 리스트],
                "text": "텍스트 피드백"
            }
        housing_agent: HousingAgent 인스턴스
        loan_agent: LoanAgent 인스턴스
        rtms_agent: RTMSAgent 인스턴스
    
    Returns:
        {
            "recommendations": List[Dict],  # 추천 매물 리스트
            "metadata": Dict,               # 디버깅 정보 포함
            "summary": Dict                 # 추천 요약
        }
    """
    try:
        # 그래프 빌드
        graph = build_recommendation_graph(
            housing_agent=housing_agent,
            loan_agent=loan_agent,
            rtms_agent=rtms_agent
        )
        
        # 초기 State 생성
        initial_state = create_initial_state(
            user_request=user_request,
            conversation_history=conversation_history,
            user_feedback=user_feedback
        )
        
        # 그래프 실행
        result = graph.invoke(initial_state)
        
        # 결과 포맷팅
        recommendations = result.get("recommendations", [])
        metadata = result.get("metadata", {})
        
        # 추천 요약 생성
        summary = metadata.get("recommendation_summary", {
            "total_count": len(recommendations),
            "summary": f"{len(recommendations)}개 매물을 추천드립니다."
        })
        
        return {
            "recommendations": recommendations,
            "metadata": metadata,
            "summary": summary,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"추천 시스템 실행 중 오류 발생: {e}")
        
        return {
            "recommendations": [],
            "metadata": {
                "error": str(e),
                "agent_execution": {}
            },
            "summary": {
                "total_count": 0,
                "summary": f"추천 중 오류가 발생했습니다: {str(e)}"
            },
            "success": False
        }


# 테스트용 함수
def test_graph_structure() -> Dict:
    """
    그래프 구조 테스트
    
    Returns:
        그래프 구조 정보
    """
    try:
        graph = build_recommendation_graph()
        
        # 그래프 노드와 엣지 정보 추출
        nodes = list(graph.nodes.keys()) if hasattr(graph, 'nodes') else []
        
        return {
            "nodes": nodes,
            "structure": "classify -> [housing_search -> recommend | loan_search -> recommend | general_llm] -> END",
            "success": True
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
