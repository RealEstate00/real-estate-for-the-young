"""
도구 정의

RDB 검색 및 벡터 검색 도구
"""

import re
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.tools import tool


# ========== LLM 설정 ==========
load_dotenv()  # .env 파일 로드

llm_openai = ChatOpenAI(
    model="gpt-5-nano",
    reasoning_effort="high",        # 논리성 강화
)

llm_ollama = OllamaLLM(
    model="gemma3:4b",
    reasoning_effort="high",
)

llm = llm_openai
# ========== 스키마 정보 ==========
# 핵심 스키마 정보 - 지역 검색에 최적화
filtered_schema_info = '''

# ========== 주요 테이블 및 검색 가이드 ==========

## 지역별 주택 검색 방법:
1. 강서구, 송파구 등 구 단위 검색: addresses.sgg_nm 컬럼 사용
2. 동 단위 검색: addresses.emd_nm, emd_cd 컬럼 사용
3. 주소 검색: addresses.address_raw 컬럼 사용

## 테이블 관계:
- notices (주택공고) ← JOIN → addresses (주소정보) 
- notices ← JOIN → units (호실정보)

# ========== HOUSING 스키마 ==========
housing_tables = {
    "housing.addresses": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "address_ext_id": "address_ext_id - ID/식별자",
            "address_raw": "address_raw - 주소",
            "ctpv_nm": "ctpv_nm - 이름",
            "sgg_nm": "sgg_nm - 이름",
            "emd_nm": "emd_nm - 이름",
            "emd_cd": "emd_cd - 법정동 코드 - FK → housing.code_master.cd",
            "building_main_no": "building_main_no - 건물 주번호",
            "building_sub_no": "building_sub_no - 건물 서브번호",
            "building_name": "building_name - 건물이름",
            "road_name_full": "road_name_full - 도로명주소",
            "jibun_name_full": "jibun_name_full - 지번주소",
            "latitude": "latitude - 위도",
            "longitude": "longitude - 경도",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
    "housing.code_master": {
        "columns": {
            "cd": "cd - PK, 고유 식별자",
            "name": "name - 이름",
            "description": "description - 설명",
            "upper_cd": "upper_cd - FK → housing.code_master.cd",
        },
    },
    "housing.notice_tags": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "notice_id": "notice_id - FK → housing.notices.notice_id",
            "tag_type": "tag_type - FK → housing.code_master.cd",
            "tag_value": "tag_value - 태그",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
    "housing.notices": {
        "columns": {
            "notice_id": "notice_id - 공고번호 - PK, 고유 식별자",
            "platform_code": "platform_code - 플랫폼 코드 - FK → housing.platforms.code",
            "title": "title - 건물명 - housing.addresses 테이블의 building_name 의미",
            "status": "status - 공고 상태",
            "address_raw": "address_raw - 주소",
            "address_id": "address_id - 주소 ID - FK → housing.addresses.id",
            "building_type": "building_type - 건물 타입 - FK → housing.code_master.cd",
            "notice_extra": "notice_extra - 공고 추가 정보 (JSONB)",
            "has_images": "has_images - 이미지 여부 (BOOLEAN)",
            "has_floorplan": "has_floorplan - 층 계획서 여부 (BOOLEAN)",
            "has_documents": "has_documents - 문서 여부 (BOOLEAN)",
            "list_url": "list_url - 목록 링크 (TEXT)",
            "detail_url": "detail_url (TEXT)",
            "posted_at": "posted_at (TIMESTAMP)",
            "last_modified": "last_modified (TIMESTAMP)",
            "apply_start_at": "apply_start_at (TIMESTAMP)",
            "apply_end_at": "apply_end_at (TIMESTAMP)",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
    "housing.platforms": {
        "columns": {
            "code": "code - PK, 고유 식별자",
            "name": "name - 이름",
            "url": "url - 링크 (TEXT)",
            "platform_code": "platform_code - 플랫폼 코드 - FK → housing.code_master.cd",
            "is_active": "is_active - 활성화 여부 (BOOLEAN)",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
    "housing.unit_features": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "unit_id": "unit_id - FK → housing.units.unit_id",
            "room_count": "room_count - 개수",
            "bathroom_count": "bathroom_count - 개수",
            "direction": "direction (VARCHAR(20))",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
    "housing.units": {
        "columns": {
            "unit_id": "unit_id - PK, 고유 식별자",
            "notice_id": "notice_id - FK → housing.notices.notice_id",
            "unit_type": "unit_type - 타입",
            "deposit": "deposit - 보증금",
            "rent": "rent - 임대료",
            "maintenance_fee": "maintenance_fee (NUMERIC)",
            "area_m2": "area_m2 - 면적",
            "floor": "floor - 층",
            "room_number": "room_number - 방",
            "occupancy_available": "occupancy_available (BOOLEAN)",
            "occupancy_available_at": "occupancy_available_at (TIMESTAMP)",
            "capacity": "capacity (INTEGER)",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
}

# ========== INFRA 스키마 ==========
infra_tables = {
    "infra.addresses": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "name": "name - 법정동코드",
            "ctpv_nm": "ctpv_nm - 시도 이름",
            "sgg_nm": "sgg_nm - 시군구 이름",
            "emd_nm": "emd_nm - 동 이름",
            "created_at": "created_at - 생성일시",
        },
    },
    "infra.facility_info": {
        "columns": {
            "facility_id": "facility_id - PK, 고유 식별자",
            "cd": "cd - 시설 코드 - FK → infra.infra_code.cd",
            "name": "name - 시설 이름",
            "address_raw": "address_raw - 주소",
            "address_id": "address_id - 법정동코드 - FK → infra.addresses.id",
            "lat": "lat - 위도",
            "lon": "lon - 경도",
            "tel": "tel - 전화번호",
            "website": "website - 웹사이트",
            "operating_hours": "operating_hours - 운영시간",
            "is_24h": "is_24h - 24시간 운영 여부 (BOOLEAN)",
            "is_emergency": "is_emergency - 응급실 존재 여부 (BOOLEAN)",
            "capacity": "capacity - 수용인원",
            "grade_level": "grade_level - 등급",
            "facility_extra": "facility_extra - 시설 추가 정보 (국공립/사립 등)",
            "data_source": "data_source - 데이터 출처",
            "last_updated": "last_updated - 최근 업데이트 일시",
            "created_at": "created_at - 생성일시",
        },
    },
    "infra.housing_facility_distances": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "notice_id": "notice_id - ID/식별자",
            "facility_id": "facility_id - FK → infra.facility_info.facility_id",
            "distance_m": "distance_m - 거리",
            "walking_time_m": "walking_time_m (INTEGER)",
            "driving_time_m": "driving_time_m (INTEGER)",
            "created_at": "created_at - 생성일시",
        },
    },
    "infra.infra_code": {
        "columns": {
            "cd": "cd - PK, 고유 식별자",
            "name": "name - 이름",
            "description": "description - 설명",
            "upper_cd": "upper_cd - 코드",
            "source": "source (VARCHAR(255))",
        },
    },
    "infra.transport_points": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "transport_type": "transport_type - 타입",
            "name": "name - 이름",
            "official_code": "official_code - 코드",
            "line_name": "line_name - 이름",
            "stop_type": "stop_type - 타입",
            "is_transfer": "is_transfer (BOOLEAN)",
            "lat": "lat - 위도",
            "lon": "lon - 경도",
            "extra_info": "extra_info (JSONB)",
            "created_at": "created_at - 생성일시",
        },
    },
}

# ========== RTMS 스키마 ==========
rtms_tables = {
    "rtms.code_table": {
        "columns": {
            "code": "code - PK, 고유 식별자",
            "name_kr": "name_kr - 이름",
            "name_en": "name_en - 이름",
            "code_type": "code_type - 코드",
            "description": "description - 설명",
            "display_order": "display_order (INTEGER)",
            "rtms_value": "rtms_value (VARCHAR(50))",
            "housing_code": "housing_code - 코드",
            "min_area": "min_area - 면적",
            "max_area": "max_area - 면적",
            "created_at": "created_at - 생성일시",
            "updated_at": "updated_at - 수정일시",
        },
    },
    "rtms.transactions_rent": {
        "columns": {
            "id": "id - PK, 고유 식별자",
            "building_type": "building_type - 타입",
            "sigungudong": "sigungudong (VARCHAR(150))",
            "emd_code": "emd_code - 코드",
            "road_address": "road_address - 주소",
            "building_name": "building_name - 이름",
            "area_type": "area_type - 타입",
            "area_m2": "area_m2 - 면적",
            "area_range": "area_range - 면적",
            "floor": "floor - 층",
            "contract_type": "contract_type - 타입",
            "contract_year_month": "contract_year_month (INTEGER)",
            "contract_status": "contract_status (VARCHAR(10))",
            "contract_start_ym": "contract_start_ym (INTEGER)",
            "contract_end_ym": "contract_end_ym (INTEGER)",
            "deposit_amount": "deposit_amount - 보증금",
            "monthly_rent": "monthly_rent - 임대료",
            "converted_price": "converted_price - 가격",
            "construction_year": "construction_year - 건축연도"
        },
    },
}


    '''


