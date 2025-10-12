import streamlit as st
from typing import List, Dict
import json
from datetime import datetime
from pathlib import Path

# Hugging Face Transformers는 선택적 import (설치되지 않은 경우 대비)
try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class ConversationSummarizer:
    """대화 요약 및 저장 관리 클래스"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.conversations_file = self.data_dir / "conversations.json"
        
        # Hugging Face 요약 모델 초기화 (캐시 사용)
        if TRANSFORMERS_AVAILABLE:
            self._init_summarizer()
        else:
            self.summarizer = None
    
    @st.cache_resource
    def _init_summarizer(_self):
        """요약 모델 초기화 (Streamlit 캐시 사용)"""
        try:
            # GPU 사용 가능 여부 확인
            device = 0 if torch.cuda.is_available() else -1
            
            # BART 모델 사용 (한국어 지원 개선된 모델로 변경 가능)
            summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=device,
                max_length=150,
                min_length=30,
                do_sample=False
            )
            return summarizer
        except Exception as e:
            st.error(f"요약 모델 초기화 실패: {e}")
            return None
    
    def summarize_conversation(self, messages: List[Dict[str, str]], conversation_type: str = "general") -> str:
        """
        대화 내용을 요약합니다.
        
        Args:
            messages: 대화 메시지 리스트 [{"role": "user/assistant", "content": "..."}]
            conversation_type: 대화 유형 ("chain" 또는 "agent")
        
        Returns:
            요약된 텍스트
        """
        if not messages:
            return "대화 내용이 없습니다."
        
        # 대화 내용을 하나의 텍스트로 결합
        conversation_text = self._format_conversation(messages)
        
        # Transformers 사용 가능한 경우 AI 요약
        if TRANSFORMERS_AVAILABLE and self.summarizer:
            try:
                # 텍스트 길이 제한 (BART 모델 한계)
                if len(conversation_text) > 1000:
                    conversation_text = conversation_text[:1000] + "..."
                
                summary_result = self.summarizer(conversation_text)
                summary = summary_result[0]['summary_text']
                
                # 한국어 후처리 (필요시)
                summary = self._post_process_summary(summary, conversation_type)
                
            except Exception as e:
                st.warning(f"AI 요약 실패, 간단 요약 사용: {e}")
                summary = self._simple_summary(messages, conversation_type)
        else:
            # Transformers 미사용 시 간단한 규칙 기반 요약
            summary = self._simple_summary(messages, conversation_type)
        
        return summary
    
    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """대화를 하나의 텍스트로 포맷팅"""
        formatted_parts = []
        
        for msg in messages:
            role = "사용자" if msg["role"] == "user" else "어시스턴트"
            content = msg["content"][:200]  # 각 메시지 200자 제한
            formatted_parts.append(f"{role}: {content}")
        
        return " ".join(formatted_parts)
    
    def _simple_summary(self, messages: List[Dict[str, str]], conversation_type: str) -> str:
        """간단한 규칙 기반 요약"""
        user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
        
        if not user_messages:
            return "사용자 질문이 없는 대화"
        
        # 첫 번째와 마지막 사용자 질문 기반 요약
        first_question = user_messages[0][:50]
        last_question = user_messages[-1][:50] if len(user_messages) > 1 else None
        
        mode_text = "Chain 모드" if conversation_type == "chain" else "Agent 모드"
        
        if last_question and last_question != first_question:
            return f"{mode_text}에서 '{first_question}'부터 '{last_question}'까지 {len(user_messages)}개 질문에 대한 주택 상담"
        else:
            return f"{mode_text}에서 '{first_question}'에 대한 주택 상담"
    
    def _post_process_summary(self, summary: str, conversation_type: str) -> str:
        """요약 후처리"""
        mode_text = "Chain 모드" if conversation_type == "chain" else "Agent 모드"
        
        # 모드 정보 추가
        if mode_text not in summary:
            summary = f"[{mode_text}] {summary}"
        
        return summary
    
    def save_conversation(self, messages: List[Dict[str, str]], conversation_type: str, user_info: Dict[str, str] = None) -> str:
        """
        대화를 요약하고 저장합니다.
        
        Returns:
            생성된 요약 텍스트
        """
        if not messages:
            return ""
        
        # 요약 생성
        summary = self.summarize_conversation(messages, conversation_type)
        
        # 저장할 데이터 구성
        conversation_data = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "type": conversation_type,
            "summary": summary,
            "message_count": len(messages),
            "user_message_count": len([m for m in messages if m["role"] == "user"]),
            "user_info": user_info or {},
            "messages": messages  # 전체 대화 내용도 저장
        }
        
        # 기존 대화 기록 로드
        conversations = self._load_conversations()
        conversations.append(conversation_data)
        
        # 파일에 저장
        self._save_conversations(conversations)
        
        return summary
    
    def _load_conversations(self) -> List[Dict]:
        """저장된 대화 기록 로드"""
        if not self.conversations_file.exists():
            return []
        
        try:
            with open(self.conversations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"대화 기록 로드 실패: {e}")
            return []
    
    def _save_conversations(self, conversations: List[Dict]):
        """대화 기록 저장"""
        try:
            with open(self.conversations_file, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"대화 기록 저장 실패: {e}")
    
    def get_conversation_history(self) -> List[Dict]:
        """저장된 대화 기록 반환"""
        return self._load_conversations()
    
    def delete_conversation(self, conversation_id: str):
        """특정 대화 기록 삭제"""
        conversations = self._load_conversations()
        conversations = [c for c in conversations if c.get("id") != conversation_id]
        self._save_conversations(conversations)

# 전역 인스턴스
@st.cache_resource
def get_summarizer():
    """요약기 싱글톤 인스턴스 반환"""
    return ConversationSummarizer()

