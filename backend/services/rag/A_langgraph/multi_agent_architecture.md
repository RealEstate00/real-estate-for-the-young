# Multi-Agent LangGraph 추천 시스템 아키텍처 설계

## 개요

이 문서는 LangGraph와 Multi-Agent 시스템을 활용한 **대화형 주거 매물 추천 시스템** 설계를 다룹니다. 전문화된 에이전트들이 협업하여 사용자 선호도를 파악하고, 복잡한 다단계 추론을 통해 최적의 매물을 추천하는 시스템입니다.

**핵심 특징:**
- ✅ **대화형 추천**: 사용자와 대화하며 선호도 파악
- ✅ **복잡한 다단계 추론**: 여러 단계를 거쳐 정확한 추천 생성
- ✅ **여러 데이터 소스 동적 통합**: 주택, 인프라, 대출 정책, 실거래가 등 실시간 통합
- ✅ **사용자 피드백 실시간 반영**: 피드백을 즉시 반영하여 추천 개선

---

## Multi-Agent 추천 시스템 아키텍처

### 대화형 추천 플로우

```
[사용자 요청]
    ↓
[질문 분류] - LLM으로 housing/finance/general 판별
    ↓
┌─────────────────────────────────────────────────┐
│ housing 질문                                     │
│    ↓                                            │
│ [Housing Agent] → 주택 매물 검색 (RDB)         │
│    ↓                                            │
│ [Recommendation Agent] → 최종 추천 생성         │
│    ↓                                            │
│ [END]                                           │
├─────────────────────────────────────────────────┤
│ finance 질문                                     │
│    ↓                                            │
│ [Loan Agent] → 대출 정보 검색 (Vector DB)       │
│    ↓                                            │
│ [Recommendation Agent] → 최종 추천 생성         │
│    ↓                                            │
│ [END]                                           │
├─────────────────────────────────────────────────┤
│ general 질문                                     │
│    ↓                                            │
│ [General LLM] → 직접 답변                       │
│    ↓                                            │
│ [END]                                           │
└─────────────────────────────────────────────────┘
```

**참고:**
- **질문 분류**: Ollama Gemma 3 4b로 사용자 질문을 자동 분류
- **RTMS Agent**: 실거래가 정보 제공 (현재 미구현)
- **PostGIS**: 인프라 점수 계산 (나중에 확장 예정)
- **Feedback Agent**: 피드백 반영 (Phase 2 구현 예정)

**핵심 특징:**
- **스마트 라우팅**: 질문 분류에 따라 적절한 Agent로 자동 라우팅
- **전문화된 Agent**: Housing Agent (RDB), Loan Agent (Vector DB), General LLM
- **확장성**: 새 Agent 추가 용이

**현재 구현:**
- ✅ 질문 분류 (LLM 기반)
- ✅ Housing Agent (주택 매물 검색)
- ✅ Loan Agent (대출 정보 검색)
- ✅ General LLM (일반 질문 답변)
- ✅ Recommendation Agent (최종 추천)

**Phase 2 확장 예정:**
- RTMS Agent (실거래가 점수)
- Feedback Agent (피드백 반영)
- PostGIS (인프라 점수)
- 대출 가능 여부 확인

---

## 상세 비교: Single Agent vs Multi-Agent

### 옵션 1: Multi-Tool Single Agent

```python
tools = [
    rdb_search_tool,      # RDB 검색
    vector_search_tool,   # Vector DB 검색
    loan_api_tool,        # 대출 API
    calculator_tool       # 계산
]

agent = create_react_agent(llm, tools)
```

**장점:**
- 구현 단순
- Tool 간 전환 자유로움
- 통합된 추론 과정

**단점:**
- Tool이 많으면 Agent 혼란
- 전문성 부족 (SQL 최적화 어려움)
- 하나의 프롬프트로 모든 도메인 커버

---

### 옵션 2: Multi-Agent Collaboration ⭐ 추천

```python
housing_agent = Agent(
    tools=[list_tables, query_rdb, schema_info],
    system_prompt="주택 데이터베이스 전문가"
)

loan_agent = Agent(
    tools=[vector_search, loan_api, rerank],
    system_prompt="대출 정책 전문가"
)

supervisor = create_supervisor([housing_agent, loan_agent])
```

**장점:**
- 각 에이전트가 전문화 (SQL 최적화, 대출 도메인 지식)
- 명확한 도메인 분리 (주택 vs 대출)
- 확장성 좋음 (새 도메인 = 새 에이전트)
- 디버깅 쉬움 (에이전트별 로그)

**단점:**
- 구현 복잡도 증가
- 에이전트 간 통신 오버헤드

---

## 프로젝트에 Multi-Agent 추천 시스템이 필요한 이유

### 1. 복잡한 다단계 추론 필요

**전통적인 추천 시스템:**
```python
# 단순 SQL 쿼리로 끝
candidates = db.query(location="강남구", type="원룸")
return candidates[:10]  # 끝
```

**Multi-Agent 추천 시스템:**
```python
# 복잡한 다단계 추론
1. Housing Agent: 강남구 원룸 검색 (50건)
2. Loan Agent: 대출 관련 정보 제공 (Vector DB)
3. RTMS Agent: 실거래가와 비교 → 가격 적정성 점수
4. Recommendation Agent: 상위 10개 선별
5. 피드백 수집 → 재추천 (필요 시)

# 나중에 확장 예정:
# - Infra Agent: 지하철역 거리 계산 (PostGIS) → 점수 부여
# - Loan Agent: 실제 대출 가능 여부 확인 → 필터링
# - Scoring Agent: 종합 점수 계산 (가중 평균)
```

### 2. 여러 데이터 소스 동적 통합

```
주택 데이터 (RDB)
├─ housing.notices (매물 정보)
└─ housing.units (호실 정보)
→ Housing Agent 담당

인프라 데이터 (RDB + PostGIS) - 나중에 확장 예정
├─ public_facilities (공공시설)
├─ subway_stations (지하철역)
└─ 거리 계산 (PostGIS 공간 쿼리)
→ Infra Agent 담당 (현재 미구현)

대출 정책 (Vector DB)
├─ 정책 문서 (Vector DB)
├─ 실시간 금리 (API)
└─ 자격 조건 확인
→ Loan Agent 담당

실거래가 데이터 (RDB)
├─ transaction_data (실거래가)
└─ price_trends (가격 동향)
→ RTMS Agent 담당
```

### 3. 대화형 추천 지원

```python
# 사용자와 대화하며 선호도 파악
턴 1: "강남구 원룸 추천해줘"
→ 초기 추천 10개

턴 2: "너무 비싸"
→ 가격 필터링 Agent 재실행
→ 재추천 10개

턴 3: "지하철역 좀 더 가까운 거"
→ 거리 재계산 Agent 실행
→ 재추천 10개

턴 4: "이건 대출 정보 알려줘"
→ Loan Agent 호출
→ 대출 관련 정보 제공 (Vector DB에서 검색)
```

### 4. 사용자 피드백 실시간 반영

```python
# 피드백 루프
[초기 추천]
    ↓
[사용자 피드백 수집]
    ├─ 좋아요/싫어요 클릭
    ├─ 조회/미조회
    └─ 추가 요구사항
    ↓
[피드백 분석 Agent]
    ├─ 선호 패턴 추출
    └─ 가중치 조정
    ↓
[재추천 (피드백 반영)]
```

### 5. 확장성

```python
# 새 데이터 소스 추가 쉬움
infra_agent = Agent(...)      # 인프라 데이터
rtms_agent = Agent(...)       # 실거래가 데이터
policy_agent = Agent(...)      # 정부 정책 (웹 크롤링)
weather_agent = Agent(...)     # 날씨 API (추후)
```

---

## 기존 RAG 함수 재사용

### 핵심 원칙: 기존 코드 활용 (90% 재사용)

Multi-Agent 시스템은 **기존 RAG 시스템의 함수들을 그대로 재사용**합니다. 새로 작성하는 코드는 재검색 로직과 Agent 래핑 코드뿐입니다.

### 기존 RAG 시스템 구조

