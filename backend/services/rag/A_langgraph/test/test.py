# 1. 라이브러리 및 의존성 Import
# Multi-Agent 추천 시스템 구축을 위한 필수 라이브러리들을 import합니다.

import os
import sys
import time
from typing import Dict, List, Optional, TypedDict, Any, Literal
from dataclasses import dataclass
import json
import concurrent.futures
from dotenv import load_dotenv
load_dotenv()

# LangGraph 및 LangChain 관련
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.agents import AgentType

# 기존 RAG 시스템 재사용
# 상대 import를 사용하는 모듈이므로 패키지 루트를 sys.path에 추가
# 현재 파일: backend/services/rag/A_langgraph/test/test.py
# 목표: backend/services를 sys.path에 추가하여 rag 패키지 import 가능하게 함

current_file = os.path.abspath(__file__)
# backend/services/rag/A_langgraph/test/test.py
# -> backend/services/rag/A_langgraph/test
# -> backend/services/rag/A_langgraph
# -> backend/services/rag
# -> backend/services
services_dir = os.path.abspath(os.path.join(os.path.dirname(current_file), '..', '..', '..'))
services_dir = os.path.normpath(services_dir)

# rag 디렉토리가 있는지 확인
rag_dir = os.path.join(services_dir, 'rag')
if not os.path.exists(rag_dir):
    # 경로 계산 실패 시, 프로젝트 루트 찾기 (pyproject.toml 등)
    current = os.path.dirname(current_file)
    while current != os.path.dirname(current):  # 루트에 도달할 때까지
        if os.path.exists(os.path.join(current, 'pyproject.toml')):
            # 프로젝트 루트 찾음
            services_dir = os.path.join(current, 'backend', 'services')
            rag_dir = os.path.join(services_dir, 'rag')
            if os.path.exists(rag_dir):
                break
        current = os.path.dirname(current)

if services_dir not in sys.path:
    sys.path.insert(0, services_dir)

from rag.retrieval.retriever import Retriever
from rag.models.config import EmbeddingModelType

print("[OK] 모든 라이브러리 import 완료")
print("[INFO] Phase 1: 기본 추천 구현 시작")



# 3. Housing Agent 구현 (RDB 전문)
# 주택 데이터베이스 전문 에이전트 - SQL Agent 패턴 사용

class HousingAgent:
    """
    주택 데이터베이스 전문 에이전트
    
    담당:
    - housing.notices (주택 공고)
    - housing.units (호실 정보)  
    - housing.complexes (단지 정보)
    
    패턴: create_sql_agent 사용 (LangChain이 내부적으로 Tool 생성)
    - list_tables: 테이블 목록 조회
    - schema_sql_db: 스키마 정보 확인
    - query_sql_db: SQL 쿼리 실행
    - query_checker: SQL 쿼리 검증
    """
    
    def __init__(self, db_uri: str = None, schema_info: str = None):
        # 실제 환경에서는 DB 연결 설정
        self.db_uri = db_uri or "postgresql://postgres:post1234@localhost:5432/rey"
        self.schema_info = schema_info or """
        housing.notices: 주택 공고 정보 (주소, 이름 등)
        housing.units: 호실 정보 (평수, 월세, 보증금 등)
        """
        
        # LLM 초기화 
        try:
            self.llm = ChatOllama(model="gemma3:4b", temperature=0)
            print("[OK] Ollama LLM 초기화 완료")
        except:
            # Fallback to mock
            self.llm = None
            print("[WARN] OpenAI API 없음 - Mock 모드로 실행")
        
        # SQL Database 연결 (실제 환경에서만)
        self.db = None
        self.agent = None
        
        try:
            # 여기서 무슨 의미냐면:
            # SQLDatabase.from_uri는 데이터베이스 URI를 활용해 실제 DB에 연결하는 객체를 생성합니다.
            # 즉, self.db는 PostgreSQL의 housing.notices, housing.units 테이블에 접근할 수 있게 해줍니다.
            self.db = SQLDatabase.from_uri(
                self.db_uri,
                include_tables=["housing.notices", "housing.units"]
            )
            # self.llm이 초기화되어 있으면 SQL Agent를 생성 (즉, 실제 LLM이 있는 경우에만 agent 활성화)
            if self.llm:
                self.agent = create_sql_agent(
                    llm=self.llm,
                    db=self.db,
                    agent_type=AgentType.OPENAI_FUNCTIONS,
                    verbose=True,
                    prefix=self._get_system_prompt()
                )
            print("[OK] Housing Agent 초기화 완료")
        except Exception as e:
            print(f"[WARN] DB 연결 실패 - Mock 모드로 실행: {e}")
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return f"""
        당신은 주택 데이터베이스 전문가입니다.

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
                "candidates": List[Dict],  # 매물 후보들
                "source": "rdb",
                "sql_query": str (optional)
            }
        """
        if self.agent:
            # 실제 SQL Agent 실행
            result = self.agent.invoke({"input": query})
            
            # 후보 매물 생성 (실제로는 SQL 결과에서 파싱)
            candidates = self._parse_candidates_from_result(result["output"])
            
            return {
                "agent": "housing",
                "query": query,
                "result": result["output"],
                "candidates": candidates,
                "source": "rdb"
            }
        else:
            # Mock 데이터 반환
            mock_candidates = self._generate_mock_candidates(query)
            
            return {
                "agent": "housing", 
                "query": query,
                "result": f"강남구 원룸 {len(mock_candidates)}건을 찾았습니다.",
                "candidates": mock_candidates,
                "source": "rdb_mock"
            }
    
    def _parse_candidates_from_result(self, sql_result: str) -> List[Dict]:
        """SQL 결과에서 후보 매물 파싱 (실제 구현 필요)"""
        # 실제로는 SQL 결과를 파싱하여 구조화된 데이터로 변환
        return []
    
    def _generate_mock_candidates(self, query: str) -> List[Dict]:
        """Mock 후보 매물 생성 (테스트용)"""
        candidates = []
        for i in range(5):
            candidates.append({
                "id": f"house_{i+1}",
                "name": f"강남구 원룸 {i+1}",
                "location": "서울시 강남구",
                "price": 500 + i * 100,  # 500~900만원
                "monthly_rent": 50 + i * 10,  # 50~90만원
                "area": 20 + i * 5,  # 20~40평방미터
                "description": f"깔끔한 원룸 {i+1}호"
            })
        return candidates

# Housing Agent 인스턴스 생성
housing_agent = HousingAgent()
print("[OK] Housing Agent 생성 완료")


# HousingAgent 클래스의 동작 테스트 코드



if __name__ == "__main__":

    def test_housing_agent():
        print("=== HousingAgent 테스트 시작 ===")
        test_queries = [
            "강서구 주택 추천",
            "송파구 사회주택 추천",
            "신촌역 근처 주택 추천"
        ]
        
        for idx, query in enumerate(test_queries):
            print(f"\n[{idx+1}] 테스트 쿼리: {query}")
            # housing_agent는 이미 위에서 생성됨
            result = housing_agent.search(query)
            print("결과:")
            for k, v in result.items():
                print(f"  {k}: {v}")
            
            # 후보 데이터 sanity check
            candidates = result.get("candidates", [])
            assert isinstance(candidates, list), "candidates should be a list"
            assert len(candidates) > 0, "후보 매물 개수는 0보다 커야 합니다 (mock 모드 기준)"
            assert "name" in candidates[0], "후보 매물 dict에 'name' 필드가 있어야 함"
        print("\n=== HousingAgent 테스트 통과 [OK] ===")
        
    # 테스트 함수 실행
    test_housing_agent()
