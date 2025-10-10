"""
주택 검색 도구 모음
LangChain Agent가 사용할 수 있는 모든 도구 정의
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.tools import tool
from langchain_core.documents import Document
from typing import List, Literal
import logging

from backend.services.llm.langchain.retrievers.inha.retriever_inha import GroqHousingRetriever

logger = logging.getLogger(__name__)


# ============================================================================
# 현재 사용 가능한 도구
# ============================================================================

@tool
def search_housing(   ## Retriever 역할의 도구
    query: str,
    search_mode: Literal["diverse", "comprehensive"] = "diverse",
    max_results: int = None
) -> List[Document]:
    """
    주택 검색 도구 - LLM이 사용자 의도에 따라 자동으로 검색 모드 선택

    Args:
        query: 검색 쿼리 (예: "강남구 청년주택", "지하철역 근처 주택")
        search_mode: 검색 모드
            - "diverse": 상위 결과 탐색 (기본, 유사도 높은 순)
                사용 예: "추천해줘", "좋은 곳 알려줘", "어떤게 있어?"
            - "comprehensive": 조건에 맞는 모든 결과 (유사도 높은 순)
                사용 예: "모두 보여줘", "전부 찾아줘", "모든 매물"
        max_results: 최대 결과 수 (None이면 모드에 따라 자동 설정)
            - diverse 모드: 기본 5개
            - comprehensive 모드: 기본 20개

    Returns:
        검색된 주택 Document 리스트 (유사도 높은 순 정렬)
    """
    try:
        logger.info(f"search_housing called: query='{query}', mode={search_mode}, max={max_results}")

        if search_mode == "comprehensive":
            # 조건에 맞는 모든 결과 검색 (유사도 높은 순)
            retriever = GroqHousingRetriever(
                k=max_results or 20,
                use_mmr=False,
                min_similarity=0.1
            )
        else:
            # 상위 결과 탐색 (유사도 높은 순, 기본)
            retriever = GroqHousingRetriever(
                k=max_results or 5,
                use_mmr=False,
                min_similarity=0.1
            )

        results = retriever.get_relevant_documents(query)
        logger.info(f"search_housing returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"search_housing failed: {e}")
        return []


# ============================================================================
# 향후 추가 예정 도구들 (비활성화 상태)
# ============================================================================

"""
@tool
def calculate_commute_time(start_address: str, housing_address: str) -> int:
    '''
    KakaoMap API로 통근시간 계산 (분 단위)

    Args:
        start_address: 출발지 주소 (회사, 학교 등)
        housing_address: 주택 주소

    Returns:
        통근시간 (분)
    '''
    # TODO: KakaoMap API 연동
    # 1. 주소를 좌표로 변환
    # 2. 경로 검색 (대중교통)
    # 3. 소요 시간 반환
    pass


@tool
def filter_by_commute(housings: List[Document], max_minutes: int) -> List[Document]:
    '''
    통근시간으로 주택 필터링

    Args:
        housings: 주택 Document 리스트
        max_minutes: 최대 통근시간 (분)

    Returns:
        필터링된 주택 리스트
    '''
    # TODO: 구현
    # 각 주택별 통근시간 계산 후 max_minutes 이하만 반환
    pass


@tool
def get_area_info(district: str) -> dict:
    '''
    지역 정보 조회 (인구, 평균 연령, 편의시설 등)

    Args:
        district: 지역명 (예: "강남구", "서초구")

    Returns:
        지역 정보 딕셔너리
    '''
    # TODO: 공공 API 연동
    pass


@tool
def compare_housing(housing_ids: List[str]) -> str:
    '''
    여러 주택 비교

    Args:
        housing_ids: 비교할 주택 ID 리스트

    Returns:
        비교 결과 텍스트
    '''
    # TODO: 구현
    # 위치, 가격, 편의시설 등 항목별 비교표 생성
    pass
"""
