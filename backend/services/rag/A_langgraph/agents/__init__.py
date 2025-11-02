"""
전문화된 에이전트들

각 에이전트는 특정 도메인에 특화되어 있습니다:
- HousingAgent: 주택 데이터베이스 전문 (RDB + SQL Agent) ✅ 사용 중
- LoanAgent: 대출 정책 전문 (Vector DB + 재검색 루프) ✅ 사용 중
- RTMSAgent: 실거래가 데이터 전문 (RDB + 점수 계산) ⚠️ 미구현 (주석처리)
- RecommendationAgent: 최종 추천 선별 ✅ 사용 중
- FeedbackAgent: 피드백 분석 및 반영 ⚠️ Phase 2에서 구현 예정

나중에 확장 예정:
- InfraAgent: 인프라 데이터 전문 (PostGIS + 공간 쿼리)
- ScoringAgent: 종합 점수 계산 전문
"""

from .housing_agent import HousingAgent
from .loan_agent import LoanAgent
from .rtms_agent import RTMSAgent
from .recommendation_agent import RecommendationAgent
from .feedback_agent import FeedbackAgent  # Phase 2에서 활성화 예정

__all__ = [
    "HousingAgent",
    "LoanAgent", 
    "RTMSAgent",
    "RecommendationAgent",
    "FeedbackAgent"  # Phase 2에서 활성화 예정
]
