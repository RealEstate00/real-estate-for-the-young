"""
RTMS Agent - 실거래가 데이터 전문 에이전트

실거래가 데이터를 분석하여 매물의 가격 적정성 점수를 계산합니다.
순수 함수로 구현하여 LangGraph 노드에서 쉽게 호출할 수 있습니다.
"""

from typing import Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)


class RTMSAgent:
    """
    실거래가 데이터 전문 에이전트 (순수 함수 기반)
    
    담당:
    - 실거래가 데이터 조회 (RDB)
    - 가격 적정성 점수 계산
    - 시세 비교 분석
    
    참고:
    - 현재는 기본적인 점수 계산만 구현
    - 나중에 더 정교한 분석 로직 추가 예정
    """

    def __init__(self, db_connection=None):
        """
        Args:
            db_connection: 데이터베이스 연결 객체 (선택사항)
        """
        self.db_connection = db_connection

    def calculate_scores(self, candidates: List[Dict]) -> Dict[str, float]:
        """
        후보 매물들의 실거래가 점수 계산
        
        Args:
            candidates: 후보 매물 리스트
            
        Returns:
            매물 ID별 점수 딕셔너리 {"candidate_id": score, ...}
        """
        if not candidates:
            return {}
            
        scores = {}
        
        for candidate in candidates:
            candidate_id = candidate.get('id', str(hash(str(candidate))))
            
            try:
                # 실거래가 점수 계산
                score = self._calculate_individual_score(candidate)
                scores[candidate_id] = score
                
            except Exception as e:
                logger.error(f"후보 {candidate_id} 점수 계산 실패: {e}")
                scores[candidate_id] = 0.5  # 기본 점수
                
        return scores

    def _calculate_individual_score(self, candidate: Dict) -> float:
        """
        개별 매물의 실거래가 점수 계산
        
        Args:
            candidate: 매물 정보
            
        Returns:
            0.0 ~ 1.0 사이의 점수
        """
        # TODO: 실제 실거래가 데이터와 비교하는 로직 구현
        # 현재는 임시 점수 계산 로직
        
        # 기본 점수
        base_score = 0.5
        
        # 가격 정보가 있으면 분석
        price_info = candidate.get('price', '')
        location = candidate.get('location', '')
        area = candidate.get('area', '')
        
        # 임시 점수 계산 (실제로는 DB에서 실거래가 조회 필요)
        if '월세' in price_info:
            # 월세 매물 점수 계산
            score = self._calculate_monthly_rent_score(price_info, location, area)
        elif '전세' in price_info:
            # 전세 매물 점수 계산
            score = self._calculate_jeonse_score(price_info, location, area)
        elif '매매' in price_info:
            # 매매 매물 점수 계산
            score = self._calculate_sale_score(price_info, location, area)
        else:
            score = base_score
            
        # 점수 범위 제한 (0.0 ~ 1.0)
        return max(0.0, min(1.0, score))

    def _calculate_monthly_rent_score(self, price_info: str, location: str, area: str) -> float:
        """월세 매물 점수 계산"""
        # TODO: 실제 월세 시세와 비교
        # 현재는 임시 로직
        
        base_score = 0.6
        
        # 강남구면 점수 조정
        if '강남' in location:
            base_score += 0.1
        elif '서초' in location:
            base_score += 0.05
            
        return base_score

    def _calculate_jeonse_score(self, price_info: str, location: str, area: str) -> float:
        """전세 매물 점수 계산"""
        # TODO: 실제 전세 시세와 비교
        # 현재는 임시 로직
        
        base_score = 0.7
        
        # 지역별 점수 조정
        if '강남' in location:
            base_score += 0.15
        elif '서초' in location:
            base_score += 0.1
            
        return base_score

    def _calculate_sale_score(self, price_info: str, location: str, area: str) -> float:
        """매매 매물 점수 계산"""
        # TODO: 실제 매매 시세와 비교
        # 현재는 임시 로직
        
        base_score = 0.65
        
        # 지역별 점수 조정
        if '강남' in location:
            base_score += 0.2
        elif '서초' in location:
            base_score += 0.15
            
        return base_score

    def get_market_analysis(self, location: str, property_type: str) -> Dict:
        """
        특정 지역/유형의 시장 분석 정보 제공
        
        Args:
            location: 지역 (예: "강남구")
            property_type: 매물 유형 (예: "원룸", "투룸")
            
        Returns:
            시장 분석 정보
        """
        # TODO: 실제 시장 분석 로직 구현
        # 현재는 임시 데이터 반환
        
        return {
            "location": location,
            "property_type": property_type,
            "average_price": "시세 정보 없음",
            "price_trend": "보통",
            "market_activity": "보통",
            "analysis_date": time.strftime("%Y-%m-%d"),
            "note": "실제 RTMS 데이터 연동 필요"
        }

    def compare_with_market(self, candidate: Dict) -> Dict:
        """
        개별 매물을 시장 시세와 비교
        
        Args:
            candidate: 매물 정보
            
        Returns:
            비교 분석 결과
        """
        location = candidate.get('location', '')
        price_info = candidate.get('price', '')
        
        # 시장 분석 정보 조회
        market_info = self.get_market_analysis(location, candidate.get('type', ''))
        
        # 가격 적정성 점수
        price_score = self._calculate_individual_score(candidate)
        
        return {
            "candidate_id": candidate.get('id', ''),
            "price_score": price_score,
            "market_comparison": "시세 대비 적정" if price_score > 0.6 else "시세 대비 높음",
            "market_info": market_info,
            "recommendation": "추천" if price_score > 0.7 else "검토 필요"
        }