```
backend/services/rag/
├── retrieval/
│   ├── retriever.py           # Retriever.search() ✅
│   └── reranker.py            # KeywordReranker.rerank() ✅
├── models/
│   ├── encoder.py             # EmbeddingEncoder.encode_query() ✅
│   └── config.py              # EmbeddingModelType ✅
├── augmentation/
│   └── augmenter.py           # DocumentAugmenter.augment() ✅
├── generation/
│   └── generator.py           # OllamaGenerator.generate() ✅
└── vectorstore/
    └── ingestion/store.py     # PgVectorStore ✅
```

### Loan Agent의 기존 함수 활용

```python
# agents/loan_agent.py

from backend.services.rag.retrieval.retriever import Retriever  # ← 기존 import ✅
from backend.services.rag.models.config import EmbeddingModelType

class LoanAgent:
    def __init__(self, retriever):
        # 기존 Retriever 인스턴스를 받음
        self.retriever = retriever  # ← 기존 Retriever 그대로 사용 ✅

    def _search_vector(self, query: str) -> str:
        """1단계: 기본 검색 - 기존 함수 그대로 호출"""

        # 기존 Retriever.search() 호출 ✅
        results = self.retriever.search(
            query=query,
            top_k=5,
            min_similarity=0.5,
            use_reranker=True  # ← 기존 KeywordReranker 사용 ✅
        )

        return self._format_results(results)

    def _search_vector_advanced(self, query: str) -> str:
        """2단계: 재검색 - 기존 함수 반복 호출"""

        # 쿼리 변형 생성 (새 로직 ✨)
        variants = self._generate_query_variants(query)

        all_results = []
        for variant in variants:
            # 기존 Retriever.search() 반복 호출 ✅
            results = self.retriever.search(
                query=variant,
                top_k=3,
                min_similarity=0.4
            )
            all_results.extend(results)

        # 중복 제거 (새 로직 ✨)
        unique = self._deduplicate_results(all_results)

        # 리랭킹 - 기존 reranker 활용 ✅
        if hasattr(self.retriever, 'reranker'):
            return self.retriever.reranker.rerank(query, unique)

        return unique
```

### 기존 함수 재사용 목록

| 기존 함수                          | 위치                            | 사용처                  |
|------------------------------------|---------------------------------|-------------------------|
| `Retriever.search()`               | `retrieval/retriever.py:48`     | ✅ Loan Agent 직접 호출 |
| `EmbeddingEncoder.encode_query()`  | `models/encoder.py`             | ✅ Retriever 내부 사용  |
| `KeywordReranker.rerank()`         | `retrieval/reranker.py`         | ✅ Retriever 내부 사용  |
| `PgVectorStore.search_similar()`   | `vectorstore/ingestion/store.py`| ✅ Retriever 내부 사용  |
| `DocumentAugmenter.augment()`      | `augmentation/augmenter.py`     | 🔄 Supervisor에서 사용  |
| `OllamaGenerator.generate()`       | `generation/generator.py`       | 🔄 Supervisor에서 사용  |

### 새로 작성하는 코드 (10%)

#### 1. 재검색 로직 (Query Rewriting)

```python
# agents/loan_agent.py

# ✨ 새로 작성
def _generate_query_variants(self, query: str, num_variants: int = 3) -> List[str]:
    """LLM으로 쿼리 변형 생성"""
    prompt = f"""다음 질문을 {num_variants}가지 다른 방식으로 표현하세요.

원래 질문: {query}

규칙:
1. 각 줄에 하나씩, 번호 없이
2. 의미는 같지만 표현 다르게
3. 전문 용어 ↔ 일상 용어 변환
"""
    response = self.llm.invoke(prompt)
    variants = [line.strip() for line in response.content.split('\n') if line.strip()]
    return [query] + variants  # 원본 포함

# ✨ 새로 작성
def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
    """중복 제거 (ID 기준)"""
    unique = {}
    for result in results:
        doc_id = result['id']
        if doc_id not in unique or result['similarity'] > unique[doc_id]['similarity']:
            unique[doc_id] = result
    return list(unique.values())

# ✨ 새로 작성 (하지만 기존 reranker 활용)
def _rerank_by_original_query(self, query: str, results: List[Dict]) -> List[Dict]:
    """원본 쿼리로 리랭킹"""
    # 기존 reranker가 있으면 사용 ✅
    if hasattr(self.retriever, 'reranker') and self.retriever.reranker:
        return self.retriever.reranker.rerank(query, results)

    # 없으면 similarity 정렬
    return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)[:5]
```

#### 2. Agent 패턴 비교

**⚠️ 참고: 현재 설계에서는 AgentExecutor를 사용하지 않습니다.**
**아래는 Agent 패턴의 차이점을 설명하기 위한 예시입니다.**

**Loan Agent (이전 버전 - 더 이상 사용 안 함):**
```python
# ❌ 이전 방식: AgentExecutor 사용
self.tools = [
    Tool(name="search_vector_db", func=self._search_vector, ...),
    Tool(name="search_vector_db_advanced", func=self._search_vector_advanced, ...)
]
self.agent = create_react_agent(self.llm, self.tools)
self.executor = AgentExecutor(agent=self.agent, tools=self.tools)

# 문제점:
# - 노드 안에 노드 구조 (복잡함)
# - LLM 호출 오버헤드
# - 디버깅 어려움
```

**Housing Agent (현재 방식 - SQL Agent 사용):**
```python
# ✅ 현재 방식: create_sql_agent 사용 (LangChain이 내부적으로 Tool 생성)
self.agent = create_sql_agent(
    llm=self.llm,
    db=self.db,
    agent_type=AgentType.OPENAI_FUNCTIONS
)

# create_sql_agent가 내부적으로 생성하는 Tool들:
# - list_tables: 테이블 목록 조회
# - schema_sql_db: 스키마 정보 확인  
# - query_sql_db: SQL 쿼리 실행
# - query_checker: SQL 쿼리 검증
# (직접 정의할 필요 없음)

# 차이점:
# - SQL Agent는 LangChain이 표준화된 Tool을 자동 생성
# - Loan Agent는 커스텀 Tool이 필요했지만, 이제는 순수 함수로 변경
```

**Loan Agent (현재 방식 - 순수 함수):**
```python
# ✅ 현재 방식: 순수 함수로 구현 (AgentExecutor 제거)
def search_loan_info(self, query: str) -> dict:
    # 직접 로직 실행 (AgentExecutor 없음)
    results = self._search_vector_basic(query)
    if not results:
        results = self._search_vector_advanced(query, metadata)
    return {"result": formatted, "results": results, ...}

# 장점:
# - 단순하고 빠름
# - 디버깅 쉬움
# - LangGraph 노드에서 호출하기 쉬움
```

**왜 Housing Agent는 SQL Agent를 사용하나?**
- SQL 쿼리 생성은 복잡함 (JOIN, WHERE, GROUP BY 등)
- LangChain의 `create_sql_agent`가 검증된 패턴 제공
- SQL 최적화와 에러 처리가 내장됨
- Loan Agent와 달리 LLM이 SQL을 생성해야 하는 필수 작업

**왜 Loan Agent는 순수 함수로 변경했나?**
- Vector 검색은 단순한 함수 호출
- 재검색 로직을 명확하게 제어 가능
- AgentExecutor 오버헤드 불필요
- LangGraph 노드에서 직접 호출하기 적합

### 코드 비율 분석

```
┌─────────────────────────────────────┐
│ 기존 RAG 함수 재사용:     90%  ✅  │
│ ├─ Retriever.search()              │
│ ├─ EmbeddingEncoder                │
│ ├─ KeywordReranker                 │
│ ├─ DocumentAugmenter               │
│ └─ OllamaGenerator                 │
├─────────────────────────────────────┤
│ 새로 작성 (재검색 로직):  10%  ✨  │
│ ├─ _generate_query_variants()      │
│ ├─ _deduplicate_results()          │
│ ├─ _rerank_by_original_query()     │
│ └─ LangGraph 노드 함수들           │
└─────────────────────────────────────┘
```

