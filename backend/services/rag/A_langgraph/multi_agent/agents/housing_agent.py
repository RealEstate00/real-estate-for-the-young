"""
Housing Agent - 주택 데이터베이스 전문 에이전트

SQL Agent를 사용하여 주택 데이터베이스에서 매물 정보를 검색합니다.
LangChain의 create_sql_agent를 활용하여 자연어 질문을 SQL로 변환합니다.
"""

from typing import Dict, List, Optional
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.agents import AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
import time
import logging

logger = logging.getLogger(__name__)


class HousingAgent:
    """
    주택 데이터베이스 전문 에이전트

    담당:
    - housing.notices (주택 공고)
    - housing.units (호실 정보)

    Tool (create_sql_agent가 자동 생성):
    - list_tables: 테이블 목록 조회
    - schema_sql_db: 스키마 정보 확인
    - query_sql_db: SQL 쿼리 실행
    - query_checker: SQL 쿼리 검증
    
    추가 Tool (LLM 판단하에 사용):
    - rtms_analysis: 실거래가 분석 및 점수 계산
    """

    def __init__(self, db_uri: str, schema_path: Optional[str] = None, rtms_agent=None):
        """
        Args:
            db_uri: PostgreSQL 연결 URI
            schema_path: SQL 스키마 파일 경로 (선택사항)
            rtms_agent: RTMS Agent 인스턴스 (선택사항)
        """
        self.db_uri = db_uri
        self.schema_path = schema_path
        self.rtms_agent = rtms_agent
        
        # PostgreSQL 연결
        # 주의: search_path가 housing, infra, rtms, vector_db로 설정되어 있어
        # 스키마 이름 없이 테이블 이름만 사용 가능
        # include_tables에 스키마 이름을 포함하면 테이블을 찾지 못함
        self.db = SQLDatabase.from_uri(db_uri)

        # 스키마 정보 로드 (선택사항)
        self.schema_info = ""
        if schema_path:
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    self.schema_info = f.read()
            except FileNotFoundError:
                logger.warning(f"스키마 파일을 찾을 수 없습니다: {schema_path}")

        # LLM 초기화
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # 추가 Tool 생성 (RTMS Agent가 있는 경우)
        extra_tools = []
        if self.rtms_agent:
            extra_tools.append(self._create_rtms_tool())

        # SQL Agent 생성
        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            prefix=self._get_system_prompt(),
            extra_tools=extra_tools  # 추가 Tool 포함
        )

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        base_prompt = """당신은 주택 데이터베이스 전문가입니다.

        ### 역할:
        - 사용자 질문을 분석하여 정확한 SQL 쿼리 작성
        - JOIN, WHERE, GROUP BY 등을 적절히 활용
        - 지역, 가격, 평수, 공급 유형 등으로 필터링
        - 결과를 명확하게 요약

        ### 주의사항:
        - 읽기 전용 쿼리만 실행 (SELECT만)
        - NULL 값 처리 주의
        - 한글 컬럼명 정확히 사용
        - 결과가 많을 경우 LIMIT 사용하여 상위 50개만 조회

        ### 스키마 정보:
        {self.schema_info}
        """

        if self.schema_info:
            return f"""{base_prompt}

### 스키마 정보:
{self.schema_info}"""
        
        

    def search(self, query: str) -> Dict:
        """
        주택 데이터 검색

        Args:
            query: 사용자 질문 (예: "강남구 원룸 추천해줘")

        Returns:
            {
                "agent": "housing",
                "query": str,
                "result": str,
                "candidates": List[Dict],  # 파싱된 후보 리스트
                "source": "rdb",
                "sql_query": str (optional),
                "execution_time_ms": float
            }
        """
        start_time = time.time()
        
        try:
            # SQL Agent 실행
            result = self.agent.invoke({"input": query})
            
            # 결과 파싱하여 후보 리스트 생성
            candidates = self._parse_candidates(result["output"])
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "agent": "housing",
                "query": query,
                "result": result["output"],
                "candidates": candidates,
                "source": "rdb",
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Housing Agent 실행 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            
            return {
                "agent": "housing",
                "query": query,
                "result": error_msg,
                "candidates": [],
                "source": "rdb",
                "execution_time_ms": execution_time,
                "error": str(e)
            }

    def _parse_candidates(self, sql_result: str) -> List[Dict]:
        """
        SQL 결과를 후보 리스트로 파싱
        
        Args:
            sql_result: SQL Agent의 결과 문자열
            
        Returns:
            파싱된 후보 리스트
        """
        # TODO: SQL 결과 파싱 로직 구현
        # 현재는 빈 리스트 반환 (나중에 구현)
        
        # 예시 구조:
        # [
        #     {
        #         "id": "notice_123",
        #         "title": "강남구 원룸 임대",
        #         "location": "서울시 강남구",
        #         "price": "월세 50만원",
        #         "area": "20평",
        #         "type": "원룸"
        #     },
        #     ...
        # ]
        
        return []

    def get_schema_info(self) -> str:
        """스키마 정보 반환"""
        return self.db.get_table_info()


    def test_connection(self) -> bool:
        """DB 연결 테스트"""
        try:
            # 간단한 쿼리로 연결 테스트
            self.db.run("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"DB 연결 테스트 실패: {e}")
            return False
