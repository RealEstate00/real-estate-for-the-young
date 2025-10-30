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
import psycopg2
from sentence_transformers import SentenceTransformer
import json

from backend.services.llm.inha.langchain.retrievers.retriever import GroqHousingRetriever

logger = logging.getLogger(__name__)


# ============================================================================
# PostgreSQL pgvector 연결 설정
# ============================================================================

# 데이터베이스 연결 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'rey',
    'user': 'postgres',
    'password': 'post1234'
}

# 임베딩 모델 설정 (데이터베이스에 저장된 문서와 동일한 모델 사용)
EMBEDDING_MODEL = "jhgan/ko-sbert-nli"  # 768차원


def search_housing_regular(query: str, k: int = 5) -> List[Document]:
    """
    PostgreSQL에서 일반 주택 데이터 검색 (주택 추천용)
    
    Args:
        query: 검색 쿼리 (지역, 가격 등)
        k: 반환할 문서 개수
        
    Returns:
        검색된 주택 Document 리스트
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 주택 정보 조인 쿼리 (notices + units + addresses)
        search_sql = """
            SELECT DISTINCT
                n.notice_id,
                n.title,
                a.road_name_full,
                a.jibun_name_full,
                a.sgg_nm,
                a.emd_nm,
                u.deposit,
                u.rent,
                u.area_m2,
                u.floor,
                n.building_type,
                n.status,
                n.apply_end_at
            FROM housing.notices n
            LEFT JOIN housing.units u ON n.notice_id = u.notice_id
            LEFT JOIN housing.addresses a ON n.address_id = a.id
            WHERE n.status = 'open'
            AND (
                a.sgg_nm ILIKE %s OR 
                a.emd_nm ILIKE %s OR 
                n.title ILIKE %s OR
                a.road_name_full ILIKE %s
            )
            ORDER BY n.created_at DESC
            LIMIT %s
        """
        
        query_pattern = f"%{query}%"
        cur.execute(search_sql, (query_pattern, query_pattern, query_pattern, query_pattern, k))
        results = cur.fetchall()
        
        # 결과를 Document 객체로 변환
        documents = []
        for row in results:
            (notice_id, title, road_addr, jibun_addr, sgg_nm, emd_nm, 
             deposit, rent, area_m2, floor, building_type, status, apply_end_at) = row
            
            # 주소 정보 결합
            address = road_addr or jibun_addr or ""
            location = f"{sgg_nm} {emd_nm}".strip() if sgg_nm else ""
            
            # 가격 정보 정리
            price_info = ""
            if deposit is not None and deposit > 0:
                price_info += f"보증금: {deposit:,.0f}만원"
            if rent is not None and rent > 0:
                price_info += f", 월세: {rent:,.0f}만원"
            
            # Document 생성
            content = f"""
주택명: {title}
주소: {address}
지역: {location}
면적: {area_m2}㎡ (단위면적: {area_m2}㎡)
층수: {floor}
건물유형: {building_type}
가격정보: {price_info}
상태: {status}
            """.strip()
            
            doc = Document(
                page_content=content,
                metadata={
                    'notice_id': notice_id,
                    'title': title,
                    'address': address,
                    'location': location,
                    'deposit': deposit,
                    'rent': rent,
                    'area_m2': area_m2,
                    'floor': floor,
                    'building_type': building_type,
                    'status': status,
                    'source': 'housing_listings_db'
                }
            )
            documents.append(doc)
        
        conn.close()
        logger.info(f"PostgreSQL 주택 데이터 검색 완료: {len(documents)}개 주택")
        return documents
        
    except Exception as e:
        logger.error(f"PostgreSQL 주택 데이터 검색 실패: {e}")
        return []


def search_housing_pgvector(query: str, k: int = 5) -> List[Document]:
    """
    PostgreSQL pgvector를 사용한 주택 문서 검색
    
    Args:
        query: 사용자 검색 쿼리
        k: 반환할 문서 개수
        
    Returns:
        검색된 주택 Document 리스트
    """
    try:
        # 1. 임베딩 모델 로드
        model = SentenceTransformer(EMBEDDING_MODEL)
        
        # 2. 쿼리를 벡터로 변환
        query_embedding = model.encode(query).tolist()
        
        # 3. PostgreSQL 연결 및 검색
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 4. pgvector를 사용한 유사도 검색 쿼리
        search_sql = """
            SELECT id, content, metadata, 
                   1 - (embedding <=> %s::vector) as similarity
            FROM housing.housing_documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        
        cur.execute(search_sql, (query_embedding, query_embedding, k))
        results = cur.fetchall()
        
        # 5. 결과를 Document 객체로 변환
        documents = []
        for row in results:
            doc_id, content, metadata_json, similarity = row
            
            # metadata 파싱
            try:
                if isinstance(metadata_json, str):
                    metadata = json.loads(metadata_json)
                elif metadata_json is None:
                    metadata = {}
                else:
                    metadata = metadata_json
            except:
                metadata = {}
            
            # Document 생성
            doc = Document(
                page_content=content,
                metadata={
                    **metadata,
                    'id': doc_id,
                    'similarity': float(similarity),
                    'source': 'housing_pgvector_db'
                }
            )
            documents.append(doc)
        
        conn.close()
        logger.info(f"PostgreSQL pgvector 검색 완료: {len(documents)}개 문서")
        return documents
        
    except Exception as e:
        logger.error(f"PostgreSQL pgvector 검색 실패: {e}")
        return []


# ============================================================================
# 현재 사용 가능한 도구
# ============================================================================

@tool
def search_housing_listings(
    query: str,
    search_mode: Literal["diverse", "comprehensive"] = "diverse",
    max_results: int = None
) -> List[Document]:
    """
    주택 매물 검색 도구 - PostgreSQL에서 실제 주택 매물 정보 검색
    주택 추천, 매물 검색, 지역별 주택 찾기 등에 사용

    Args:
        query: 검색 쿼리 (예: "강남구", "청년주택", "50만원 이하")
        search_mode: 검색 모드
            - "diverse": 상위 결과 탐색 (기본 5개)
            - "comprehensive": 조건에 맞는 모든 결과 (기본 20개)
        max_results: 최대 결과 수

    Returns:
        검색된 주택 매물 Document 리스트
    """
    try:
        logger.info(f"search_housing_listings called: query='{query}', mode={search_mode}, max={max_results}")

        # 검색 결과 수 결정
        if search_mode == "comprehensive":
            k = max_results or 20
        else:
            k = max_results or 5

        # PostgreSQL에서 일반 주택 데이터 검색
        results = search_housing_regular(query, k)
        logger.info(f"search_housing_listings returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"search_housing_listings failed: {e}")
        return []


@tool
def search_housing_qa(
    query: str,
    max_results: int = 5
) -> List[Document]:
    """
    주택 Q&A 및 정책 질문 검색 도구 - PostgreSQL pgvector를 사용한 의미적 검색
    주택 정책, 제도, 자격요건, 신청방법 등에 대한 질문에 사용

    Args:
        query: 질문 (예: "신혼부부 임차보증금 이자지원 신청방법", "청년 주택 대출 조건")
        max_results: 최대 결과 수 (기본 5개)

    Returns:
        검색된 정책/Q&A Document 리스트 (유사도 높은 순 정렬)
    """
    try:
        logger.info(f"search_housing_qa called: query='{query}', max={max_results}")

        # PostgreSQL pgvector를 사용한 의미적 검색
        results = search_housing_pgvector(query, max_results)
        logger.info(f"search_housing_qa returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"search_housing_qa failed: {e}")
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
