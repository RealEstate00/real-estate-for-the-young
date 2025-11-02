"""
Conversation Manager - 대화 히스토리 관리

사용자와의 대화 히스토리를 관리하고 컨텍스트를 유지합니다.

⚠️ 향후 계획: Vector DB 도입 시 간소화 예정
- 현재: 메모리 기반 임시 저장 + 파일 저장
- 향후: Vector DB 연동으로 영구 저장 + 의미적 검색 지원
- 변화: 세션 캐시 관리자 역할로 축소, 저장 로직은 Vector Service로 이관
- 장점: 사용자별 개인화 추천 강화, 유사 사용자 패턴 분석 가능
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """대화 히스토리 관리자"""
    
    def __init__(self, max_history: int = 10):
        """
        Args:
            max_history: 최대 대화 히스토리 개수
        """
        self.max_history = max_history
        self.conversations: List[Dict] = []
    
    def add_user_message(self, message: str, metadata: Optional[Dict] = None) -> None:
        """
        사용자 메시지 추가
        
        Args:
            message: 사용자 메시지
            metadata: 추가 메타데이터
        """
        self.conversations.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        
        self._trim_history()
    
    def add_assistant_message(
        self, 
        message: str, 
        recommendations: List[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        어시스턴트 메시지 추가
        
        Args:
            message: 어시스턴트 응답
            recommendations: 추천 결과
            metadata: 추가 메타데이터
        """
        self.conversations.append({
            "role": "assistant", 
            "content": message,
            "recommendations": recommendations or [],
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        
        self._trim_history()
    
    def add_feedback(self, feedback: Dict) -> None:
        """
        피드백 추가
        
        Args:
            feedback: 사용자 피드백
        """
        self.conversations.append({
            "role": "feedback",
            "content": feedback,
            "timestamp": datetime.now().isoformat()
        })
        
        self._trim_history()
    
    def get_history(self, last_n: Optional[int] = None) -> List[Dict]:
        """
        대화 히스토리 반환
        
        Args:
            last_n: 최근 N개 대화만 반환 (None이면 전체)
            
        Returns:
            대화 히스토리 리스트
        """
        if last_n is None:
            return self.conversations.copy()
        else:
            return self.conversations[-last_n:] if last_n > 0 else []
    
    def get_context_summary(self) -> str:
        """
        대화 컨텍스트 요약 생성
        
        Returns:
            대화 컨텍스트 요약 문자열
        """
        if not self.conversations:
            return "새로운 대화입니다."
        
        user_messages = [
            conv["content"] for conv in self.conversations 
            if conv["role"] == "user"
        ]
        
        if not user_messages:
            return "사용자 메시지가 없습니다."
        
        # 최근 사용자 요청들 요약
        recent_requests = user_messages[-3:]  # 최근 3개
        
        summary = f"최근 요청: {' → '.join(recent_requests)}"
        
        # 피드백 정보 추가
        feedbacks = [
            conv["content"] for conv in self.conversations 
            if conv["role"] == "feedback"
        ]
        
        if feedbacks:
            summary += f" | 피드백: {len(feedbacks)}건"
        
        return summary
    
    def get_user_preferences(self) -> Dict:
        """
        사용자 선호도 추출
        
        Returns:
            추출된 선호도 정보
        """
        preferences = {
            "locations": [],
            "property_types": [],
            "price_preferences": [],
            "feedback_patterns": []
        }
        
        # 사용자 메시지에서 선호도 추출
        for conv in self.conversations:
            if conv["role"] == "user":
                content = conv["content"].lower()
                
                # 지역 선호도
                if "강남" in content:
                    preferences["locations"].append("강남구")
                elif "서초" in content:
                    preferences["locations"].append("서초구")
                elif "송파" in content:
                    preferences["locations"].append("송파구")
                
                # 매물 유형 선호도
                if "원룸" in content:
                    preferences["property_types"].append("원룸")
                elif "투룸" in content:
                    preferences["property_types"].append("투룸")
                elif "오피스텔" in content:
                    preferences["property_types"].append("오피스텔")
        
        # 피드백에서 패턴 추출
        for conv in self.conversations:
            if conv["role"] == "feedback":
                feedback = conv["content"]
                if isinstance(feedback, dict):
                    preferences["feedback_patterns"].append(feedback.get("type", ""))
        
        # 중복 제거
        for key in preferences:
            preferences[key] = list(set(preferences[key]))
        
        return preferences
    
    def clear_history(self) -> None:
        """대화 히스토리 초기화"""
        self.conversations.clear()
        logger.info("대화 히스토리가 초기화되었습니다")
    
    def _trim_history(self) -> None:
        """히스토리 길이 제한"""
        if len(self.conversations) > self.max_history:
            # 오래된 대화 제거 (첫 번째 대화는 유지)
            self.conversations = (
                self.conversations[:1] + 
                self.conversations[-(self.max_history-1):]
            )
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "conversations": self.conversations,
            "max_history": self.max_history
        }
    
    def from_dict(self, data: Dict) -> None:
        """딕셔너리에서 복원"""
        self.conversations = data.get("conversations", [])
        self.max_history = data.get("max_history", 10)
    
    def save_to_file(self, filepath: str) -> None:
        """파일로 저장"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"대화 히스토리 저장 완료: {filepath}")
        except Exception as e:
            logger.error(f"대화 히스토리 저장 실패: {e}")
    
    def load_from_file(self, filepath: str) -> None:
        """파일에서 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.from_dict(data)
            logger.info(f"대화 히스토리 로드 완료: {filepath}")
        except Exception as e:
            logger.error(f"대화 히스토리 로드 실패: {e}")
