import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from components.main_chain import render_main_chain
from components.main_agent import render_main_agent
from utils.session_manager import SessionManager

# 페이지 설정
st.set_page_config(
    page_title="청년을 위한 부동산",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
SessionManager.init_session()

# 사이드바 메뉴
st.sidebar.title("🏠 청년을 위한 부동산")

# 사이드바 메뉴 구성
menu_options = {
    "🏠 HOME": "home",
    "💬 MAIN (Chain)": "main_chain",
    "🤖 MAIN (Agent)": "main_agent", 
}

# 메뉴 선택
if 'current_page' not in st.session_state:
    st.session_state.current_page = "home"

selected_menu = st.sidebar.radio(
    "메뉴",
    options=list(menu_options.keys()),
    index=list(menu_options.values()).index(st.session_state.current_page)
)

# 선택된 페이지 업데이트
st.session_state.current_page = menu_options[selected_menu]

# 구분선
st.sidebar.markdown("---")

# 사이드바 정보
st.sidebar.markdown("### 💡 모드 설명")
st.sidebar.info("""
**Chain 모드**
- ⚡ 빠른 응답
- 📝 고정 검색 (5개)

**Agent 모드**
- 🧠 똑똑한 도구 선택
- 🎯 맞춤형 검색 (동적)
""")

# =============================================================================
# 페이지 라우팅
# =============================================================================

if st.session_state.current_page == "home":
    # Home Page - 메인 랜딩 페이지
    
    # 상단 여백
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # REY 타이틀 (중앙, 큰 글씨, 굵게)
    st.markdown(
        """
        <h1 style='text-align: center; font-size: 120px; font-weight: bold; color: #1E3A8A; margin-bottom: 50px;'>
            REY
        </h1>
        """, 
        unsafe_allow_html=True
    )
    
    # 메인 메시지 (중앙, 얇은 글씨)
    st.markdown(
        """
        <div style='text-align: center; font-size: 28px; font-weight: 300; line-height: 1.8; color: #4B5563; margin-bottom: 40px;'>
            집은 단순히 머무는 공간이 아니라<br>
            나의 취향과 일상을 담아내는<br>
            삶의 무대 입니다
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 하단 메시지 (중앙, 굵은 글씨)
    st.markdown(
        """
        <div style='text-align: center; font-size: 32px; font-weight: bold; color: #1E3A8A; margin-top: 50px;'>
            나에게 맞는 집을 찾는 여정을 함께 합니다
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 버튼 영역 (중앙 정렬)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col2:
        if st.button("💬 Chain 모드 시작", use_container_width=True, type="secondary"):
            st.session_state.current_page = "main_chain"
            st.rerun()
    
    with col4:
        if st.button("🤖 Agent 모드 시작", use_container_width=True, type="primary"):
            st.session_state.current_page = "main_agent"
            st.rerun()
    
    # 하단 추가 정보
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # 3단 컬럼으로 특징 표시
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>🏠 서울시 청년주택</h3>
            <p style='color: #6B7280; font-size: 16px;'>
            서울시 전역의<br>
            청년 주택 정보 제공
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with info_col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>🤖 AI 추천</h3>
            <p style='color: #6B7280; font-size: 16px;'>
            LangChain 기반<br>
            맞춤형 주택 추천
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with info_col3:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>💬 대화형 검색</h3>
            <p style='color: #6B7280; font-size: 16px;'>
            자연어로 질문하고<br>
            실시간 답변 받기
            </p>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "main_chain":
    # Chain 모드 페이지
    render_main_chain()

elif st.session_state.current_page == "main_agent":
    # Agent 모드 페이지
    render_main_agent()