**Agent 패턴 선택 기준:**

| Agent | 패턴 | 이유 |
|-------|------|------|
| **Housing Agent** | SQL Agent (`create_sql_agent`) | SQL 생성이 복잡하고, LangChain의 검증된 패턴 활용 |
| **Loan Agent** | 순수 함수 | Vector 검색은 단순 함수 호출, AgentExecutor 불필요 |
| **RTMS Agent** | 순수 함수 | 계산 로직만 수행, Agent 불필요 |
| **Recommendation Agent** | 순수 함수 | 선별 로직만 수행, Agent 불필요 |

### Loan Agent 초기화 예시

```python
# hybrid_graph.py

from backend.services.rag.retrieval.retriever import Retriever  # ← 기존 import ✅
from backend.services.rag.models.config import EmbeddingModelType
from agents.loan_agent import LoanAgent

# 기존 Retriever 인스턴스 생성 ✅
retriever = Retriever(
    model_type=EmbeddingModelType.MULTILINGUAL_E5_BASE,
    db_config={
        'host': 'localhost',
        'port': '5432',
        'database': 'rey',
        'user': 'postgres',
        'password': 'post1234'
    }
)

# Loan Agent에 전달 (기존 Retriever 재사용) ✅
loan_agent = LoanAgent(retriever=retriever)

# 사용
result = loan_agent.search("청년 전세대출 조건")
```

---

## 폴더 구조

```
backend/services/rag/A_langgraph/
├── __init__.py
├── recommendation_graph.py      # Multi-Agent 추천 그래프
│
├── components/                  # 재사용 컴포넌트
│   ├── __init__.py
│   ├── state.py                # RecommendationState 정의
│   ├── nodes.py                # 공통 노드 함수들
│   └── tools.py                # Tool 정의들
│
├── agents/                      # 전문 에이전트들
│   ├── __init__.py
│   ├── housing_agent.py        # RDB 전문 (주택 데이터)
│   ├── loan_agent.py           # Vector + API (대출 정책)
│   ├── rtms_agent.py           # RDB 전문 (실거래가 데이터) - 현재 미구현
│   ├── recommendation_agent.py # 최종 추천 선별
│   └── feedback_agent.py       # 피드백 분석 및 반영 - Phase 2 구현 예정
│
└── utils/                       # 유틸리티
    ├── __init__.py
    ├── llm_factory.py          # LLM 초기화 및 싱글톤
    ├── schema_loader.py        # SQL 스키마 로더
    └── conversation_manager.py # 대화 히스토리 관리 (⚠️ Vector DB 도입 시 간소화 예정)
```

---

## 상세 구현

### 1. Housing Agent (RDB 전문)

```python
# agents/housing_agent.py

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.agents import AgentType
from langchain_openai import ChatOpenAI

class HousingAgent:
    """
    주택 데이터베이스 전문 에이전트

    담당:
    - housing.notices (주택 공고)
    - housing.units (호실 정보)

    Tool:
    - list_tables: 테이블 목록 조회
    - schema_sql_db: 스키마 정보 확인
    - query_sql_db: SQL 쿼리 실행
    - query_checker: SQL 쿼리 검증
    """

    def __init__(self, db_uri: str, schema_path: str):
        # PostgreSQL 연결
        self.db = SQLDatabase.from_uri(
            db_uri,
            include_tables=[
                "housing.notices",
                "housing.units"
            ]
            # sample_rows_in_table_info 제거: DB 연결되어 있으니 쿼리 실행 시 실제 결과를 받음
        )

        # 스키마 정보 로드
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema_info = f.read()

        # LLM 초기화
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # SQL Agent 생성
        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            prefix=self._get_system_prompt()
        )

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return f"""당신은 주택 데이터베이스 전문가입니다.

### 스키마 정보:
{self.schema_info}

### 역할:
- 사용자 질문을 분석하여 정확한 SQL 쿼리 작성
- JOIN, WHERE, GROUP BY 등을 적절히 활용
- 지역, 가격, 평수, 공급 유형 등으로 필터링
- 결과를 명확하게 요약

### 주의사항:
- 읽기 전용 쿼리만 실행 (SELECT만)
- NULL 값 처리 주의
- 한글 컬럼명 정확히 사용
"""

    def search(self, query: str) -> dict:
        """
        주택 데이터 검색

        Args:
            query: 사용자 질문

        Returns:
            {
                "agent": "housing",
                "query": str,
                "result": str,
                "source": "rdb",
                "sql_query": str (optional)
            }
        """
        result = self.agent.invoke({"input": query})

        return {
            "agent": "housing",
            "query": query,
            "result": result["output"],
            "source": "rdb"
        }
```

---

### 2. Loan Agent (Vector + 재검색 루프)