# ========== 헬퍼 함수 ==========
def query_from_natural_language(question: str) -> str:
    """
    자연어 질문을 PostgreSQL SQL 쿼리로 변환하여 반환합니다.
    """
    prompt = f"""
You are an expert PostgreSQL data analyst.
Based on the database schema below, write a syntactically correct SELECT-only SQL query 
to answer the user's question.

SCHEMA:
{filtered_schema_info}

Rules:
- Only generate SELECT queries referencing tables listed in the SCHEMA above.
- Use fully qualified table names (e.g., housing.addresses)
- Join tables only if both appear in the SCHEMA above and have a foreign key relationship
- Avoid using ORDER BY on columns not in SELECT DISTINCT
- No UPDATE, DELETE, INSERT. Only SELECT.

- 사용자가 ~주택 추천해줘 라고 요청한다면
주택 이름, 주소, tag_type과 tag_value에 대한 정보만 조회하는 쿼리를 반환한다. 
- 사용자가 그외의 정보를 특정해서 물어보는 경우 해당 테이블과 컬럼을 조회하는 쿼리를 반환한다. 

USER QUESTION:
{question}

Return only the SQL query.
"""
    response = llm.invoke(prompt)
    
    # LLM 모델 타입에 따라 content 추출 방식이 다름
    # OpenAI (ChatOpenAI): response.content 속성 존재
    # Ollama (OllamaLLM): content 속성이 없고 직접 문자열이거나 다른 방식으로 접근
    if isinstance(llm, ChatOpenAI):
        # OpenAI 모델: content 속성 사용
        sql = response.content.strip() if hasattr(response, 'content') else str(response).strip()
    elif isinstance(llm, OllamaLLM):
        # Ollama 모델: content 속성이 없으므로 직접 문자열 변환 또는 다른 속성 확인
        if hasattr(response, 'response'):
            sql = str(response.response).strip()
        elif hasattr(response, 'content'):
            sql = str(response.content).strip()
        else:
            sql = str(response).strip()
    else:
        # 기타 모델: 안전하게 처리
        sql = response.content.strip() if hasattr(response, 'content') else str(response).strip()
    
    return sql  # 마크다운 형식으로 나옴


