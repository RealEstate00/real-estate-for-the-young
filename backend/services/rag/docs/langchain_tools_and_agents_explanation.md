# LangChain Tool과 Agent 개념 설명

## 📚 기본 개념

### 1. Tool이란?

**Tool**은 LLM이 사용할 수 있는 **함수/도구**입니다. LLM이 직접 할 수 없는 작업(데이터베이스 조회, API 호출, 계산 등)을 대신 수행합니다.

#### 현재 RAG 시스템과의 비교

```
현재 RAG 시스템:
─────────────────
[사용자 질문]
  ↓
[벡터 검색] ← 항상 실행됨
  ↓
[답변 생성]

문제: 항상 검색부터 시작, 유연성 부족
```

```
Tool 기반 시스템:
─────────────────
[사용자 질문]
  ↓
[LLM 판단]
  ├─ "검색이 필요해" → search_tool() 사용
  ├─ "계산이 필요해" → calculator_tool() 사용
  └─ "직접 답할 수 있어" → 바로 답변
```

### 2. Agent란?

**Agent**는 Tool을 선택하고 사용 순서를 결정하는 **지능형 라우터**입니다. LLM이 상황에 맞춰 적절한 Tool을 선택합니다.

## 🔍 구체적인 예시

### 예시 1: 단순 RAG vs Tool 기반

#### 현재 방식 (고정 파이프라인)

```python
# 질문: "서울시 청년 전세대출 금리는 얼마야?"
# → 항상 벡터 검색부터 실행
query = "서울시 청년 전세대출 금리는 얼마야?"
results = vector_search(query)  # 무조건 실행
answer = llm.generate(query, results)
```

#### Tool 기반 방식

```python
# LLM이 판단:
# "이 질문은 검색이 필요해!" → search_tool() 호출
# "이 질문은 단순 계산이야" → calculator_tool() 호출
# "이건 일반 상식이야" → 바로 답변

tools = [
    Tool(
        name="search_knowledge_base",
        func=vector_search,
        description="주거 정책 정보 검색"
    ),
    Tool(
        name="calculator",
        func=calculate,
        description="수치 계산"
    )
]

agent = create_agent(llm, tools)
# LLM이 자동으로 필요한 tool 선택
```

### 예시 2: 복잡한 질문 처리

#### 시나리오: "청년 전세대출 금리가 작년보다 얼마나 올랐어?"

**현재 시스템:**

```
1. 벡터 검색만 실행
2. 작년 데이터와 비교 불가능 (단일 검색 결과만)
3. 계산 로직 없음
```

**Tool 기반 Agent:**

```python
# LLM의 추론 과정:
"""
1. 현재 금리 정보 필요 → search_tool("청년 전세대출 금리")
2. 작년 금리 정보 필요 → search_tool("2023년 청년 전세대출 금리")
3. 비교 계산 필요 → calculator_tool(현재금리 - 작년금리)
4. 결과 종합하여 답변
"""

tools = [
    search_tool,      # 벡터 검색
    calculator_tool,  # 계산기
    date_tool        # 날짜 처리
]

agent.run("청년 전세대출 금리가 작년보다 얼마나 올랐어?")
```

## 🏗️ 현재 시스템에 Tool/Agent 적용 시

### 현재 구조

```
[질문] → [검색] → [리랭킹] → [증강] → [생성] → [답변]
```

### Tool 기반 구조

```
[질문]
  ↓
[Agent 판단]
  ├─ "검색 필요" → search_tool() → [검색 노드]
  ├─ "재검색 필요" → re_search_tool() → [재검색 노드]
  ├─ "특정 모델 사용" → multi_model_search_tool() → [멀티 모델]
  └─ "직접 답변" → [생성 노드]

각 Tool = 현재의 노드 함수
```

## 📋 Tool 구현 예시

### 1. 검색 Tool

```python
from langchain.tools import Tool

# 현재 Retriever를 Tool로 래핑
search_tool = Tool(
    name="vector_search",
    func=lambda query: retriever.search(query, top_k=5),
    description="""
    주거 정책 지식 베이스에서 관련 문서를 검색합니다.
    질문이 정책, 규정, 조건 등에 관한 경우 사용하세요.

    입력: 검색할 질문
    출력: 관련 문서 리스트
    """
)
```

