# LangGraph 노드 분석: 현재 구현 상태

## 📊 현재 구현된 노드들

### ✅ 완전히 구현된 노드

#### 1. **Query Embedding Node**

- **위치**: `models/encoder.py` → `encode_query()`
- **기능**: 쿼리 텍스트를 벡터 임베딩으로 변환
- **상태**: ✅ 완료
- **LangGraph 변환**: 즉시 사용 가능

```python
def query_embedding_node(state):
    query = state["query"]
    embedding = encoder.encode_query(query)
    return {"query_embedding": embedding}
```

#### 2. **Retrieval Node (Vector Search)**

- **위치**: `retrieval/retriever.py` → `Retriever.search()`
- **기능**: 벡터 데이터베이스에서 유사 문서 검색
- **상태**: ✅ 완료 (pgvector 사용)
- **LangGraph 변환**: 즉시 사용 가능

```python
def retrieval_node(state):
    query_embedding = state["query_embedding"]
    results = vector_store.search_similar(
        query_embedding=query_embedding,
        top_k=state.get("top_k", 5)
    )
    return {"retrieved_documents": results}
```

#### 3. **Reranking Node**

- **위치**: `retrieval/reranker.py` → `KeywordReranker.rerank()`
- **기능**: LLM 기반 키워드 추출 후 검색 결과 리랭킹
- **상태**: ✅ 완료 (LLM 키워드 추출 포함)
- **LangGraph 변환**: 즉시 사용 가능

```python
def reranking_node(state):
    query = state["query"]
    candidates = state["retrieved_documents"]
    reranker = KeywordReranker()
    reranked = reranker.rerank(query, candidates, top_k=5)
    return {"reranked_documents": reranked}
```

#### 4. **Augmentation Node**

- **위치**: `augmentation/augmenter.py` → `DocumentAugmenter.augment()`
- **기능**: 검색 결과를 LLM용 컨텍스트로 포맷팅
- **상태**: ✅ 완료 (EnhancedPromptFormatter 지원)
- **LangGraph 변환**: 즉시 사용 가능

```python
def augmentation_node(state):
    query = state["query"]
    documents = state.get("reranked_documents") or state["retrieved_documents"]
    formatter = EnhancedPromptFormatter()
    context = formatter.format_documents(query, documents)
    return {"augmented_context": context}
```

#### 5. **Generation Node**

- **위치**: `generation/generator.py` → `OllamaGenerator.generate()`
- **기능**: LLM으로 최종 답변 생성
- **상태**: ✅ 완료 (Ollama 연동)
- **LangGraph 변환**: 즉시 사용 가능

```python
def generation_node(state):
    query = state["query"]
    context = state["augmented_context"]
    generator = OllamaGenerator()
    answer = generator.generate(query, context)
    return {"final_answer": answer}
```

### 🔄 현재 구조의 LangGraph 매핑

```
현재 순차 구조 (rag_system.py):
─────────────────────────────────
generate_answer()
  ├─ retrieve_and_augment()
  │   ├─ retriever.search()       → Retrieval Node
  │   │   ├─ encoder.encode_query() → Query Embedding Node
  │   │   └─ reranker.rerank()      → Reranking Node (조건부)
  │   └─ augmenter.augment()        → Augmentation Node
  └─ generator.generate()            → Generation Node

LangGraph 구조로 변환 시:
─────────────────────────────────
State: {
  "query": str,
  "query_embedding": List[float],
  "retrieved_documents": List[Dict],
  "reranked_documents": List[Dict],
  "augmented_context": str,
  "final_answer": str,
  "metadata": Dict
}

Graph:
  START → QueryEmbedding → Retrieval → [조건부] Reranking → Augmentation → Generation → END
```

## ⚠️ LangGraph 전환 시 추가 필요한 부분

### 1. **State 관리 구조화**

- **현재**: `RAGResponse` dataclass로 관리
- **필요**: LangGraph의 StateGraph에 맞는 구조화된 State 정의

### 2. **조건부 라우팅 (Conditional Edges)**

- **현재**: `use_reranker` 플래그로 조건부 실행
- **LangGraph**: 명시적인 conditional edge 필요

```python
def should_rerank(state):
    return state.get("use_reranker", False)

# 그래프에서
graph.add_conditional_edges(
    "retrieval",
    should_rerank,
    {
        True: "reranking",
        False: "augmentation"
    }
)
```

### 3. **에러 처리 노드**

- **현재**: try-except로 처리
- **LangGraph**: 에러 전용 노드 추가 권장

