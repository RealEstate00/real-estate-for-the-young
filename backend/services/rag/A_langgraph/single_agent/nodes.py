"""
노드 정의

LangGraph의 노드 함수들
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage

from .state import AssistantState
from .tools import create_llm_with_tools, rdb_search, vector_search


# ========== AI 에이전트 노드 ==========
def ai_agent_node(state: AssistantState):
    """
    사용자 요청을 분석하고 필요한 도구를 사용하는 AI 에이전트
    """
    llm_with_tools = create_llm_with_tools()
    
    # 시스템 프롬프트로 역할 부여
    system_prompt = SystemMessage(content="""
    당신은 도움이 되는 AI 개인 비서입니다.
    사용자의 요청을 분석하여 적절한 도구를 **하나만** 선택해 사용하세요.

    ⚠️ 중요: 이 시스템은 "매물"이나 "판매용 주택"이 아닌 "사회주택"과 "공동체주택" 정보를 다룹니다.

    사용 가능한 도구:
    - rdb_search: 사회주택 및 공동체주택 정보 검색 (지역별 주택 공고 정보, 공공시설 정보)
      * housing.notices 테이블에는 사회주택/공동체주택 공고 정보가 저장되어 있습니다.
      * infra.facility_info 테이블에는 공공시설 정보가 저장되어 있습니다.
      * 사용자가 "강서구 주택"이라고 요청하면 "강서구에 있는 사회주택 및 공동체주택 공고 조회"로 이해해야 합니다.
      * "매물", "판매", "구매" 등의 용어는 사용하지 마세요. "공고", "사회주택", "공동체주택" 용어를 사용하세요.
    - vector_search: 금융 정책 문서 검색 (청년 지원 정책, 대출 제도 등 - 일반적인 질문에만 사용)

    **도구 선택 규칙:**
    - 지역명, 주택, 공공시설 관련 질문 → rdb_search만 사용
    - 청년 지원 정책, 금융 제도 관련 질문 → vector_search만 사용
    - 둘 다 사용하지 말고 하나만 선택하세요!

    rdb_search 도구를 사용할 때는, 사용자의 원래 요청을 그대로 rdb_search에 입력값으로 전달하세요.
    (예: "강서구에 있는 주택알려줘" → rdb_search로 그대로 입력)
    쿼리 변환이나 재가공 없이, 적합한 도구를 정하고 사용자의 입력을 해당 도구에 전달하세요.
    """)
    
    # 기존 메시지에 시스템 프롬프트 추가
    messages = [system_prompt] + state["messages"]
    
    print("AI 에이전트가 요청을 분석 중...")
    response = llm_with_tools.invoke(messages)
    
    # 도구 사용 여부 확인
    if response.tool_calls:
        print(f"{len(response.tool_calls)}개의 도구를 사용합니다:")
        for tool_call in response.tool_calls:
            print(f"   - {tool_call['name']}: {tool_call['args']}")
    else:
        print("도구 사용 없이 직접 응답합니다.")
    
    # ✅ 반드시 딕셔너리 반환
    return {
        "messages": [response],
        "tools_used": [tool_call['name'] for tool_call in response.tool_calls] if response.tool_calls else []
    }


# ========== 도구 실행 노드 ==========
def tool_execution_node(state: AssistantState):
    """
    AI가 요청한 도구들을 실제로 실행하는 노드
    """
    last_message = state["messages"][-1]
    
    if not last_message.tool_calls:
        # 도구 호출이 없으면 빈 메시지 리스트 반환
        return {"messages": []}
    
    tool_results = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        print(f"{tool_name} 실행 중... (인자: {tool_args})")
        
        try:
            if tool_name == "rdb_search":
                result = rdb_search.invoke({"query": tool_args["query"]})
            elif tool_name == "vector_search":
                result = vector_search.invoke({"query": tool_args["query"]})
            else:
                result = f"알 수 없는 도구: {tool_name}"
            
            print(f"{tool_name} 실행 완료: {result[:100]}...")
            
            # 도구 실행 결과를 ToolMessage로 생성
            tool_message = ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]
            )
            tool_results.append(tool_message)
            
        except Exception as e:
            print(f"{tool_name} 실행 오류: {e}")
            error_message = ToolMessage(
                content=f"도구 실행 중 오류가 발생했습니다: {str(e)}",
                tool_call_id=tool_call["id"]
            )
            tool_results.append(error_message)
    
    # ✅ 반드시 딕셔너리 반환
    return {"messages": tool_results}


# ========== 최종 응답 노드 ==========
def final_response_node(state: AssistantState):
    """
    도구 실행 결과를 바탕으로 최종 응답을 생성하는 노드
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,  # 더 빠른 토큰 생성을 위해 낮춤
    )

    # 도구 사용 여부 확인
    tools_used = state.get("tools_used", [])

    if tools_used:
        # 도구를 사용한 경우: 검색 결과 기반 답변
        system_prompt = SystemMessage(content="""
        도구 실행 결과를 바탕으로 사용자에게 간결하고 명확한 답변을 제공하세요.

        답변 가이드라인:
        1. 검색 결과를 간결하게 요약 (불필요한 서론/결론 제거)
        2. 핵심 정보만 2-3문장으로 제공
        3. 이모지 사용 최소화
        4. 검색 결과가 없으면 "현재 등록된 정보가 없습니다"라고 간단히 답변
        """)
    else:
        # 도구를 사용하지 않은 경우: 일반 대화
        system_prompt = SystemMessage(content="""
        당신은 친절한 AI 비서입니다. 사용자에게 자연스럽고 따뜻하게 응답하세요.

        답변 가이드라인:
        1. 인사, 소개 등 일반적인 대화에는 친근하게 응답
        2. 간결하고 명확한 답변 제공
        3. 이모지 사용 최소화
        """)
    
    # 전체 대화 컨텍스트 포함
    messages = [system_prompt] + state["messages"]
    
    print("최종 응답 생성 중...")
    response = llm.invoke(messages)
    
    # response에서 content가 없으면 content로 감싸서 반환
    if hasattr(response, "content"):
        result_message = {"content": response.content}
    elif isinstance(response, dict) and "content" in response:
        result_message = {"content": response["content"]}
    else:
        result_message = {"content": str(response)}

    # ✅ 반드시 딕셔너리 반환
    return {"messages": [response]}

