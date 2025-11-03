"""
State 정의

LangGraph의 상태 관리
"""

from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict


class AssistantState(TypedDict):
    """ai 주택정보 상담 에이전트의 상태"""
    messages: Annotated[list, add_messages]  # 그동안 나눈 메세지 저장
    tools_used: list

