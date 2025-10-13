import streamlit as st
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class SessionManager:
    """Streamlit 세션 상태 관리 클래스"""
    
    @staticmethod
    def init_session():
        """세션 상태 초기화"""

        # Chain 모드: UI 메시지
        if 'chain_messages' not in st.session_state:
            st.session_state.chain_messages = []
        
        # Chain 모드: LLM 메모리 (대화 맥락 관리)
        if 'chain_memory' not in st.session_state:
            st.session_state.chain_memory = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
            
        # Agent 모드: UI 메시지
        if 'agent_messages' not in st.session_state:
            st.session_state.agent_messages = []
        
        # Agent 모드: LLM 메모리 (대화 맥락 관리)
        if 'agent_memory' not in st.session_state:
            st.session_state.agent_memory = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
            
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
            

    
    @staticmethod
    def add_message(message_type: str, role: str, content: str):
        """메시지 추가 (chain 또는 agent)"""
        message = {
            "role": role,
            "content": content
        }
        
        if message_type == "chain":
            st.session_state.chain_messages.append(message)
        elif message_type == "agent":
            st.session_state.agent_messages.append(message)
    
    @staticmethod
    def get_messages(message_type: str):
        """메시지 히스토리 가져오기 (UI 표시용)"""
        if message_type == "chain":
            return st.session_state.chain_messages
        elif message_type == "agent":
            return st.session_state.agent_messages
        return []
    
    @staticmethod
    def get_memory(message_type: str):
        """LangChain 메모리 객체 가져오기 (LLM이 사용)"""
        if message_type == "chain":
            return st.session_state.chain_memory
        elif message_type == "agent":
            return st.session_state.agent_memory
        return None
    
    @staticmethod
    def clear_messages(message_type: str):
        """메시지 히스토리 및 메모리 초기화"""
        if message_type == "chain":
            st.session_state.chain_messages = []
            # 메모리도 초기화
            if 'chain_memory' in st.session_state:
                st.session_state.chain_memory.clear()
                
        elif message_type == "agent":
            st.session_state.agent_messages = []
            # 메모리도 초기화
            if 'agent_memory' in st.session_state:
                st.session_state.agent_memory.clear()