```python
# agents/loan_agent.py

from langchain_ollama import ChatOllama
from typing import List, Dict
import time

class LoanAgent:
    """
    대출 정책 전문 에이전트 (로직만 담당)
    
    설계 원칙:
    - AgentExecutor 제거: 순수 함수로 구현
    - LangGraph 노드에서 호출하기 쉽게 설계
    - 재검색 로직을 내부에 캡슐화

    담당:
    - 대출 정책 문서 검색 (Vector DB)
    - 재검색 루프 (Query Rewriting)
    - 대출 관련 정보 제공

    참고:
    - 현재는 Vector DB에서 대출 관련 정보만 제공
    - 실제 대출 가능 여부 확인은 나중에 기능 추가 시 고려
    """

    def __init__(self, retriever):
        self.retriever = retriever
        self.llm = ChatOllama(model="gemma3:4b", temperature=0)

    def search_loan_info(self, query: str) -> dict:
        """
        대출 관련 정보 검색 (재검색 루프 포함)
        
        순수 함수로 구현: AgentExecutor 없이 직접 로직 실행
        
        Args:
            query: 사용자 질문

        Returns:
            {
                "agent": "loan",
                "query": str,
                "result": str,  # 대출 관련 정보 (Vector DB 검색 결과)
                "results": List[Dict],  # 원본 검색 결과
                "search_path": List[str],  # 사용한 검색 단계 ("basic" 또는 ["basic", "advanced"])
                "execution_time_ms": float,
                "metadata": Dict  # 디버깅용 메타데이터
            }
        """
        start_time = time.time()
        search_path = []
        metadata = {
            "query_variants": [],
            "search_attempts": 0,
            "total_results_found": 0
        }
        
        # 1단계: 기본 검색 시도
        results = self._search_vector_basic(query)
        search_path.append("basic")
        metadata["search_attempts"] += 1
        
        if results:
            metadata["total_results_found"] = len(results)
            formatted = self._format_results(results)
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "agent": "loan",
                "query": query,
                "result": formatted,
                "results": results,
                "search_path": search_path,
                "execution_time_ms": execution_time,
                "metadata": metadata
            }
        
        # 2단계: 재검색 시도 (기본 검색 실패 시)
        advanced_results = self._search_vector_advanced(query, metadata)
        search_path.append("advanced")
        metadata["search_attempts"] += 1
        
        if advanced_results:
            metadata["total_results_found"] = len(advanced_results)
            formatted = self._format_results(advanced_results)
        else:
            formatted = f"""❌ 대출 관련 정보를 찾을 수 없습니다.

시도한 검색어:
{chr(10).join(f'- {v}' for v in metadata.get('query_variants', [query]))}

Vector DB에 해당 정보가 없을 가능성이 높습니다."""
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "agent": "loan",
            "query": query,
            "result": formatted,
            "results": advanced_results or [],
            "search_path": search_path,
            "execution_time_ms": execution_time,
            "metadata": metadata
        }

    def _search_vector_basic(self, query: str) -> List[Dict]:
        """1단계: 기본 Vector DB 검색"""
        results = self.retriever.search(
            query=query,
            top_k=5,
            min_similarity=0.5,
            use_reranker=True
        )
        return results

    def _search_vector_advanced(self, query: str, metadata: Dict) -> List[Dict]:
        """
        2단계: 쿼리 재작성 + 재검색

        현직 실전 패턴 (Query Rewriting):
        1. LLM으로 쿼리 변형 생성 (3가지)
        2. 모든 변형으로 검색
        3. 중복 제거
        4. 원본 쿼리로 리랭킹
        """

        # 1단계: 쿼리 변형 생성
        variants = self._generate_query_variants(query)

        # 2단계: 모든 변형으로 검색
        all_results = []
        for variant in variants:
            results = self.retriever.search(
                query=variant,
                top_k=3,
                min_similarity=0.4,  # 임계값 낮춤
                use_reranker=False   # 속도 우선
            )
            all_results.extend(results)

        if not all_results:
            return f"""❌ 재검색에도 결과가 없습니다.

시도한 검색어:
{chr(10).join(f'- {v}' for v in variants)}

Vector DB에 해당 정보가 없을 가능성이 높습니다."""

        # 3단계: 중복 제거
        unique_results = self._deduplicate_results(all_results)

        # 4단계: 원본 쿼리로 리랭킹
        reranked = self._rerank_by_original_query(query, unique_results)

        return f"""✅ 고급 검색 성공

시도한 검색어: {', '.join(variants)}
최종 결과: {len(reranked)}건

{self._format_results(reranked)}"""

    def _generate_query_variants(self, query: str, num_variants: int = 3) -> List[str]:
        """
        LLM으로 쿼리 변형 생성

        현직 팁:
        - Few-shot 예시 포함하면 품질 향상
        - 3-5개가 적당 (너무 많으면 느림)
        """

        prompt = f"""다음 질문을 {num_variants}가지 다른 방식으로 표현하세요.

원래 질문: {query}

규칙:
1. 각 줄에 하나씩, 번호 없이
2. 의미는 같지만 표현 다르게
3. 전문 용어 ↔ 일상 용어 변환
4. 축약어 풀어쓰기

예시:
입력: "청년 전세대출 금리"
출력:
청년 주거 자금 대출 이자율
만 34세 이하 전세자금 대출 금리
청년층 대상 전세 융자 금리

입력: {query}
출력:"""

        response = self.llm.invoke(prompt)

        # 파싱
        variants = [
            line.strip()
            for line in response.content.split('\n')
            if line.strip() and not line.strip().startswith(('입력:', '출력:', '#'))
        ][:num_variants]

        # 원본도 포함 (중요!)
        return [query] + variants

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        중복 제거

        현직 팁:
        - ID 기반 중복 제거 (가장 높은 점수만 유지)
        """

        # ID 기반 중복 제거 (더 높은 similarity 우선)
        unique = {}
        for result in results:
            doc_id = result['id']
            if doc_id not in unique or result.get('similarity', 0) > unique[doc_id].get('similarity', 0):
                unique[doc_id] = result

        return list(unique.values())

    def _rerank_by_original_query(self, original_query: str, results: List[Dict]) -> List[Dict]:
        """
        원본 쿼리로 리랭킹

        현직 팁:
        - 변형 쿼리로 찾았지만, 원본 쿼리와의 관련성으로 정렬
        """

        if not results:
            return []

        # Reranker가 있으면 사용
        if hasattr(self.retriever, 'reranker') and self.retriever.reranker:
            return self.retriever.reranker.rerank(original_query, results)

        # 없으면 similarity 기준 정렬
        return sorted(
            results,
            key=lambda x: x.get('similarity', 0),
            reverse=True
        )[:5]  # 상위 5개만

    def _format_results(self, results: List[Dict]) -> str:
        """검색 결과 포맷팅"""
        if not results:
            return "검색 결과가 없습니다."
            
        formatted = []
        for i, result in enumerate(results, 1):
            similarity = result.get('similarity', 0)
            content = result['content'][:500]  # 너무 길면 자르기

            formatted.append(f"""[문서 {i}] (유사도: {similarity:.2f})
{content}
{"..." if len(result['content']) > 500 else ""}
---""")

        return "\n\n".join(formatted)
```

---

#### Loan Agent 실행 예시

**예시 1: 기본 검색 성공**

```
질문: "청년 전세대출 조건은?"

Loan Agent 실행 (순수 함수):
┌────────────────────────────────────────┐
│ 1단계: 기본 검색 시도                  │
│   → retriever.search() 호출            │
│   → 결과: [문서 5건, 유사도 0.85+]     │
│                                        │
│ 반환:                                  │
│ {                                      │
│   "result": "청년 전세대출 조건은...", │
│   "search_path": ["basic"],            │
│   "execution_time_ms": 1200,           │
│   "metadata": {                        │
│     "search_attempts": 1,              │
│     "total_results_found": 5           │
│   }                                    │
│ }                                      │
└────────────────────────────────────────┘
```

**예시 2: 재검색 필요**

```
질문: "젊은이 집 얻을 때 돈 빌려주는 거"

Loan Agent 실행 (순수 함수):
┌────────────────────────────────────────────────┐
│ 1단계: 기본 검색 시도                          │
│   → retriever.search() 호출                   │
│   → 결과: [] (빈 결과)                        │
│                                                │
│ 2단계: 재검색 시도                             │
│   → _generate_query_variants() 호출           │
│   → 변형 쿼리: ["청년 전세대출",              │
│                "청년 주거자금",                │
│                "만 34세 이하 전세"]            │
│   → 각 변형으로 검색                           │
│   → 중복 제거 + 리랭킹                         │
│   → 결과: 3건                                 │
│                                                │
│ 반환:                                         │
│ {                                             │
│   "result": "청년 전세대출은...",             │
│   "search_path": ["basic", "advanced"],        │
│   "execution_time_ms": 2500,                  │
│   "metadata": {                               │
│     "search_attempts": 2,                     │
│     "total_results_found": 3,                 │
│     "query_variants": [...]                   │
│   }                                           │
│ }                                             │
└────────────────────────────────────────────────┘
```

**장점:**
- AgentExecutor 없이 순수 함수로 실행 → 빠르고 예측 가능
- 디버깅 정보가 명확함 (search_path, metadata)
- LangGraph 노드에서 호출하기 쉬움

---

### 3. Supervisor Agent (에이전트 조율)

```python
# agents/supervisor.py

from typing import List, Literal, Dict
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import concurrent.futures

class SupervisorAgent:
    """
    에이전트를 조율하는 Supervisor

    역할:
    - 사용자 질문 분석
    - 적절한 에이전트 선택 (housing, loan, both)
    - 에이전트 실행 조율
    - 결과 통합
    """

    def __init__(self, agents: Dict[str, any]):
        """
        Args:
            agents: {"housing": HousingAgent, "loan": LoanAgent}
        """
        self.agents = agents
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def route(self, query: str) -> Literal["housing", "loan", "both"]:
        """
        질문을 분석하여 적절한 에이전트 선택

        Args:
            query: 사용자 질문

        Returns:
            "housing" | "loan" | "both"
        """

        prompt = f"""다음 질문을 분석하여 어떤 에이전트에게 보낼지 결정하세요.

질문: {query}

선택지:
- housing: 주택 매물, 위치, 가격, 평수, 공급 유형 등 부동산 정보 질문
  예시: "서울 강남구 원룸", "3억 이하 매물", "청년주택 공고"

- loan: 대출 정책, 금리, 조건, 신청 방법 등 금융 정보 질문
  예시: "청년 전세대출 금리", "버팀목 대출 조건", "대출 신청 방법"

- both: 주택 정보와 대출 정보 모두 필요한 질문
  예시: "강남구에서 청년 전세대출 가능한 매물", "3억 이하 집과 대출 상품"

반드시 'housing', 'loan', 'both' 중 하나만 답변하세요."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        routing = response.content.strip().lower()

        # 검증
        if routing not in ["housing", "loan", "both"]:
            # 기본값: both
            routing = "both"

        return routing

    def execute(self, query: str) -> dict:
        """
        에이전트 실행 조율

        Args:
            query: 사용자 질문

        Returns:
            {
                "routing": str,
                "results": {
                    "housing": dict (optional),
                    "loan": dict (optional)
                },
                "execution_time_ms": float
            }
        """
        import time
        start_time = time.time()

        # 라우팅 결정
        routing = self.route(query)

        results = {}

        if routing == "housing":
            # Housing Agent만 실행
            results["housing"] = self.agents["housing"].search(query)

        elif routing == "loan":
            # Loan Agent만 실행
            results["loan"] = self.agents["loan"].search(query)

        elif routing == "both":
            # 병렬 실행으로 성능 최적화
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_housing = executor.submit(
                    self.agents["housing"].search, query
                )
                future_loan = executor.submit(
                    self.agents["loan"].search, query
                )

                results["housing"] = future_housing.result()
                results["loan"] = future_loan.result()

        execution_time = (time.time() - start_time) * 1000

        return {
            "routing": routing,
            "results": results,
            "execution_time_ms": execution_time
        }

    def format_results(self, supervisor_result: dict) -> str:
        """
        에이전트 실행 결과를 포맷팅

        Args:
            supervisor_result: execute() 반환값

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        formatted_parts = []

        results = supervisor_result["results"]

        if "housing" in results:
            housing_data = results["housing"]
            formatted_parts.append(f"""## 주택 데이터베이스 조회 결과

{housing_data['result']}

출처: RDB (housing schema)
""")

        if "loan" in results:
            loan_data = results["loan"]
            formatted_parts.append(f"""## 대출 정책 정보

{loan_data['result']}

출처: Vector DB + API
""")

        return "\n\n---\n\n".join(formatted_parts)
```

