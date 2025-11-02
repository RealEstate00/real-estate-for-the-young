"""
RecommendationState 정의

LangGraph에서 사용할 State 정의
각 노드 간에 공유되는 데이터 구조
"""

from typing import TypedDict, Optional, Dict, Any, List


class RecommendationState(TypedDict):
    """추천 시스템 State"""
    
    # ========================================
    # 사용자 입력
    # ========================================
    user_request: str                    # 사용자 요청
    query_type: str                      # 질문 분류 ("housing", "finance", "general")
    conversation_history: List[Dict]     # 대화 히스토리
    user_feedback: Optional[Dict]        # 사용자 피드백
    
    # ========================================
    # Agent 인스턴스 (그래프 빌드 시 주입)
    # ========================================
    _agents: Dict[str, Any]              # {"housing": HousingAgent, "loan": LoanAgent, ...}
    
    # ========================================
    # 추천 프로세스 (각 노드에서 업데이트)
    # ========================================
    candidates: List[Dict]               # 초기 후보들 (housing_search_node에서 설정)
    housing_result: Optional[Dict]       # Housing Agent 원본 결과 (디버깅용)
    loan_info: str                       # 대출 관련 정보 문자열 (loan_search_node에서 설정)
    loan_results: List[Dict]             # 대출 검색 원본 결과 (디버깅용)
    loan_metadata: Dict[str, Any]        # Loan Agent 메타데이터 (디버깅용)
    # rtms_scores: Dict[str, float]        # 실거래가 점수 (rtms_search_node에서 설정) - 현재 미구현
    recommendations: List[Dict]          # 최종 추천 리스트
    
    # ========================================
    # 나중에 확장 예정
    # ========================================
    # infra_scores: Dict[str, float]     # 인프라 점수 (PostGIS)
    # loan_eligibility: Dict[str, bool]  # 대출 가능 여부
    # final_scores: Dict[str, float]     # 종합 점수
    
    # ========================================
    # 메타데이터 (디버깅 및 추적용)
    # ========================================
    metadata: Dict[str, Any]             # 추적 정보
    # metadata 구조:
    # {
    #   "agent_execution": {
    #     "housing": {"execution_time_ms": 1200, "candidates_count": 50},
    #     "loan": {"execution_time_ms": 2500, "search_path": ["basic", "advanced"], ...},
    #     "rtms": {"execution_time_ms": 800, "scores_count": 50}
    #   },
    #   "feedback_weights": {...},
    #   "feedback_analysis": {...}
    # }
    iteration: int                       # 추천 반복 횟수


def create_initial_state(
    user_request: str,
    conversation_history: List[Dict] = None,
    user_feedback: Dict = None
) -> RecommendationState:
    """
    초기 State 생성
    
    Args:
        user_request: 사용자 요청
        conversation_history: 대화 히스토리
        user_feedback: 사용자 피드백
    
    Returns:
        초기화된 RecommendationState
    """
    return RecommendationState(
        # 사용자 입력
        user_request=user_request,
        query_type="",  # 분류 노드에서 설정
        conversation_history=conversation_history or [],
        user_feedback=user_feedback,
        
        # Agent 인스턴스 (나중에 주입)
        _agents={},
        
        # 추천 프로세스 (빈 값으로 초기화)
        candidates=[],
        housing_result=None,
        loan_info="",
        loan_results=[],
        loan_metadata={},
        # rtms_scores={},  # 현재 미구현
        recommendations=[],
        
        # 메타데이터
        metadata={
            "agent_execution": {}
        },
        iteration=0
    )
