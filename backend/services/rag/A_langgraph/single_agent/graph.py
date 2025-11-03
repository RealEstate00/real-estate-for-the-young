"""
그래프 모듈

LangGraph 워크플로우 구성 및 라우팅 로직
"""

import threading
from langgraph.graph import StateGraph

from .state import AssistantState
from .nodes import ai_agent_node, tool_execution_node, final_response_node


# ========== 라우팅 함수 ==========
def should_use_tools(state: AssistantState) -> str:
    """도구 사용이 필요한지 판단하는 라우팅 함수"""
    last_message = state["messages"][-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print("라우팅: 도구 실행 필요 → 도구 실행 노드로")
        return "execute_tools"
    else:
        print("라우팅: 도구 실행 불필요 → 최종 응답으로")
        return "final_response"


# ========== 그래프 생성 ==========
def rey_ai_assistant():
    """도구를 사용하는 rey ai 그래프 (수정된 버전)"""
    
    # 그래프를 생성할 객체 생성
    workflow = StateGraph(AssistantState)
    
    # 노드 추가 (수정된 노드 함수들 사용)
    workflow.add_node("ai_agent", ai_agent_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("final_response", final_response_node)
    
    # 시작점 설정
    workflow.set_entry_point("ai_agent")
    
    # 조건부 엣지 추가
    workflow.add_conditional_edges(
        "ai_agent",
        should_use_tools,
        {
            "execute_tools": "tool_execution",
            "final_response": "final_response"
        }
    )
    
    # 도구 실행 후에는 다시 최종 응답으로
    workflow.add_edge("tool_execution", "final_response")
    
    # 최종 응답 노드에서 최종 응답 반환
    workflow.set_finish_point("final_response")

    ##################################################
    # 컴파일 -> 그래프 생성
    ##################################################
    return workflow.compile()


# ========== 싱글톤 설정 ==========
# 싱글톤은 클래스로 구현하는 것이 가장 바람직한 이유는
# 1. 코드의 구조가 더 명확해지고,
# 2. 인스턴스 관리(예: 생성/초기화, 스레드 세이프티, 상태 보존 등)를 OOP로 일관성 있게 처리할 수 있기 때문입니다.
# 3. 테스트/확장/유지보수가 훨씬 용이함. 모듈 전역 변수 방식은 코드가 복잡해지면 꼬일 수 있습니다.


class ReyAIGraphSingleton:
    """
    ReyAI 그래프 싱글톤 클래스
    
    Double-Checked Locking 패턴을 사용하여 멀티스레드 환경에서도
    안전하게 단일 인스턴스만 생성되도록 보장합니다.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._graph = rey_ai_assistant()
        return cls._instance

    @property
    def graph(self):
        """싱글톤 그래프 인스턴스 반환"""
        return self._graph


def get_rey_ai_graph():
    """
    rey_ai_assistant 싱글톤 그래프 반환.
    클래스로 구현하여 구조적이고 확장성 있게 관리합니다.
    """
    return ReyAIGraphSingleton().graph