---

### 4. Multi-Agent 추천 Graph 통합

```python
# multi_agent_recommendation_graph.py

from typing import TypedDict, Optional, Dict, Any, List
import logging

from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from agents.housing_agent import HousingAgent
from agents.infra_agent import InfraAgent
from agents.loan_agent import LoanAgent
from agents.rtms_agent import RTMSAgent
from agents.scoring_agent import ScoringAgent
from agents.recommendation_agent import RecommendationAgent
# from agents.feedback_agent import FeedbackAgent  # 현재 미구현으로 주석처리

# State 정의
class RecommendationState(TypedDict):
    """추천 시스템 State"""
    # 사용자 입력
    user_request: str                    # 사용자 요청
    query_type: str                      # 질문 분류 ("housing", "finance", "general")
    conversation_history: List[Dict]    # 대화 히스토리
    user_feedback: Optional[Dict]       # 사용자 피드백
    
    # Agent 인스턴스 (그래프 빌드 시 주입)
    _agents: Dict[str, Any]             # {"housing": HousingAgent, "loan": LoanAgent, ...}
    
    # 추천 프로세스 (각 노드에서 업데이트)
    candidates: List[Dict]               # 초기 후보들 (housing_search_node에서 설정)
    housing_result: Optional[Dict]       # Housing Agent 원본 결과 (디버깅용)
    loan_info: str                       # 대출 관련 정보 문자열 (loan_search_node에서 설정)
    loan_results: List[Dict]             # 대출 검색 원본 결과 (디버깅용)
    loan_metadata: Dict[str, Any]       # Loan Agent 메타데이터 (디버깅용)
    # rtms_scores: Dict[str, float]       # 실거래가 점수 (rtms_search_node에서 설정) - 현재 미구현
    recommendations: List[Dict]          # 최종 추천 리스트
    
    # 나중에 확장 예정:
    # infra_scores: Dict[str, float]   # 인프라 점수 (PostGIS)
    # loan_eligibility: Dict[str, bool]  # 대출 가능 여부
    # final_scores: Dict[str, float]     # 종합 점수
    
    # 메타데이터 (디버깅 및 추적용)
    metadata: Dict[str, Any]            # 추적 정보
    # metadata 구조:
    # {
    #   "query_classification": {"query_type": "housing", "confidence": "llm", "llm_model": "ollama/gemma:3b"},
    #   "agent_execution": {
    #     "housing": {"execution_time_ms": 1200, "candidates_count": 50},
    #     "loan": {"execution_time_ms": 2500, "search_path": ["basic", "advanced"], ...}
    #     # "rtms": {"execution_time_ms": 800, "scores_count": 50}  # 현재 미구현
    #   },
    #   "general_llm": {...}  # general 질문의 경우
    # }
    iteration: int                      # 추천 반복 횟수


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


# ========================================
# 각 Agent를 독립 노드로 분리
# ========================================

def classify_query_node(state: RecommendationState) -> Dict[str, Any]:
    """
    질문 분류 노드 - LLM(Ollama Gemma 3 4b)으로 사용자 질문을 집/금융/그외로 분류
    
    Ollama의 gemma:3b 모델만 사용하여 분류합니다.
    
    Returns:
        query_type: housing / finance / general
        metadata: 분류 정보 포함
    """
    import time
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    start_time = time.time()
    try:
        user_request = state.get("user_request", "")

        system_prompt = (
            "너는 사용자의 질문이 어떤 카테고리인지 판별하는 시스템이야. "
            "아래 세 카테고리 중 하나로만 분류해서 한국어 또는 영어로 한 단어(housing, finance, general)만 반드시 출력해.\n"
            "1. housing: 주택(집, 매물, 원룸, 아파트, 임대, 전세, 월세 등)에 관한 질문\n"
            "2. finance: 금융/대출(대출, 금리, 청년, 전세대출, 주택담보대출 등)에 관한 질문\n"
            "3. general: 그 외의 모든 질문\n"
            "질문 예시:\n"
            "- '강남 전세 추천해줘' → housing\n"
            "- '청년 전세자금 대출 금리 알려줘' → finance\n"
            "- '오늘 날씨 어때?' → general\n"
            "다음 질문의 카테고리를 housing, finance, general 중 하나로만 답변해라.\n"
            "질문: '{question}'"
        ).format(question=user_request)

        llm = ChatOllama(
            model="gemma:3b",     # 반드시 Ollama gemma:3b만
            temperature=0
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"질문: {user_request}")
        ]

        response = llm.invoke(messages)
        llm_output = response.content.strip().lower()
        
        # 라벨 정제
        if "housing" in llm_output:
            query_type = "housing"
        elif "finance" in llm_output:
            query_type = "finance"
        elif "general" in llm_output:
            query_type = "general"
        else:
            query_type = "general"

        metadata = state.get("metadata", {})
        metadata["query_classification"] = {
            "query_type": query_type,
            "llm_output": llm_output,
            "original_query": user_request,
            "classification_time_ms": (time.time() - start_time) * 1000,
            "llm_model": "ollama/gemma:3b",
            "confidence": "llm"
        }

        logger.info(f"Ollama(gemma:3b) 기반 질문 분류: '{user_request}' -> {query_type} (LLM결과: {llm_output})")

        return {
            "query_type": query_type,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Ollama(gemma:3b) 기반 Query classification node 오류: {e}")

        metadata = state.get("metadata", {})
        metadata["query_classification"] = {
            "query_type": "general",
            "error": str(e),
            "classification_time_ms": (time.time() - start_time) * 1000,
            "llm_model": "ollama/gemma:3b",
            "confidence": "error"
        }

        return {
            "query_type": "general",
            "metadata": metadata
        }


def general_llm_node(state: RecommendationState) -> Dict[str, Any]:
    """
    일반 질문 LLM 답변 노드 - housing/finance와 관련없는 질문에 대한 직접 답변
    
    Ollama의 gemma:3b 모델을 사용하여 일반적인 질문에 답변합니다.
    
    Returns:
        final_answer: LLM의 답변
        metadata: 답변 생성 정보
    """
    import time
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    start_time = time.time()
    try:
        user_request = state.get("user_request", "")

        system_prompt = (
            "너는 도움이 되는 AI 어시스턴트야. "
            "사용자의 질문에 정확하고 친절하게 답변해줘. "
            "부동산이나 금융 관련 전문적인 질문이 아닌 일반적인 질문에 답변하고 있어. "
            "한국어로 자연스럽고 이해하기 쉽게 답변해줘."
        )

        llm = ChatOllama(
            model="gemma:3b",
            temperature=0.7  # 일반 답변은 조금 더 창의적으로
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request)
        ]

        response = llm.invoke(messages)
        llm_answer = response.content.strip()

        metadata = state.get("metadata", {})
        metadata["general_llm"] = {
            "model": "ollama/gemma:3b",
            "response_time_ms": (time.time() - start_time) * 1000,
            "original_query": user_request,
            "answer_length": len(llm_answer)
        }

        logger.info(f"일반 질문 LLM 답변 완료: '{user_request}' -> {len(llm_answer)}자 답변")

        return {
            "final_answer": llm_answer,
            "metadata": metadata,
            "iteration": state.get("iteration", 0)
        }

    except Exception as e:
        logger.error(f"일반 질문 LLM 노드 오류: {e}")
        
        metadata = state.get("metadata", {})
        metadata["general_llm"] = {
            "error": str(e),
            "response_time_ms": (time.time() - start_time) * 1000
        }

        return {
            "final_answer": "죄송합니다. 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.",
            "metadata": metadata,
            "iteration": state.get("iteration", 0)
        }


def housing_search_node(state: RecommendationState) -> Dict[str, Any]:
    """
    Housing Agent 노드 - 주택 매물 검색
    
    독립 노드로 분리하여 디버깅과 확장성 향상
    """
    start_time = time.time()
    
    try:
        # Agent 인스턴스는 그래프 빌드 시 주입 (의존성 주입)
        housing_agent = state.get("_agents", {}).get("housing")
        if not housing_agent:
            raise ValueError("HousingAgent가 state에 없습니다. 그래프 빌드 시 주입 필요")
        
        result = housing_agent.search(state["user_request"])
        
        # 메타데이터에 실행 정보 저장 (디버깅용)
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
        
        metadata["agent_execution"]["housing"] = {
            "execution_time_ms": (time.time() - start_time) * 1000,
            "candidates_count": len(result.get("candidates", [])),
            "success": "error" not in result
        }
        
        return {
            "candidates": result.get("candidates", []),
            "housing_result": result,  # 원본 결과도 저장 (디버깅용)
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Housing search node 실행 중 오류: {e}")
        
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
            
        metadata["agent_execution"]["housing"] = {
            "execution_time_ms": (time.time() - start_time) * 1000,
            "candidates_count": 0,
            "success": False,
            "error": str(e)
        }
        
        return {
            "candidates": [],
            "housing_result": None,
            "metadata": metadata
        }

def loan_search_node(state: RecommendationState) -> Dict[str, Any]:
    """
    Loan Agent 노드 - 대출 관련 정보 검색
    
    독립 노드로 분리하여 디버깅과 확장성 향상
    """
    start_time = time.time()
    
    try:
        loan_agent = state.get("_agents", {}).get("loan")
        if not loan_agent:
            raise ValueError("LoanAgent가 state에 없습니다. 그래프 빌드 시 주입 필요")
        
        result = loan_agent.search_loan_info(state["user_request"])
        
        # 메타데이터에 실행 정보 저장 (디버깅용)
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
        
        metadata["agent_execution"]["loan"] = {
            "execution_time_ms": result.get("execution_time_ms", 0),
            "search_path": result.get("search_path", []),
            "results_count": len(result.get("results", [])),
            "query_variants": result.get("metadata", {}).get("query_variants", []),
            "success": "error" not in result
        }
        
        return {
            "loan_info": result.get("result", ""),
            "loan_results": result.get("results", []),
            "loan_metadata": result.get("metadata", {}),
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Loan search node 실행 중 오류: {e}")
        
        metadata = state.get("metadata", {})
        if "agent_execution" not in metadata:
            metadata["agent_execution"] = {}
            
        metadata["agent_execution"]["loan"] = {
            "execution_time_ms": (time.time() - start_time) * 1000,
            "search_path": [],
            "results_count": 0,
            "success": False,
            "error": str(e)
        }
        
        return {
            "loan_info": f"대출 정보 검색 중 오류 발생: {str(e)}",
            "loan_results": [],
            "loan_metadata": {},
            "metadata": metadata
        }

# RTMS Agent는 현재 미구현으로 주석처리
# def rtms_search_node(state: RecommendationState) -> Dict[str, Any]:
#     """
#     RTMS Agent 노드 - 실거래가 점수 계산
#     
#     독립 노드로 분리하여 디버깅과 확장성 향상
#     """
#     start_time = time.time()
#     
#     rtms_agent = state.get("_agents", {}).get("rtms")
#     if not rtms_agent:
#         raise ValueError("RTMSAgent가 state에 없습니다. 그래프 빌드 시 주입 필요")
#     
#     # candidates가 있어야 점수 계산 가능
#     candidates = state.get("candidates", [])
#     if not candidates:
#         # candidates가 없으면 빈 점수 반환
#         return {"rtms_scores": {}}
#     
#     scores = rtms_agent.calculate_scores(candidates)
#     
#     # 메타데이터에 실행 정보 저장 (디버깅용)
#     metadata = state.get("metadata", {})
#     if "agent_execution" not in metadata:
#         metadata["agent_execution"] = {}
#     
#     metadata["agent_execution"]["rtms"] = {
#         "execution_time_ms": (time.time() - start_time) * 1000,
#         "scores_count": len(scores)
#     }
#     
#     return {"rtms_scores": scores}

# 나중에 확장 예정:
# def infra_search_node(state: RecommendationState) -> Dict[str, Any]:
#     """Infra Agent 노드 - 인프라 점수 계산 (PostGIS)"""
#     infra_agent = state.get("_agents", {}).get("infra")
#     candidates = state.get("candidates", [])
#     scores = infra_agent.calculate_scores(candidates)
#     return {"infra_scores": scores}

def generate_recommendations_node(state: RecommendationState) -> Dict[str, Any]:
    """
    최종 추천 생성 노드
    
    여러 Agent의 결과를 종합하여 최종 추천 리스트 생성
    """
    start_time = time.time()
    
    try:
        recommendation_agent = RecommendationAgent()
        
        # 현재는 종합 점수 없이 후보를 선별 (RTMS 점수는 미구현으로 제외)
        recommendations = recommendation_agent.select_top_n(
            candidates=state.get("candidates", []),
            # rtms_scores=state.get("rtms_scores", {}),  # 현재 미구현
            loan_info=state.get("loan_info", ""),
            top_n=10
        )
        
        # 추천 요약 생성
        summary = recommendation_agent.generate_summary(recommendations)
        
        # 메타데이터 업데이트
        metadata = state.get("metadata", {})
        metadata["recommendation_count"] = len(recommendations)
        metadata["recommendation_summary"] = summary
        metadata["generation_time_ms"] = (time.time() - start_time) * 1000
        
        # 반복 횟수 증가
        iteration = state.get("iteration", 0) + 1
        
        return {
            "recommendations": recommendations,
            "metadata": metadata,
            "iteration": iteration
        }
        
    except Exception as e:
        logger.error(f"Recommendation generation node 실행 중 오류: {e}")
        
        metadata = state.get("metadata", {})
        metadata["recommendation_count"] = 0
        metadata["generation_error"] = str(e)
        metadata["generation_time_ms"] = (time.time() - start_time) * 1000
        
        return {
            "recommendations": [],
            "metadata": metadata,
            "iteration": state.get("iteration", 0)
        }

# 피드백 에이전트는 현재 미구현으로 주석처리
# def process_feedback_node(state: RecommendationState) -> RecommendationState:
#     """4단계: 피드백 처리 및 재추천"""
#     if not state.get("user_feedback"):
#         return state  # 피드백 없으면 스킵
#     
#     feedback_agent = FeedbackAgent()
#     
#     # 피드백 분석
#     feedback_analysis = feedback_agent.analyze(
#         feedback=state["user_feedback"],
#         previous_recommendations=state.get("recommendations", []),
#         conversation_history=state.get("conversation_history", [])
#     )
#     
#     # 가중치 조정
#     state["metadata"]["feedback_weights"] = feedback_analysis["adjusted_weights"]
#     
#     # 재추천 필요 여부 확인
#     if feedback_analysis["needs_rerun"]:
#         # 다시 1단계부터 시작
#         state["iteration"] = state.get("iteration", 0) + 1
#         return state  # collect_candidates_node로 다시 라우팅
#     
#     return state

# 그래프 빌드
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
    
    # 조건부 라우팅 함수 정의
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
    
    # 분류 후 조건부 라우팅
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
    
    # 나중에 확장 예정:
    # workflow.add_node("infra_search", infra_search_node)
    # workflow.add_node("score", calculate_scores_node)
    # workflow.add_edge("housing_search", "infra_search")
    # workflow.add_edge("infra_search", "score")
    # workflow.add_edge("score", "recommend")
    
    # 피드백 루프는 현재 미구현으로 주석처리
    # def should_rerun(state: RecommendationState) -> str:
    #     if state.get("user_feedback") and state["metadata"].get("feedback_weights"):
    #         feedback_analysis = state["metadata"].get("feedback_analysis", {})
    #         if feedback_analysis.get("needs_rerun", False):
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
```

