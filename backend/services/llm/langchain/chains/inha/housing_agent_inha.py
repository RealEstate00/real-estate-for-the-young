"""
주택 검색 Agent
하이브리드 LLM 지원 (설정으로 활성화/비활성화)
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from backend.services.llm.models.inha.llm_inha import agent_llm, response_llm, USE_HYBRID
from backend.services.llm.prompts.inha.prompt_inha import agent_prompt, rag_prompt
from backend.services.llm.utils.inha.housing_tools_inha import search_housing

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# Agent 설정
# ============================================================================

# 도구 목록 (향후 확장 가능)
tools = [search_housing]

# Agent 생성 (도구 호출용)
agent = create_tool_calling_agent(agent_llm, tools, agent_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)


# ============================================================================
# 메인 함수
# ============================================================================

def housing_assistant(query: str, use_hybrid: bool = USE_HYBRID) -> str:
    """
    주택 검색 어시스턴트

    Args:
        query: 사용자 질문
        use_hybrid: 하이브리드 모드 사용 여부

    Returns:
        답변 텍스트
    """
    try:
        if use_hybrid:
            # Phase 1: Agent LLM이 도구 실행
            logger.info(f"[Hybrid Mode] Agent LLM 실행: {query}")
            search_results = agent_executor.invoke({"input": query})

            # Phase 2: Response LLM이 최종 답변 생성
            logger.info("[Hybrid Mode] Response LLM 답변 생성")
            final_response = (
                rag_prompt
                | response_llm
                | StrOutputParser()
            ).invoke({
                "context": search_results["output"],
                "query": query
            })
            return final_response
        else:
            # 단일 LLM 모드 (기본)
            logger.info(f"[Single LLM Mode] Agent 실행: {query}")
            result = agent_executor.invoke({"input": query})
            return result["output"]

    except Exception as e:
        logger.error(f"Housing assistant failed: {e}")
        return f"죄송합니다. 검색 중 오류가 발생했습니다: {e}"