### 4. **인간 피드백 루프 (Human-in-the-loop)**

- **현재**: ❌ 미구현
- **LangGraph**: 필요한 경우 `interrupt_before()` 사용 가능

### 5. **멀티 에이전트 체인**

- **현재**: 단일 파이프라인만 지원
- **LangGraph**: 필요시 여러 에이전트 체인 구성 가능

### 6. **재검색 루프 (Re-search Loop)**

- **현재**: ❌ 미구현
- **LangGraph**: 답변 품질이 낮을 때 재검색하는 루프 추가 가능

## 📈 구현 완성도

| 노드              | 구현 상태 | LangGraph 전환 난이도 |
| ----------------- | --------- | --------------------- |
| Query Embedding   | ✅ 100%   | 🟢 매우 쉬움          |
| Retrieval         | ✅ 100%   | 🟢 매우 쉬움          |
| Reranking         | ✅ 100%   | 🟢 매우 쉬움          |
| Augmentation      | ✅ 100%   | 🟢 매우 쉬움          |
| Generation        | ✅ 100%   | 🟢 매우 쉬움          |
| State 관리        | 🟡 70%    | 🟡 보통               |
| 조건부 라우팅     | 🟡 70%    | 🟡 보통               |
| 에러 처리         | 🟡 60%    | 🟡 보통               |
| 재검색 루프       | ❌ 0%     | 🟠 어려움             |
| Human-in-the-loop | ❌ 0%     | 🟠 어려움             |

## 🎯 결론

### ✅ **거의 다 구현되어 있음 (약 85%)**

**핵심 노드들은 모두 구현 완료:**

- 모든 주요 RAG 파이프라인 노드 (5개) 구현됨
- 각 노드는 독립적인 함수로 잘 분리됨
- 상태 관리가 `RAGResponse`로 구조화됨

**LangGraph 전환 시 필요한 작업:**

1. State를 LangGraph 형식으로 재정의 (30분)
2. 조건부 라우팅 명시화 (1시간)
3. 그래프 구조 정의 및 연결 (1시간)
4. 테스트 및 검증 (1시간)

**총 예상 시간: 약 3-4시간**

### 🚀 LangGraph 전환의 이점

1. **시각화**: 파이프라인을 그래프로 시각화 가능
2. **디버깅**: 각 노드의 입력/출력 추적 용이
3. **유연성**: 동적 라우팅, 루프, 병렬 처리 지원
4. **모니터링**: 각 노드의 실행 시간, 성공률 추적
5. **확장성**: 새로운 노드 추가가 쉽고 구조화됨

## 📝 LangGraph 변환 예시 코드

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class RAGState(TypedDict):
    query: str
    query_embedding: Annotated[list, operator.add]
    retrieved_documents: list
    reranked_documents: list
    augmented_context: str
    final_answer: str
    metadata: dict

def query_embedding_node(state: RAGState):
    embedding = encoder.encode_query(state["query"])
    return {"query_embedding": embedding}

def retrieval_node(state: RAGState):
    results = retriever.search(
        query_embedding=state["query_embedding"],
        top_k=5
    )
    return {"retrieved_documents": results}

def should_rerank(state: RAGState):
    return state.get("metadata", {}).get("use_reranker", True)

def reranking_node(state: RAGState):
    reranked = reranker.rerank(
        state["query"],
        state["retrieved_documents"]
    )
    return {"reranked_documents": reranked}

def augmentation_node(state: RAGState):
    docs = state.get("reranked_documents") or state["retrieved_documents"]
    context = augmenter.augment(state["query"], docs)
    return {"augmented_context": context.context_text}

def generation_node(state: RAGState):
    answer = generator.generate(
        state["query"],
        state["augmented_context"]
    )
    return {"final_answer": answer.answer}

# 그래프 구성
graph = StateGraph(RAGState)
graph.add_node("query_embedding", query_embedding_node)
graph.add_node("retrieval", retrieval_node)
graph.add_node("reranking", reranking_node)
graph.add_node("augmentation", augmentation_node)
graph.add_node("generation", generation_node)

# 엣지 연결
graph.set_entry_point("query_embedding")
graph.add_edge("query_embedding", "retrieval")
graph.add_conditional_edges(
    "retrieval",
    should_rerank,
    {
        True: "reranking",
        False: "augmentation"
    }
)
graph.add_edge("reranking", "augmentation")
graph.add_edge("augmentation", "generation")
graph.add_edge("generation", END)

# 컴파일
app = graph.compile()
```
