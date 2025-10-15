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


# ============================================================================
# 메인 함수
# ============================================================================

def is_tool_related_query(query: str) -> bool:
    """
    질문이 도구 사용이 필요한 주택 검색 관련 질문인지 판단
    
    Args:
        query: 사용자 질문
        
    Returns:
        bool: 도구 사용 필요 여부
    """
    # 주택 검색 관련 키워드
    housing_keywords = [
        "주택", "아파트", "원룸", "투룸", "쓰리룸", "오피스텔", "빌라", "단독주택",
        "청년주택", "임대주택", "전세", "월세", "매매", "분양",
        "서울", "강남", "강북", "서초", "송파", "마포", "영등포", "용산", "성동", "광진",
        "강동", "송파", "강서", "양천", "구로", "금천", "관악", "서대문", "은평", "노원", "도봉",
        "추천", "찾아", "보여", "검색", "모두", "전부", "어디", "있어", "없어"
    ]
    
    query_lower = query.lower()
    
    # 주택 검색 관련 키워드가 있으면 도구 사용, 없으면 일반 대화
    return any(keyword in query_lower for keyword in housing_keywords)


def housing_assistant(query: str, memory=None, use_hybrid: bool = USE_HYBRID) -> str:
    """
    주택 검색 어시스턴트

    Args:
        query: 사용자 질문
        memory: ConversationSummaryBufferMemory 객체 (대화 맥락 관리)
        use_hybrid: 하이브리드 모드 사용 여부

    Returns:
        답변 텍스트
    """
    try:
        # AgentExecutor를 메모리와 함께 생성
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,  # 메모리 통합
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=2  # 토큰 절약을 위해 2회로 제한
        )
        
        if use_hybrid:
            # 하이브리드 모드: 질문 유형에 따라 다른 처리
            if is_tool_related_query(query):
                # Phase 1: Agent LLM이 도구 실행 (주택 검색 관련)
                logger.info(f"[Hybrid Mode] Tool 관련 질문 - Agent LLM 실행: {query}")
                search_results = agent_executor.invoke({"input": query})

                # Phase 2: Response LLM이 최종 답변 생성
                logger.info("[Hybrid Mode] Response LLM 답변 생성 (도구 결과 기반)")
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
                # 일반 대화: Response LLM만 사용 (도구 사용 안함)
                logger.info(f"[Hybrid Mode] 일반 대화 - Response LLM만 실행: {query}")
                simple_response = (
                    rag_prompt
                    | response_llm
                    | StrOutputParser()
                ).invoke({
                    "context": "",  # 빈 컨텍스트 (검색 결과 없음)
                    "query": query
                })
                return simple_response
        else:
            # 단일 LLM 모드 (기본)
            logger.info(f"[Single LLM Mode] Agent 실행: {query}")
            result = agent_executor.invoke({"input": query})
            return result["output"]

    except Exception as e:
        logger.error(f"Housing assistant failed: {e}")
        return f"죄송합니다. 검색 중 오류가 발생했습니다: {e}"




# =============================================================================
# 테스트 코드
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Agent 기반 주택 추천 시스템 테스트")
    print("=" * 80)
    
    # 테스트 쿼리들
    test_queries = [
        # "강남구 청년주택 추천해줘",
        "서초구에 있는 주택 모두 보여줘",
        "대치동 근처 좋은 주택 추천해줘"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n\n💬 테스트 {i}: {query}")
        print("-" * 80)
        
        try:
            # Agent 실행
            response = housing_assistant(query)
            print(response)
            
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
        
        print("-" * 80)
    
    print("\n✅ 모든 테스트 완료!")