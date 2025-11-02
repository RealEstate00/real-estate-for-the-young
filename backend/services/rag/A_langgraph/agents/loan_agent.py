"""
Loan Agent - 대출 정책 전문 에이전트

순수 함수로 구현하여 Vector DB에서 대출 관련 정보를 검색합니다.
재검색 루프(Query Rewriting)를 통해 검색 성공률을 높입니다.
"""

from typing import Dict, List, Optional
from langchain_ollama import ChatOllama
import time
import logging

logger = logging.getLogger(__name__)


class LoanAgent:
    """
    대출 정책 전문 에이전트 (순수 함수 기반)
    
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
        """
        Args:
            retriever: 기존 Retriever 인스턴스 (Vector DB 검색용)
        """
        self.retriever = retriever
        self.llm = ChatOllama(model="gemma3:4b", temperature=0)

    def search_loan_info(self, query: str) -> Dict:
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
        
        try:
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
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Loan Agent 실행 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            
            return {
                "agent": "loan",
                "query": query,
                "result": error_msg,
                "results": [],
                "search_path": search_path,
                "execution_time_ms": execution_time,
                "metadata": metadata,
                "error": str(e)
            }

    def _search_vector_basic(self, query: str) -> List[Dict]:
        """1단계: 기본 Vector DB 검색"""
        try:
            results = self.retriever.search(
                query=query,
                top_k=5,
                min_similarity=0.5,
                use_reranker=True
            )
            return results
        except Exception as e:
            logger.error(f"기본 검색 실패: {e}")
            return []

    def _search_vector_advanced(self, query: str, metadata: Dict) -> List[Dict]:
        """
        2단계: 쿼리 재작성 + 재검색

        현직 실전 패턴 (Query Rewriting):
        1. LLM으로 쿼리 변형 생성 (3가지)
        2. 모든 변형으로 검색
        3. 중복 제거
        4. 원본 쿼리로 리랭킹
        """
        try:
            # 1단계: 쿼리 변형 생성
            variants = self._generate_query_variants(query)
            metadata["query_variants"] = variants

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
                return []

            # 3단계: 중복 제거
            unique_results = self._deduplicate_results(all_results)

            # 4단계: 원본 쿼리로 리랭킹
            reranked = self._rerank_by_original_query(query, unique_results)

            return reranked
            
        except Exception as e:
            logger.error(f"고급 검색 실패: {e}")
            return []

    def _generate_query_variants(self, query: str, num_variants: int = 3) -> List[str]:
        """
        LLM으로 쿼리 변형 생성

        현직 팁:
        - Few-shot 예시 포함하면 품질 향상
        - 3-5개가 적당 (너무 많으면 느림)
        """
        try:
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
            
        except Exception as e:
            logger.error(f"쿼리 변형 생성 실패: {e}")
            return [query]  # 원본만 반환

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        중복 제거

        현직 팁:
        - ID 기반 중복 제거 (가장 높은 점수만 유지)
        """
        # ID 기반 중복 제거 (더 높은 similarity 우선)
        unique = {}
        for result in results:
            doc_id = result.get('id', str(hash(result.get('content', ''))))
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

        try:
            # Reranker가 있으면 사용
            if hasattr(self.retriever, 'reranker') and self.retriever.reranker:
                return self.retriever.reranker.rerank(original_query, results)
        except Exception as e:
            logger.error(f"리랭킹 실패: {e}")

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
            content = result.get('content', '')[:500]  # 너무 길면 자르기

            formatted.append(f"""[문서 {i}] (유사도: {similarity:.2f})
{content}
{"..." if len(result.get('content', '')) > 500 else ""}
---""")

        return "\n\n".join(formatted)
