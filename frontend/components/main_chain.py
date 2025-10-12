import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.session_manager import SessionManager

def response_from_chain(messages, memory=None):
    """
    Chain 모드에서 LLM 응답 생성 (스트리밍)
    기존 housing_chain_inha.py의 stream_recommendation 함수 활용
    
    Args:
        messages: 메시지 히스토리 (UI 표시용)
        memory: ConversationSummaryBufferMemory 객체 (LLM이 대화 맥락 이해용)
    """
    try:
        # 기존 LangChain Chain 모듈 import
        from backend.services.llm.langchain.chains.inha.housing_chain_inha import stream_recommendation
        
        # 최신 사용자 메시지 추출
        latest_query = messages[-1]["content"] if messages else ""
        
        # 스트리밍 응답 생성 (메모리 전달)
        for chunk in stream_recommendation(latest_query, memory=memory):
            yield chunk
            
    except ImportError as e:
        yield f"Chain 모듈을 불러올 수 없습니다: {e}"
    except Exception as e:
        yield f"응답 생성 중 오류가 발생했습니다: {e}"

def render_main_chain():
    """MAIN(Chain) 페이지 렌더링"""
    # 페이지 클리어 (캐시 문제 해결)
    st.empty()
    
    st.title("💬 MAIN (Chain)")
    st.caption("LangChain Chain 기반 주택 추천 시스템")
    
    # 디버깅 정보
    st.caption("✅ Chain 페이지가 로드되었습니다.")
    
    # 대화 초기화 버튼
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ 대화 초기화", use_container_width=True):
            SessionManager.clear_messages("chain")
            st.rerun()
    
    with col2:
        st.info("Chain 모드: 빠르고 간단한 주택 검색 (고정 5개 결과)")
    
    ####################################
    # 기존에 저장된 메시지 출력
    ####################################
    messages = SessionManager.get_messages("chain")
    
    for message in messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    
    ####################################
    # 사용자의 메시지(prompt) 입력
    ####################################
    prompt = st.chat_input("주택에 대해 질문해보세요 (예: 서초구 청년주택 추천해줘)")
    
    if isinstance(prompt, str) and prompt.strip():
        # 사용자 메시지 추가
        user_message = {
            "role": "user",
            "content": prompt.strip()
        }
        
        with st.chat_message(user_message["role"]):
            st.markdown(user_message["content"])
        
        # 세션에 사용자 메시지 저장
        SessionManager.add_message("chain", "user", prompt.strip())
        
        ####################################
        # LLM의 답변 (스트리밍)
        ####################################
        with st.chat_message("assistant"):
            # 현재 메시지 히스토리 및 메모리 가져오기
            current_messages = SessionManager.get_messages("chain")
            current_memory = SessionManager.get_memory("chain")
            
            assistant_response = st.write_stream(
                response_from_chain(current_messages, memory=current_memory)
            )
        
        # 어시스턴트 응답을 세션에 저장
        SessionManager.add_message("chain", "assistant", assistant_response)
    
    # 사용 안내
    with st.expander("💡 사용 팁"):
        st.markdown("""
        **Chain 모드 특징:**
        - ⚡ 빠른 응답 속도
        - 🎯 고정된 검색 결과 (5개)
        - 📝 간단한 질문-답변 형태
        
        **질문 예시:**
        - "서초구 청년주택 추천해줘"
        - "강남구 원룸 찾아줘"
        - "지하철역 근처 주택 보여줘"
        """)
    
    # 현재 대화 수 표시
    if messages:
        st.sidebar.metric("현재 대화 수", len([m for m in messages if m["role"] == "user"]))
