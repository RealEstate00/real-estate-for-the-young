"""
Single Agent RAG System - 실행 예제

노트북 내용을 그대로 모듈화한 버전

Usage:
    uv run python backend/services/rag/A_langgraph/single_agent/test.py
    python -m backend.services.rag.A_langgraph.single_agent.test
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가 (pyproject.toml이 있는 디렉토리)
current_file = Path(__file__).resolve()
project_root = current_file.parent
for _ in range(10):  # 최대 10단계 상위로 탐색
    if (project_root / "pyproject.toml").exists():
        break
    parent = project_root.parent
    if parent == project_root:  # 루트에 도달
        project_root = current_file.parents[5]  # 폴백: 수동 계산
        break
    project_root = parent

sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage
from backend.services.rag.A_langgraph.single_agent.graph import get_rey_ai_graph
from backend.services.rag.A_langgraph.single_agent.state import AssistantState


def main(query=None):
    """메인 실행 함수"""
    # 싱글톤 그래프 가져오기
    graph = get_rey_ai_graph()
    
    # 테스트 쿼리 (기본값)
    if query is None:
        query = "강서구에 있는 주택 추천해줘"
    
    # 초기 상태 생성
    initial_state: AssistantState = {
        "messages": [HumanMessage(content=query)],
        "tools_used": []
    }
    
    # 그래프 실행
    print(f"🔄 쿼리: {query}")
    print("-" * 50)
    final_state = graph.invoke(initial_state)
    
    # 결과 출력
    messages = final_state.get("messages", [])
    tools_used = final_state.get("tools_used", [])
    
    print(f"\n✅ 실행 완료!")
    print(f"📊 사용된 도구: {tools_used if tools_used else '없음'}")
    print(f"💬 메시지 수: {len(messages)}")
    
    # 최종 응답 출력
    if messages:
        final_message = messages[-1]
        if hasattr(final_message, 'content'):
            print(f"\n🤖 AI 응답:\n{final_message.content}")
        else:
            print(f"\n🤖 AI 응답: {str(final_message)}")


if __name__ == "__main__":
    main("월세지원을 받는 중 군입대하면 어떻게 되는거야?")