---

## 그래프 구조 및 디버깅

### 그래프 시각화

```
[START]
  ↓
[classify] → 질문 분류 (LLM)
  ├─→ [housing_search] → 주택 매물 검색 → [recommend] → [END]
  ├─→ [loan_search] → 대출 정보 검색 → [recommend] → [END]
  └─→ [general_llm] → 일반 질문 답변 → [END]
```

### 디버깅 정보 수집

각 노드는 실행 정보를 `metadata.agent_execution`에 저장합니다:

```python
result = graph.invoke({...})

# 디버깅 정보 확인
print(result["metadata"]["agent_execution"])
# {
#   "housing": {
#     "execution_time_ms": 1200,
#     "candidates_count": 50
#   },
#   "loan": {
#     "execution_time_ms": 2500,
#     "search_path": ["basic", "advanced"],
#     "results_count": 3,
#     "query_variants": ["청년 전세대출", "청년 주거자금", ...]
#   },
#   "rtms": {
#     "execution_time_ms": 800,
#     "scores_count": 50
#   }
# }
```

### 확장 방법

**새 Agent 추가 (예: Infra Agent):**

```python
# 1. Agent 클래스 구현
class InfraAgent:
    def calculate_scores(self, candidates):
        # PostGIS 로직
        pass

# 2. 노드 함수 추가
def infra_search_node(state: RecommendationState) -> RecommendationState:
    infra_agent = state.get("_agents", {}).get("infra")
    candidates = state.get("candidates", [])
    scores = infra_agent.calculate_scores(candidates)
    return {"infra_scores": scores}

# 3. 그래프에 노드 추가
workflow.add_node("infra_search", infra_search_node)
workflow.add_edge("housing_search", "infra_search")
workflow.add_edge("infra_search", "recommend")

# 4. State에 필드 추가
class RecommendationState(TypedDict):
    infra_scores: Dict[str, float]  # 추가
```

