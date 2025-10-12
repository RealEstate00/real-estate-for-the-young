import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.session_manager import SessionManager

def response_from_agent(messages, memory=None):
    """
    Agent 모드에서 LLM 응답 생성
    기존 housing_agent_inha.py의 housing_assistant 함수 활용
    
    Args:
        messages: 메시지 히스토리 (UI 표시용)
        memory: ConversationSummaryBufferMemory 객체 (LLM이 대화 맥락 이해용)
    """
    try:
        # 기존 LangChain Agent 모듈 import
        from backend.services.llm.langchain.chains.inha.housing_agent_inha import housing_assistant
        
        # 최신 사용자 메시지 추출
        latest_query = messages[-1]["content"] if messages else ""
        
        # Agent 응답 생성 (메모리 전달)
        response = housing_assistant(latest_query, memory=memory)
        
        # 스트리밍 효과를 위해 문자 단위로 yield
        for char in response:
            yield char
            
    except ImportError as e:
        yield f"Agent 모듈을 불러올 수 없습니다: {e}"
    except Exception as e:
        yield f"응답 생성 중 오류가 발생했습니다: {e}"

def render_main_agent():
    """MAIN(Agent) 페이지 렌더링"""
    # 페이지 클리어 (캐시 문제 해결)
    st.empty()
    
    st.title("🤖 MAIN (Agent)")
    st.caption("LangChain Agent 기반 지능형 주택 추천 시스템")
    
    # 디버깅 정보
    st.caption("✅ Agent 페이지가 로드되었습니다.")
    
    # 대화 초기화 버튼
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ 대화 초기화", use_container_width=True):
            SessionManager.clear_messages("agent")
            st.rerun()
    
    with col2:
        st.info("Agent 모드: 똑똑한 도구 선택으로 맞춤형 검색 (동적 결과)")
    
    ####################################
    # 기존에 저장된 메시지 출력
    ####################################
    messages = SessionManager.get_messages("agent")
    
    for message in messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    
    ####################################
    # 사용자의 메시지(prompt) 입력
    ####################################
    prompt = st.chat_input("주택에 대해 질문해보세요 (예: 홍대역 근처 주택 모두 보여줘)")
    
    if isinstance(prompt, str) and prompt.strip():
        # 사용자 메시지 추가
        user_message = {
            "role": "user",
            "content": prompt.strip()
        }
        
        with st.chat_message(user_message["role"]):
            st.markdown(user_message["content"])
        
        # 세션에 사용자 메시지 저장
        SessionManager.add_message("agent", "user", prompt.strip())
        
        ####################################
        # LLM의 답변 (Agent 모드)
        ####################################
        with st.chat_message("assistant"):
            # 현재 메시지 히스토리 및 메모리 가져오기
            current_messages = SessionManager.get_messages("agent")
            current_memory = SessionManager.get_memory("agent")
            
            # 로딩 표시
            with st.spinner("Agent가 최적의 도구를 선택하고 있습니다..."):
                assistant_response = st.write_stream(
                    response_from_agent(current_messages, memory=current_memory)
                )
        
        # 어시스턴트 응답을 세션에 저장
        SessionManager.add_message("agent", "assistant", assistant_response)
    
    # 사용 안내
    with st.expander("💡 사용 팁"):
        st.markdown("""
        **Agent 모드 특징:**
        - 🧠 사용자 의도 파악 ("모두" vs "추천")
        - 🔧 동적 도구 선택 및 검색 조건 변경
        - 📊 다양한 검색 모드 (comprehensive/diverse)
        - 🎯 맞춤형 결과 제공
        
        **질문 예시:**
        - "서초구 주택 **모두** 보여줘" → 20개 결과
        - "강남구 좋은 주택 **추천**해줘" → 5개 추천
        - "지하철 2호선 근처 원룸 찾아줘"
        - "예산 50만원 이하 주택 있어?"
        """)
    
    # Agent 상태 정보
    with st.expander("🔧 Agent 정보"):
        try:
            from backend.services.llm.models.inha.llm_inha import USE_HYBRID
            
            if USE_HYBRID:
                st.markdown("""
                **현재 설정 (하이브리드 모드):**
                - 🤖 Agent LLM: OpenAI gpt-4o-mini (도구 호출)
                - 💬 Response LLM: Groq llama-3.3-70b-versatile (답변 생성)
                - 🛠️ 사용 가능한 도구: 주택 검색
                - 🔄 최대 반복: 5회
                - ⚙️ 모드: 하이브리드 (2단계 처리)
                """)
            else:
                st.markdown("""
                **현재 설정 (단일 모드):**
                - 🤖 LLM: Groq llama-3.3-70b-versatile
                - 🛠️ 사용 가능한 도구: 주택 검색
                - 🔄 최대 반복: 5회
                - ⚙️ 모드: 단일 LLM (빠른 처리)
                """)
        except ImportError:
            st.markdown("""
            **설정 정보를 불러올 수 없습니다.**
            - 🛠️ 사용 가능한 도구: 주택 검색
            - 🔄 최대 반복: 5회
            """)
    
    # 현재 대화 수 표시
    if messages:
        st.sidebar.metric("현재 대화 수", len([m for m in messages if m["role"] == "user"]))