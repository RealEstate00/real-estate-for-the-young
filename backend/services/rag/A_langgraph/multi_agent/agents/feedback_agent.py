"""
Feedback Agent - 피드백 분석 및 반영 에이전트

사용자 피드백을 분석하여 추천 시스템을 개선합니다.
순수 함수로 구현하여 LangGraph 노드에서 쉽게 호출할 수 있습니다.

⚠️ 현재 상태: 미구현 (Phase 2에서 구현 예정)
- 코드는 작성되어 있으나 그래프에서 비활성화됨
- Phase 2에서 대화형 추천 기능과 함께 활성화 예정
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FeedbackAgent:
    """
    피드백 분석 및 반영 에이전트 (순수 함수 기반)
    
    담당:
    - 사용자 피드백 분석
    - 선호 패턴 추출
    - 가중치 동적 조정
    - 재추천 필요성 판단
    
    참고:
    - 현재는 기본적인 피드백 분석만 구현
    - 나중에 더 정교한 학습 알고리즘 추가 예정
    """

    def __init__(self):
        """초기화"""
        pass

    def analyze(
        self,
        feedback: Dict,
        previous_recommendations: List[Dict],
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        피드백 분석
        
        Args:
            feedback: 사용자 피드백
                {
                    "type": "like/dislike/text/action",
                    "target_ids": [매물 ID 리스트],
                    "text": "텍스트 피드백",
                    "action": "view/click/save"
                }
            previous_recommendations: 이전 추천 결과
            conversation_history: 대화 히스토리
            
        Returns:
            분석 결과
                {
                    "preference_patterns": {...},
                    "adjusted_weights": {...},
                    "needs_rerun": bool,
                    "feedback_summary": str
                }
        """
        try:
            # 피드백 타입별 분석
            feedback_type = feedback.get("type", "")
            
            if feedback_type == "like":
                return self._analyze_like_feedback(feedback, previous_recommendations)
            elif feedback_type == "dislike":
                return self._analyze_dislike_feedback(feedback, previous_recommendations)
            elif feedback_type == "text":
                return self._analyze_text_feedback(feedback, previous_recommendations)
            elif feedback_type == "action":
                return self._analyze_action_feedback(feedback, previous_recommendations)
            else:
                return self._create_default_analysis()
                
        except Exception as e:
            logger.error(f"피드백 분석 중 오류 발생: {e}")
            return self._create_default_analysis()

    def _analyze_like_feedback(self, feedback: Dict, recommendations: List[Dict]) -> Dict:
        """좋아요 피드백 분석"""
        target_ids = feedback.get("target_ids", [])
        liked_items = [r for r in recommendations if r.get("id") in target_ids]
        
        if not liked_items:
            return self._create_default_analysis()
            
        # 선호 패턴 추출
        patterns = self._extract_preference_patterns(liked_items, positive=True)
        
        # 가중치 조정 (좋아한 특성 강화)
        adjusted_weights = self._adjust_weights_for_likes(patterns)
        
        return {
            "preference_patterns": patterns,
            "adjusted_weights": adjusted_weights,
            "needs_rerun": True,  # 좋아요는 재추천 필요
            "feedback_summary": f"{len(liked_items)}개 매물을 좋아하셨습니다. 유사한 매물을 더 추천드리겠습니다."
        }

    def _analyze_dislike_feedback(self, feedback: Dict, recommendations: List[Dict]) -> Dict:
        """싫어요 피드백 분석"""
        target_ids = feedback.get("target_ids", [])
        disliked_items = [r for r in recommendations if r.get("id") in target_ids]
        
        if not disliked_items:
            return self._create_default_analysis()
            
        # 비선호 패턴 추출
        patterns = self._extract_preference_patterns(disliked_items, positive=False)
        
        # 가중치 조정 (싫어한 특성 약화)
        adjusted_weights = self._adjust_weights_for_dislikes(patterns)
        
        return {
            "preference_patterns": patterns,
            "adjusted_weights": adjusted_weights,
            "needs_rerun": True,  # 싫어요도 재추천 필요
            "feedback_summary": f"{len(disliked_items)}개 매물을 제외하고 다른 매물을 추천드리겠습니다."
        }

    def _analyze_text_feedback(self, feedback: Dict, recommendations: List[Dict]) -> Dict:
        """텍스트 피드백 분석"""
        text = feedback.get("text", "").lower()
        
        # 키워드 기반 분석
        needs_rerun = False
        adjusted_weights = {}
        feedback_summary = "피드백을 반영하겠습니다."
        
        # 가격 관련 피드백
        if any(keyword in text for keyword in ["비싸", "비용", "가격", "저렴"]):
            adjusted_weights["price"] = 0.6  # 가격 가중치 증가
            needs_rerun = True
            feedback_summary = "가격을 더 고려하여 재추천드리겠습니다."
            
        # 위치 관련 피드백
        elif any(keyword in text for keyword in ["위치", "지역", "교통", "역", "거리"]):
            adjusted_weights["location"] = 0.5  # 위치 가중치 증가
            needs_rerun = True
            feedback_summary = "위치를 더 고려하여 재추천드리겠습니다."
            
        # 대출 관련 피드백
        elif any(keyword in text for keyword in ["대출", "금리", "융자", "자금"]):
            adjusted_weights["loan"] = 0.4  # 대출 가중치 증가
            feedback_summary = "대출 관련 정보를 더 자세히 제공드리겠습니다."
        
        return {
            "preference_patterns": {"text_keywords": text.split()},
            "adjusted_weights": adjusted_weights,
            "needs_rerun": needs_rerun,
            "feedback_summary": feedback_summary
        }

    def _analyze_action_feedback(self, feedback: Dict, recommendations: List[Dict]) -> Dict:
        """행동 피드백 분석 (조회, 클릭, 저장 등)"""
        action = feedback.get("action", "")
        target_ids = feedback.get("target_ids", [])
        
        if action == "view" and target_ids:
            # 조회한 매물들의 패턴 분석
            viewed_items = [r for r in recommendations if r.get("id") in target_ids]
            patterns = self._extract_preference_patterns(viewed_items, positive=True)
            
            return {
                "preference_patterns": patterns,
                "adjusted_weights": {},  # 조회는 가중치 변경 없음
                "needs_rerun": False,
                "feedback_summary": f"{len(viewed_items)}개 매물을 확인하셨습니다."
            }
            
        return self._create_default_analysis()

    def _extract_preference_patterns(self, items: List[Dict], positive: bool = True) -> Dict:
        """선호/비선호 패턴 추출"""
        if not items:
            return {}
            
        patterns = {
            "locations": [],
            "price_ranges": [],
            "property_types": [],
            "common_features": []
        }
        
        # 위치 패턴
        locations = [item.get("location", "") for item in items if item.get("location")]
        patterns["locations"] = list(set(locations))
        
        # 매물 유형 패턴
        types = [item.get("type", "") for item in items if item.get("type")]
        patterns["property_types"] = list(set(types))
        
        # 가격 패턴 (간단한 분류)
        prices = [item.get("price", "") for item in items if item.get("price")]
        patterns["price_ranges"] = list(set(prices))
        
        return patterns

    def _adjust_weights_for_likes(self, patterns: Dict) -> Dict:
        """좋아요 패턴에 따른 가중치 조정"""
        weights = {}
        
        # 위치가 일관되면 위치 가중치 증가
        if len(patterns.get("locations", [])) <= 2:
            weights["location"] = 0.5
            
        # 매물 유형이 일관되면 유형 가중치 증가
        if len(patterns.get("property_types", [])) == 1:
            weights["property_type"] = 0.3
            
        return weights

    def _adjust_weights_for_dislikes(self, patterns: Dict) -> Dict:
        """싫어요 패턴에 따른 가중치 조정"""
        weights = {}
        
        # 특정 위치를 싫어하면 다른 위치 선호
        if patterns.get("locations"):
            weights["location"] = 0.4
            weights["exclude_locations"] = patterns["locations"]
            
        return weights

    def _create_default_analysis(self) -> Dict:
        """기본 분석 결과 생성"""
        return {
            "preference_patterns": {},
            "adjusted_weights": {},
            "needs_rerun": False,
            "feedback_summary": "피드백을 확인했습니다."
        }
