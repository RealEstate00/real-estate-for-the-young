"""
LCEL Chain 기반 주택 추천 RAG 시스템
Agent 없이 단순 파이프라인으로 구현

구성:
1. Retriever: ChromaDB에서 주택 검색
2. Prompt: 검색 결과를 포맷팅하여 LLM에 전달
3. LLM: Groq llama-3.3-70b-versatile 모델
4. Output Parser: 문자열 파싱
"""

import sys
from pathlib import Path
import time

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from backend.services.llm.models.llm import llm
from backend.services.llm.prompts.prompt import rag_prompt
from backend.services.llm.langchain.retrievers.retriever import GroqHousingRetriever

import logging
logger = logging.getLogger(__name__)

# =============================================================================
# 1. 컴포넌트 초기화
# =============================================================================

# Retriever 생성 (k=5개 결과, 유사도 높은 순)
retriever = GroqHousingRetriever(k=5)

# Output Parser
output_parser = StrOutputParser()


# =============================================================================
# 2. 유틸리티 함수
# =============================================================================

def format_documents(docs):
    """검색된 문서를 LLM이 읽기 좋은 형태로 포맷팅"""
    if not docs:
        return "검색 결과가 없습니다."
    
    formatted = []
    for i, doc in enumerate(docs, 1):
        metadata = doc.metadata
        housing_name = metadata.get('주택명', 'N/A')
        address = metadata.get('도로명주소', metadata.get('지번주소', 'N/A'))
        district = metadata.get('시군구', 'N/A')
        dong = metadata.get('동명', 'N/A')
        tags = metadata.get('태그', metadata.get('theme', 'N/A'))
        similarity = metadata.get('similarity', 0)
        
        formatted.append(f"""
{i}. {housing_name}
   - 주소: {address}
   - 지역: {district} {dong}
   - 특성: {tags}
   - 유사도: {similarity:.2f}
        """.strip())
    
    return "\n\n".join(formatted)


def retrieve_and_format(query: str) -> str:
    """쿼리로 검색하고 결과를 포맷팅"""
    try:
        # Retriever 호출
        docs = retriever.invoke(query)
        
        # 검색된 문서 포맷팅
        formatted_context = format_documents(docs)
        
        logger.info(f"Retrieved {len(docs)} documents for query: '{query}'")
        return formatted_context
        
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return f"검색 중 오류 발생: {e}"


# =============================================================================
# 3. LCEL Chain 정의 (파이프라인)
# =============================================================================

# 메인 RAG Chain
rag_chain = (
    {
        "context": RunnableLambda(retrieve_and_format),  # 검색 & 포맷팅
        "query": RunnablePassthrough()                   # 쿼리 그대로 전달
    }
    | rag_prompt      # 프롬프트 템플릿
    | llm             # LLM 모델
    | output_parser   # 출력 파싱
)


# =============================================================================
# 4. 편의 함수
# =============================================================================

def recommend_housing(query: str, memory=None) -> str:
    """주택 추천 실행
    
    Args:
        query: 사용자 질문
        memory: ConversationSummaryBufferMemory 객체 (대화 맥락 관리)
    """
    try:
        logger.info(f"Housing recommendation for: '{query}'")
        response = rag_chain.invoke(query)
        
        # 메모리에 대화 저장
        if memory:
            memory.save_context({"input": query}, {"output": response})
            logger.info("Conversation saved to memory")
        
        return response
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        return f"죄송합니다. 추천 중 오류가 발생했습니다: {e}"


def stream_recommendation(query: str, memory=None):
    """스트리밍 주택 추천
    
    Args:
        query: 사용자 질문
        memory: ConversationSummaryBufferMemory 객체 (대화 맥락 관리)
    """
    try:
        logger.info(f"Streaming recommendation for: '{query}'")
        
        # 스트리밍 응답을 모아서 메모리에 저장하기 위해
        full_response = ""
        
        for chunk in rag_chain.stream(query):
            full_response += chunk
            yield chunk
        
        # 메모리에 대화 저장
        if memory:
            memory.save_context({"input": query}, {"output": full_response})
            logger.info("Conversation saved to memory")
            
    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        yield f"오류: {e}"


# =============================================================================
# 5. 테스트 코드
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("LCEL Chain 기반 주택 추천 RAG 시스템 - 스트리밍 테스트")
    print("=" * 80)
    
    # 테스트 쿼리들
    test_queries = [
        # "강남구 청년주택 추천해줘",
        # "서초구에 있는 주택 보여줘",
        "대치동 근처 좋은 주택 찾아줘"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n\n💬 테스트 {i}: {query}")
        print("-" * 80)
        
        try:
            # 스트리밍 추천
            for chunk in stream_recommendation(query):
                print(chunk, end="", flush=True)
                time.sleep(0.03)
            
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
        
        print("\n" + "-" * 80)
    
    print("\n✅ 모든 테스트 완료!")