def extract_sql(response: str) -> str:
    """SQL 추출"""
    sql = response.strip()
    
    # 마크다운 제거
    if '```' in sql:
        match = re.search(r'```(?:sql)?\s*(.*?)\s*```', sql, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
    
    # SELECT 부분만 추출
    if not sql.upper().startswith('SELECT'):
        match = re.search(r'(SELECT.*)', sql, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
    
    return sql.rstrip(';').strip()


# ========== 도구 정의 ==========
@tool
def rdb_search(query: str) -> str:
    """
    query_from_natural_language 함수를 사용하여 자연어 질문을 SQL 쿼리로 변환하고,
    postgres 데이터베이스에서 데이터를 조회하는 도구입니다.
    """
    sql = query_from_natural_language(query)

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수를 찾을 수 없습니다. .env 파일을 확인하세요.")

    db = SQLDatabase.from_uri(database_url)

    # sql 쿼리 받아 실행
    query_tool = QuerySQLDataBaseTool(db=db)
    result = query_tool.run(sql)

    return result


@tool
def vector_search(query: str) -> str:
    """
    주택 관련 금융정보를 벡터디비에서 조회하는 도구
    
    MULTILINGUAL_E5_LARGE 모델을 사용하여 사용자 쿼리를 임베딩하고,
    embeddings_e5_large 테이블에서 유사도 비교를 통해 검색합니다.
    """
    try:
        # 1. 경로 설정
        current_dir = Path.cwd()
        services_dir = None
        
        # backend/services 디렉토리 찾기
        for parent in [current_dir] + list(current_dir.parents):
            potential_services = parent / "backend" / "services"
            if potential_services.exists():
                services_dir = potential_services
                break
        
        if not services_dir:
            return "❌ 오류: backend/services 디렉토리를 찾을 수 없습니다."
        
        if str(services_dir) not in sys.path:
            sys.path.insert(0, str(services_dir))
        
        # 2. Import (명확하게)
        from rag.core.search import VectorRetriever
        from rag.models.config import EmbeddingModelType
        
        # 사용 가능한 모델 타입 확인 (디버깅용)
        available_models = [attr for attr in dir(EmbeddingModelType) 
                          if not attr.startswith('_') and attr.isupper()]
        
        # 3. 모델 타입 확인 및 설정
        # MULTILINGUAL_E5_LARGE가 존재하는지 확인
        if not hasattr(EmbeddingModelType, 'MULTILINGUAL_E5_LARGE'):
            return f"❌ 오류: MULTILINGUAL_E5_LARGE 모델 타입을 찾을 수 없습니다.\n사용 가능한 모델: {available_models}"
        
        model_type = EmbeddingModelType.MULTILINGUAL_E5_LARGE
        
        # 4. DB 설정
        load_dotenv()
        db_config = {
            'host': os.getenv('PG_HOST'),
            'port': os.getenv('PG_PORT'),
            'database': os.getenv('PG_DB'),
            'user': os.getenv('PG_USER'),
            'password': os.getenv('PG_PASSWORD')
        }
        
        # 5. VectorRetriever 초기화
        try:
            retriever = VectorRetriever(
                model_type=model_type,
                db_config=db_config
            )
        except Exception as e:
            return f"❌ VectorRetriever 초기화 실패: {str(e)}\n모델 타입: {model_type}"
        
        # 6. 검색 수행
        try:
            results = retriever.search(
                query=query,
                top_k=2,
                min_similarity=0.6
            )
        except Exception as e:
            import traceback
            return f"❌ 검색 실행 실패: {str(e)}\n상세: {traceback.format_exc()}"
        
        # 7. 결과 포맷팅
        if not results:
            return "❌ 검색 결과가 없습니다. 다른 키워드로 시도해보세요."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            # content 키가 있는지 확인
            content = result.get('content') or result.get('document', '')
            similarity = result.get('similarity', 0)
            chunk_id = result.get('chunk_id', 'N/A')
            
            formatted_results.append(
                f"{i}. [유사도: {similarity:.3f}, ID: {chunk_id}]\n"
                f"   내용: {content[:200]}...\n"
            )
        
        return f"✅ 벡터 검색 결과 ({len(results)}건):\n\n" + "\n".join(formatted_results)
            
    except ImportError as e:
        return f"❌ 모듈 import 오류: {str(e)}\n경로 설정을 확인해주세요."
    except Exception as e:
        import traceback
        return f"❌ 벡터 검색 오류: {str(e)}\n\n상세 오류:\n{traceback.format_exc()}"


# ========== 도구 목록 ==========
available_tools = [
    rdb_search,
    vector_search
]


# ========== LLM with Tools ==========
def create_llm_with_tools():
    """도구가 연결된 LLM 생성"""
    return llm.bind_tools(available_tools)  # LLM에 등록된 tools 적용