**새 단계 추가 (예: Scoring Agent):**

```python
# 1. 노드 함수 추가
def calculate_scores_node(state: RecommendationState) -> RecommendationState:
    scoring_agent = ScoringAgent()
    final_scores = scoring_agent.calculate(
        candidates=state["candidates"],
        infra_scores=state.get("infra_scores", {}),
        rtms_scores=state.get("rtms_scores", {})
    )
    return {"final_scores": final_scores}

# 2. 그래프에 노드 추가 (모든 검색 완료 후)
workflow.add_node("score", calculate_scores_node)
workflow.add_edge("infra_search", "score")  # 또는 조건부 라우팅
workflow.add_edge("score", "recommend")
```

---

## 실제 추천 시나리오

### 시나리오 1: 초기 추천 (다단계 추론)

```
사용자: "강남구 원룸 추천해줘"

[1단계: 초기 후보 수집]
├─ Housing Agent: 강남구 원룸 검색 → 50건
├─ Loan Agent: 대출 관련 정보 제공 (Vector DB)
└─ RTMS Agent: 실거래가와 비교 → 가격 적정성 점수

[2단계: 최종 추천]
└─ Recommendation Agent: 상위 10개 선별

결과: "강남구 원룸 추천 10건 제공"
실행 시간: ~2초

# 나중에 확장 예정:
# [1단계 추가] Infra Agent: 지하철역 거리 계산 (PostGIS) → 점수 부여
# [2단계 추가] Scoring Agent: 종합 점수 계산 (가중 평균)
```

### 시나리오 2: 대화형 추천 (피드백 반영)

```
턴 1: "강남구 원룸 추천해줘"
→ 초기 추천 10개 제공

턴 2: "너무 비싸" (피드백)
→ [피드백 분석 Agent]
   - 가격 가중치 증가
   - 가격 상위 후보 제외
→ [재추천] (1단계부터 재실행)
→ 가격 낮은 순 10개 재추천

턴 3: "대출 정보 알려줘" (질문)
→ [Loan Agent] 대출 관련 정보 검색 (Vector DB)
→ "청년 전세대출 조건은..." + 대출 정책 정보 제공

# 나중에 확장 예정:
# 턴 3: "지하철역 좀 더 가까운 거" (피드백)
# → [Infra Agent] 지하철역 거리 계산 (PostGIS)
# → [피드백 분석 Agent] 인프라 가중치 증가
# → [재추천] 지하철역 500m 이내 10개 재추천
#
# 턴 4: "이건 대출 가능해?" (질문)
# → [Loan Agent] 특정 매물 대출 가능 여부 확인
# → "네, 청년 전세대출 가능합니다" + 대출 조건 안내

실행 시간: ~2-4초 (피드백 반영 시)
```

### 시나리오 3: 복잡한 다단계 추론

```
사용자: "강남구에서 청년 전세대출 가능하고, 지하철역 500m 이내, 
         월세 50만원 이하인 원룸 추천해줘"

[1단계: 초기 후보 수집 (병렬)]
├─ Housing Agent: 강남구 원룸 검색 → 50건
├─ Loan Agent: 대출 관련 정보 제공 (Vector DB)
└─ RTMS Agent: 실거래가와 비교

[2단계: 필터링]
└─ Filter Agent: 월세 50만원 이하 → 15건

[3단계: 최종 추천]
└─ Recommendation Agent: 상위 10개 선별

# 나중에 확장 예정:
# [1단계 추가] Infra Agent: 지하철역 500m 이내 필터링 (PostGIS)
# [2단계 추가] Loan Agent: 청년 전세대출 가능 여부 확인 → 필터링
# [3단계 추가] Scoring Agent: 종합 점수 계산

결과: "조건에 맞는 원룸 10건 추천"
실행 시간: ~5초
```

### 시나리오 4: 사용자 피드백 실시간 반영

```
[초기 추천 10개]
→ 사용자 액션: [좋아요: 3번, 7번], [싫어요: 1번, 5번], [조회: 2번, 4번]

[피드백 분석 Agent]
→ 선호 패턴 추출:
   - 좋아요한 매물: 모두 월세 40만원 이하
   - 싫어요한 매물: 모두 월세 60만원 이상
   - 조회한 매물: 모두 지하철역 300m 이내

[가중치 조정]
→ 가격 가중치: 20% → 40%
→ 인프라 가중치: 30% → 35%
→ 기본 가중치: 50% → 25%

[재추천]
→ 조정된 가중치로 1단계부터 재실행
→ 피드백 반영된 10개 재추천

실행 시간: ~3초
```

---

## 구현 우선순위

### Phase 1: 기본 추천 구현 (2주) - 현재 진행 중
- [x] Housing Agent (agents/housing_agent.py) - 매물 검색
- [ ] Loan Agent (agents/loan_agent.py) - 대출 관련 정보 제공 (Vector DB)
- [ ] RTMS Agent (agents/rtms_agent.py) - 실거래가 점수 계산
- [ ] Recommendation Agent (agents/recommendation_agent.py) - 최종 선별

### Phase 1.5: 나중에 확장 예정
- [ ] Infra Agent (agents/infra_agent.py) - 인프라 점수 계산 (PostGIS)
- [ ] Loan Agent 확장 - 대출 가능 여부 확인 기능 추가
- [ ] Scoring Agent (agents/scoring_agent.py) - 종합 점수 계산

