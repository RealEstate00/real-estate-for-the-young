"""
Recommendation Agent - 최종 추천 선별 에이전트

여러 Agent들의 결과를 종합하여 최종 추천 리스트를 생성합니다.
순수 함수로 구현하여 LangGraph 노드에서 쉽게 호출할 수 있습니다.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RecommendationAgent:
    """
    최종 추천 선별 에이전트 (순수 함수 기반)
    
    담당:
    - 여러 Agent 결과 종합
    - 최종 추천 리스트 생성
    - 추천 이유 생성
    
    참고:
    - 현재는 단순한 선별 로직 구현
    - 나중에 더 정교한 추천 알고리즘 추가 예정
    """

    def __init__(self):
        """초기화"""
        pass

    def select_top_n(
        self,
        candidates: List[Dict],
        rtms_scores: Dict[str, float] = None,
        loan_info: str = "",
        top_n: int = 10
    ) -> List[Dict]:
        """
        상위 N개 매물 선별
        
        Args:
            candidates: 후보 매물 리스트
            rtms_scores: 실거래가 점수 (매물 ID별) _ 현재 미구현
            loan_info: 대출 관련 정보
            top_n: 선별할 개수
            
        Returns:
            선별된 추천 매물 리스트
        """
        if not candidates:
            return []
            
        try:
            # 각 후보에 점수 부여
            scored_candidates = []
            
            for candidate in candidates:
                candidate_id = candidate.get('id', str(hash(str(candidate))))
                
                # 종합 점수 계산
                total_score = self._calculate_total_score(
                    candidate=candidate,
                    rtms_score=rtms_scores.get(candidate_id, 0.5) if rtms_scores else 0.5,
                    loan_info=loan_info
                )
                
                # 추천 이유 생성
                recommendation_reason = self._generate_recommendation_reason(
                    candidate=candidate,
                    rtms_score=rtms_scores.get(candidate_id, 0.5) if rtms_scores else 0.5,
                    loan_info=loan_info
                )
                
                scored_candidate = {
                    **candidate,
                    "total_score": total_score,
                    "recommendation_reason": recommendation_reason,
                    "rtms_score": rtms_scores.get(candidate_id, 0.5) if rtms_scores else 0.5
                }
                
                scored_candidates.append(scored_candidate)
            
            # 점수 순으로 정렬하여 상위 N개 선택
            sorted_candidates = sorted(
                scored_candidates,
                key=lambda x: x["total_score"],
                reverse=True
            )
            
            return sorted_candidates[:top_n]
            
        except Exception as e:
            logger.error(f"추천 선별 중 오류 발생: {e}")
            return candidates[:top_n]  # 오류 시 원본에서 상위 N개만 반환

    def _calculate_total_score(
        self,
        candidate: Dict,
        rtms_score: float,
        loan_info: str
    ) -> float:
        """
        종합 점수 계산
        
        Args:
            candidate: 매물 정보
            rtms_score: 실거래가 점수
            loan_info: 대출 관련 정보
            
        Returns:
            0.0 ~ 1.0 사이의 종합 점수
        """
        # 현재는 단순한 가중 평균 계산
        # 나중에 더 정교한 알고리즘으로 개선 예정
        
        # 기본 점수 (매물 자체의 품질)
        base_score = 0.6
        
        # 실거래가 점수 반영 (40% 가중치)
        rtms_weight = 0.4
        rtms_contribution = rtms_score * rtms_weight
        
        # 대출 정보 반영 (20% 가중치)
        loan_weight = 0.2
        loan_contribution = self._calculate_loan_score(candidate, loan_info) * loan_weight
        
        # 위치 점수 (40% 가중치)
        location_weight = 0.4
        location_contribution = self._calculate_location_score(candidate) * location_weight
        
        total_score = rtms_contribution + loan_contribution + location_contribution
        
        # 점수 범위 제한 (0.0 ~ 1.0)
        return max(0.0, min(1.0, total_score))

    def _calculate_loan_score(self, candidate: Dict, loan_info: str) -> float:
        """대출 관련 점수 계산"""
        # TODO: 대출 정보와 매물의 연관성 분석
        # 현재는 기본 점수 반환
        
        if not loan_info or "정보를 찾을 수 없습니다" in loan_info:
            return 0.3  # 대출 정보 없으면 낮은 점수
            
        # 대출 관련 키워드가 있으면 점수 상승
        loan_keywords = ["청년", "전세", "대출", "금리", "지원"]
        keyword_count = sum(1 for keyword in loan_keywords if keyword in loan_info)
        
        return min(0.8, 0.4 + (keyword_count * 0.1))

    def _calculate_location_score(self, candidate: Dict) -> float:
        """위치 점수 계산"""
        location = candidate.get('location', '').lower()
        
        # 임시 위치 점수 (실제로는 더 정교한 로직 필요)
        if '강남' in location:
            return 0.9
        elif '서초' in location:
            return 0.85
        elif '송파' in location:
            return 0.8
        elif '마포' in location:
            return 0.75
        else:
            return 0.6

    def _generate_recommendation_reason(
        self,
        candidate: Dict,
        rtms_score: float,
        loan_info: str
    ) -> str:
        """추천 이유 생성"""
        reasons = []
        
        # 실거래가 점수 기반 이유
        if rtms_score > 0.7:
            reasons.append("시세 대비 적정한 가격")
        elif rtms_score > 0.5:
            reasons.append("합리적인 가격대")
        
        # 위치 기반 이유
        location = candidate.get('location', '')
        if '강남' in location:
            reasons.append("프리미엄 지역 위치")
        elif '서초' in location:
            reasons.append("교통 편리한 지역")
            
        # 대출 관련 이유
        if loan_info and "청년" in loan_info:
            reasons.append("청년 대출 지원 가능")
            
        # 매물 특성 기반 이유
        if candidate.get('type') == '원룸':
            reasons.append("1인 가구에 적합")
            
        if not reasons:
            reasons.append("기본 조건 만족")
            
        return " • ".join(reasons)

    def generate_summary(self, recommendations: List[Dict]) -> Dict:
        """
        추천 결과 요약 생성
        
        Args:
            recommendations: 추천 매물 리스트
            
        Returns:
            추천 결과 요약
        """
        if not recommendations:
            return {
                "total_count": 0,
                "average_score": 0.0,
                "top_locations": [],
                "price_range": "정보 없음",
                "summary": "추천 매물이 없습니다."
            }
            
        # 통계 계산
        total_count = len(recommendations)
        average_score = sum(r.get("total_score", 0) for r in recommendations) / total_count
        
        # 상위 지역 추출
        locations = [r.get("location", "") for r in recommendations]
        location_counts = {}
        for loc in locations:
            if loc:
                location_counts[loc] = location_counts.get(loc, 0) + 1
        
        top_locations = sorted(
            location_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # 가격 범위 (임시)
        price_range = "다양한 가격대"
        
        # 요약 메시지 생성
        summary = f"""총 {total_count}개 매물을 추천드립니다.
평균 추천 점수: {average_score:.2f}/1.0
주요 지역: {', '.join([loc[0] for loc in top_locations[:2]])}"""
        
        return {
            "total_count": total_count,
            "average_score": average_score,
            "top_locations": [{"location": loc, "count": count} for loc, count in top_locations],
            "price_range": price_range,
            "summary": summary
        }
