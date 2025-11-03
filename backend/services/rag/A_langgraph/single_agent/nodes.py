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
    사용자의 요청을 분석하여 적절한 도구를 사용해 도와주세요.
    
    ⚠️ 중요: 이 시스템은 "매물"이나 "판매용 주택"이 아닌 "사회주택"과 "공동체주택" 정보를 다룹니다.
    
    사용 가능한 도구:
    - rdb_search: 사회주택 및 공동체주택 정보 검색 (지역별 주택 공고 정보)
      * housing.notices 테이블에는 사회주택/공동체주택 공고 정보가 저장되어 있습니다.
      * 사용자가 "강서구 주택"이라고 요청하면 "강서구에 있는 사회주택 및 공동체주택 공고 조회"로 이해해야 합니다.
      * "매물", "판매", "구매" 등의 용어는 사용하지 마세요. "공고", "사회주택", "공동체주택" 용어를 사용하세요.
    - vector_search: 금융 정책 정보 검색 (청년 지원, 대출 정보 등)
    
    정확한 도구이름을 반환하세요
    
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
                result = rdb_search(tool_args["query"])
            elif tool_name == "vector_search":
                result = vector_search(tool_args["query"])
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
        model="gpt-4o-mini",  # gpt-5-nano는 존재하지 않음
        temperature=0.7,
    )
    
    system_prompt = SystemMessage(content="""
    도구 실행 결과를 바탕으로 사용자에게 친근하고 도움이 되는 최종 답변을 제공하세요.
    
    답변 가이드라인:
    1. 검색 결과가 있으면 구체적이고 유용한 정보를 제공
    2. 검색 결과가 없으면 대안을 제시
    3. 친근하고 도움이 되는 톤으로 작성
    4. 필요하면 추가 질문을 유도
    """)
    
    # 전체 대화 컨텍스트 포함
    messages = [system_prompt] + state["messages"]
    
    print("최종 응답 생성 중...")
    response = llm.invoke(messages)
    
    # ✅ 반드시 딕셔너리 반환
    return {"messages": [response]}