### Phase 2: 대화형 추천 (1주)
- [ ] State 정의 (components/state.py) - RecommendationState
- [ ] 대화 히스토리 관리 (utils/conversation_manager.py)
  - ⚠️ **향후 Vector DB 연동 계획**: 현재는 메모리 기반 임시 저장
  - **개선 예정**: Vector DB로 영구 저장 + 의미적 검색으로 개인화 추천 강화
- [ ] 피드백 수집 로직
- [ ] 추천 그래프 통합 (recommendation_graph.py)
- [ ] 테스트 및 디버깅

### Phase 3: 피드백 루프 (1주)
- [ ] Feedback Agent (agents/feedback_agent.py) - 피드백 분석
- [ ] 피드백 반영 로직
- [ ] 가중치 동적 조정
- [ ] 재추천 그래프 통합 (피드백 루프)

### Phase 4: 최적화 (1주)
- [ ] 캐싱 추가
- [ ] 성능 모니터링 (LangSmith)
- [ ] 에러 핸들링
- [ ] 피드백 루프 최적화

### Phase 5: Vector DB 연동 (향후 계획)

#### 🎯 목표: 대화 히스토리 영구 저장 및 개인화 추천 강화

**현재 상황:**
- `ConversationManager`: 메모리 기반 임시 저장 + 파일 저장
- 한계: 서버 재시작 시 데이터 손실, 사용자별 개인화 부족

**Vector DB 도입 후 개선사항:**

```python
# 현재: 메모리 기반
class ConversationManager:
    def __init__(self):
        self.conversations: List[Dict] = []  # 임시 저장
        
# 향후: Vector DB 연동
class HybridConversationManager:
    def __init__(self, vector_db, rdb):
        self.vector_db = vector_db      # 의미적 검색용
        self.rdb = rdb                  # 구조화된 저장용  
        self.session_cache = []         # 세션 중 빠른 접근
```

**주요 개선 효과:**
1. **개인화 추천**: 사용자별 선호도 벡터로 유사 사용자 패턴 분석
2. **의미적 검색**: "강남 원룸 선호" → 유사한 선호도 사용자 발견
3. **영구 저장**: 사용자 대화 기록 영구 보존
4. **트렌드 분석**: 전체 사용자 선호도 패턴 분석 가능

**구현 계획:**
- [ ] Vector DB 스키마 설계 (사용자 선호도 임베딩)
- [ ] RDB 스키마 설계 (구조화된 대화 기록)
- [ ] ConversationManager 리팩토링 (하이브리드 구조)
- [ ] 개인화 추천 알고리즘 개발
- [ ] 성능 최적화 (배치 처리 vs 실시간)

---

## 재검색 전략 요약 (Phase 1)

### Query Rewriting 패턴 ⭐

**현직에서 가장 많이 쓰는 방법**

```python
# 재검색 루프 플로우
[사용자 질문: "젊은이 집 빌리는 돈"]
    ↓
[1차 검색] search_vector_db
    → ❌ 결과 없음
    ↓
[2차 검색] search_vector_db_advanced
    → LLM이 쿼리 변형 생성:
      ["청년 전세대출", "청년 주거자금", "만 34세 이하 전세"]
    → 모든 변형으로 검색
    → 중복 제거
    → 원본 쿼리로 리랭킹
    → ✅ 결과 3건
```

### 성능 지표

| 지표             | 기본 검색 | 재검색 추가 |
|------------------|-----------|-------------|
| 검색 성공률      | 70%       | 90%+        |
| 평균 응답 시간   | 1초       | 2초         |
| 비용             | $0        | $0          |

### Phase 2 확장 계획

```python
# 3단계 Fallback 전략 (나중에 추가)
[1단계] search_vector_db           # 기본 검색
    ↓ 실패 시
[2단계] search_vector_db_advanced  # 재검색 (Phase 1) ✅
    ↓ 실패 시
[3단계] web_search_tavily          # 인터넷 검색 (Phase 2)
```

---

## 장단점 요약

### Multi-Agent 장점

✅ **전문화된 에이전트**
- Housing Agent: SQL 전문 (주택 데이터)
- Loan Agent: 정책 문서 검색 + 재검색 루프 전문 (Vector DB)
- 나중에 확장: Infra Agent (PostGIS 공간 쿼리), Loan Agent (대출 가능 여부 확인)

✅ **확장성**
- 새 도메인 추가 쉬움 (Infra Agent, RTMS Agent 등)

✅ **복잡한 질문 처리**
- 비교, 계산, 다단계 추론 가능
- 재검색 루프로 애매한 표현도 처리

✅ **디버깅 용이**
- 에이전트별 로그 분리
- 검색 경로 추적 (search_path)

### Multi-Agent 단점

❌ **복잡도 증가**
- 구현 및 유지보수 복잡

❌ **성능 오버헤드**
- Agent 추론 시간 추가 (~2초)

❌ **비용 증가**
- LLM 호출 횟수 증가

---

## 결론

### 왜 Multi-Agent 추천 시스템인가?

1. **대화형 추천 필수**
   - 사용자와 대화하며 선호도 파악
   - 피드백을 실시간 반영하여 추천 개선
   - 단순 쿼리로는 불가능

2. **복잡한 다단계 추론 필요**
   - 여러 데이터 소스를 단계적으로 통합
   - 필터링, 선별의 순차적 프로세스 (현재 단순화된 버전)
   - 나중에 확장: 점수 계산 단계 추가 예정
   - LangGraph가 상태 관리와 흐름 제어에 최적

3. **여러 데이터 소스 동적 통합**
   - 주택, 대출, 실거래가 등 실시간 통합 (현재)
   - 나중에 확장: 인프라 데이터 (PostGIS) 추가 예정
   - 각 Agent가 자신의 도메인에 특화
   - 병렬 실행으로 성능 최적화

4. **사용자 피드백 실시간 반영**
   - 피드백 루프를 통한 추천 개선
   - 가중치 동적 조정
   - LangGraph의 조건부 라우팅으로 구현

### 핵심 특징 요약

✅ **대화형 추천**: 사용자와 대화하며 선호도 파악
✅ **다단계 추론**: 초기 수집 → 선별 → 피드백 반영 (현재 단순화된 버전)
✅ **동적 통합**: 여러 데이터 소스를 실시간으로 통합
✅ **피드백 루프**: 사용자 피드백을 즉시 반영하여 추천 개선

**나중에 확장 예정:**
- 종합 점수 계산 단계 추가 (초기 수집 → 점수 계산 → 선별 → 피드백 반영)

### 단계적 개발

```
Phase 1: 기본 추천 구현 (2주) - 현재 진행 중
├─ Housing Agent (SQL 전문)
├─ Loan Agent (Vector + 재검색) - 대출 정보 제공만
├─ RTMS Agent (실거래가)
└─ Recommendation Agent (최종 선별)

Phase 1.5: 나중에 확장 예정
├─ Infra Agent (PostGIS 공간 쿼리)
├─ Loan Agent 확장 (대출 가능 여부 확인)
└─ Scoring Agent (종합 점수 계산)

Phase 2: 대화형 추천 (1주)
├─ 대화 히스토리 관리 (⚠️ Vector DB 연동 예정)
├─ 피드백 수집
└─ 피드백 분석 Agent

Phase 3: 피드백 루프 (1주)
├─ 피드백 반영 로직
├─ 가중치 동적 조정
└─ 재추천 그래프 통합

Phase 4: 최적화 (1주)
├─ 캐싱 추가
├─ 성능 모니터링
└─ 에러 핸들링
```

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [SQL Agent Toolkit](https://python.langchain.com/docs/integrations/toolkits/sql_database)
- [Query Rewriting 패턴 (Anthropic)](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/query-rewriting)
- 관련 문서:
  - [langgraph_node_analysis.md](langgraph_node_analysis.md)
  - [search_strategy_comparison.md](search_strategy_comparison.md)

---

**작성일**: 2025-10-31
**버전**: 4.0 (추천 시스템 전용)
**다음 단계**: Phase 1 기본 추천 구현 시작