### 2. 멀티 모델 검색 Tool

```python
multi_model_search_tool = Tool(
    name="multi_model_search",
    func=lambda query, model: {
        "E5_SMALL": retriever_e5_small.search(query),
        "E5_LARGE": retriever_e5_large.search(query),
        "KAKAO": retriever_kakao.search(query)
    },
    description="""
    여러 임베딩 모델로 동시에 검색하여 결과를 비교합니다.
    높은 정확도가 필요한 경우 사용하세요.
    """
)
```

### 3. 계산 Tool

```python
calculator_tool = Tool(
    name="calculator",
    func=eval,  # 또는 안전한 계산기 라이브러리
    description="""
    수치 계산을 수행합니다.
    금리, 금액, 비율 등의 계산에 사용하세요.
    """
)
```

### 4. 데이터 조회 Tool

```python
db_query_tool = Tool(
    name="query_database",
    func=lambda sql: db.execute(sql),
    description="""
    데이터베이스에서 직접 데이터를 조회합니다.
    정확한 수치나 통계 정보가 필요한 경우 사용하세요.
    """
)
```

## 🤖 Agent 구현 예시

### ReAct Agent (추론 → 행동 반복)

```python
from langchain.agents import AgentType, initialize_agent
from langchain.llms import OllamaLLM

# 현재 RAG 시스템의 LLM 사용
llm = OllamaLLM(model="gemma3:4b")

# Tool 리스트
tools = [
    search_tool,
    calculator_tool,
    db_query_tool,
    multi_model_search_tool
]

# Agent 생성
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.REACT_DESCRIPTION,
    verbose=True
)

# 실행
response = agent.run("청년 전세대출 금리가 작년보다 얼마나 올랐어?")

# Agent의 추론 과정:
# Thought: 이 질문은 두 가지 정보가 필요하다
# Action: search_tool("청년 전세대출 금리")
# Observation: 현재 금리는 2.5%
# Thought: 이제 작년 금리를 찾아야 한다
# Action: search_tool("2023년 청년 전세대출 금리")
# Observation: 작년 금리는 2.0%
# Thought: 차이를 계산해야 한다
# Action: calculator_tool("2.5 - 2.0")
# Observation: 0.5%
# Final Answer: 청년 전세대출 금리는 작년 대비 0.5%p 올랐습니다.
```

## 🔄 현재 RAG vs Tool/Agent 기반 RAG

### 현재 시스템의 한계

```python
# 항상 동일한 파이프라인
def answer(query):
    # 1. 항상 검색
    docs = vector_search(query)

    # 2. 항상 리랭킹
    docs = rerank(query, docs)

    # 3. 항상 증강
    context = augment(query, docs)

    # 4. 항상 생성
    return generate(query, context)

# 문제:
# - 간단한 질문에도 불필요한 검색 실행
# - 재검색 불가능
# - 다른 데이터 소스 활용 불가
```

### Tool/Agent 기반의 장점

```python
# 상황에 맞춰 유연하게 실행
def answer_with_agent(query):
    # Agent가 판단
    if is_simple_question(query):
        # 바로 답변
        return llm.generate(query)

    elif needs_search(query):
        # 검색 Tool 사용
        docs = search_tool(query)
        return generate(query, docs)

    elif needs_recalculation(query):
        # 계산 Tool 사용
        result = calculator_tool(calculate_from_results(docs))
        return format_answer(result)

    # 복합 작업도 가능
    # 검색 → 계산 → 추가 검색 → 답변
```

## 🎯 실제 사용 케이스

### 케이스 1: 간단한 질문

```
질문: "청년 전세대출 신청 나이 제한은?"
Agent 판단: 검색 필요
→ search_tool() 사용
→ 바로 답변
```

### 케이스 2: 계산이 필요한 질문

```
질문: "월소득 300만원이면 최대 대출 한도는?"
Agent 판단: 검색 + 계산 필요
→ search_tool("소득별 대출 한도")
→ calculator_tool("300만원 * 대출비율")
→ 답변
```

### 케이스 3: 비교 질문

```
질문: "청년 전세대출과 일반 전세대출의 차이점은?"
Agent 판단: 여러 검색 필요
→ search_tool("청년 전세대출")
→ search_tool("일반 전세대출")
→ 비교 분석
→ 답변
```

### 케이스 4: 재검색이 필요한 경우

```
질문: "청년 전세대출 신청 방법"
Agent 판단: 첫 검색 결과가 부족함
→ search_tool() (첫 검색)
→ 평가: 품질 낮음
→ re_search_tool() (재검색, 다른 키워드)
→ 답변
```

## 🔧 현재 시스템에 적용하는 방법

### 1단계: 현재 노드를 Tool로 변환

```python
# 현재: retriever.search()
# 변환: Tool로 래핑

from langchain.tools import Tool

# 검색 Tool
search_tool = Tool(
    name="knowledge_base_search",
    func=lambda q: retriever.search(q, top_k=5),
    description="주거 정책 지식 베이스 검색"
)

# 리랭킹 Tool
rerank_tool = Tool(
    name="rerank_documents",
    func=lambda q, docs: reranker.rerank(q, docs),
    description="검색 결과 리랭킹"
)
```

### 2단계: Agent 생성

```python
from langchain.agents import initialize_agent

tools = [search_tool, rerank_tool]
agent = initialize_agent(
    tools=tools,
    llm=OllamaLLM(model="gemma3:4b"),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)
```

### 3단계: 사용

```python
# 기존: 항상 검색 → 리랭킹 → 생성
# 새로운: Agent가 필요에 따라 선택

response = agent.run("청년 전세대출 조건")
# Agent가 자동으로 search_tool → rerank_tool 사용
```

## 📊 비교 요약

| 특징               | 현재 RAG         | Tool/Agent RAG           |
| ------------------ | ---------------- | ------------------------ |
| **실행 방식**      | 고정 파이프라인  | 동적 선택                |
| **유연성**         | 낮음 (항상 동일) | 높음 (상황별)            |
| **재검색**         | 불가능           | 가능                     |
| **다른 도구 활용** | 불가능           | 가능 (계산기, DB 등)     |
| **복잡한 질문**    | 한계 있음        | 잘 처리                  |
| **구현 복잡도**    | 간단             | 중간                     |
| **성능**           | 빠름 (고정)      | 느릴 수 있음 (추론 필요) |

## 💡 언제 Tool/Agent가 유용한가?

### ✅ 유용한 경우

1. **복잡한 질문**

   - 여러 단계가 필요한 질문
   - 예: "작년 대비 금리 변화는?"

2. **다양한 데이터 소스**

   - 벡터 검색 + 데이터베이스 + API
   - 예: 검색 → DB 조회 → 계산

3. **동적 재검색**

   - 첫 결과가 부족하면 재검색
   - 예: 키워드 변경하여 재검색

4. **사용자 피드백 반영**
   - "더 자세히" → 추가 검색
   - "다른 관점" → 다른 모델 검색

### ❌ 불필요한 경우

1. **단순 질문**

   - 직접 답변 가능한 경우
   - 예: "안녕하세요"

2. **성능이 중요한 경우**

   - 실시간 응답이 필요한 경우
   - Tool 선택 오버헤드가 부담

3. **고정된 워크플로우**
   - 항상 같은 과정이면 기존 방식이 더 빠름

## 🚀 LangGraph + Agent 조합

```python
from langgraph.graph import StateGraph
from langchain.agents import AgentExecutor

# Graph 내부에 Agent 노드 추가
def agent_node(state):
    """Agent가 Tool을 선택하고 실행"""
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools
    )
    result = agent_executor.invoke({"input": state["query"]})
    return {"agent_response": result["output"]}

# 그래프 구성
graph = StateGraph(RAGState)
graph.add_node("query_embedding", query_embedding_node)
graph.add_node("agent", agent_node)  # Agent 노드
graph.add_node("generation", generation_node)

graph.add_edge("query_embedding", "agent")
graph.add_edge("agent", "generation")
```

이렇게 하면 **그래프 구조 안에서도 Agent가 유연하게 Tool을 선택**할 수 있습니다.
