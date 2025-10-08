"""
LLM 모델 설정
- 단일 모드: Groq gemma2-9b-it
- 하이브리드 모드: OpenAI GPT-4o-mini (Agent) + Groq gemma2-9b-it (Response)
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

# 환경 변수 로드
load_dotenv()

# API 키
groq_api_key = os.getenv("GROQ_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# 하이브리드 모드 설정
USE_HYBRID = os.getenv("USE_HYBRID_LLM", "False").lower() == "true"
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")  # OpenAI 기본값
AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "openai")  # openai or groq
RESPONSE_MODEL = os.getenv("RESPONSE_MODEL", "gemma2-9b-it")

# LLM 모델 설정
print("LLM 모델 연결 중...")

# Groq API 키 체크
if not groq_api_key:
    print("❌ GROQ_API_KEY가 설정되지 않았습니다.")
    print("Groq 계정에서 API 키를 발급받아 .env 파일에 설정해주세요.")
    print("토큰 발급: https://console.groq.com/keys")
    raise ValueError("Groq API 키가 필요합니다.")

print(f"✅ Groq API 키 발견: {groq_api_key[:10]}...")

# 하이브리드 모드에서 OpenAI 사용 시 API 키 체크
if USE_HYBRID and AGENT_PROVIDER == "openai":
    if not openai_api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("OpenAI 계정에서 API 키를 발급받아 .env 파일에 설정해주세요.")
        print("토큰 발급: https://platform.openai.com/api-keys")
        raise ValueError("OpenAI API 키가 필요합니다.")
    print(f"✅ OpenAI API 키 발견: {openai_api_key[:10]}...")

# LLM 인스턴스 생성
try:
    # 기본 LLM (단일 모드용 - Groq)
    llm = ChatGroq(
        model="gemma2-9b-it",
        temperature=0.5,
        max_tokens=1000,
        api_key=groq_api_key
    )

    # 하이브리드 모드 설정
    if USE_HYBRID:
        print(f"🔀 하이브리드 LLM 모드 활성화")

        # Agent LLM (도구 호출 전용)
        if AGENT_PROVIDER == "openai":
            agent_llm = ChatOpenAI(
                model=AGENT_MODEL,
                temperature=0.3,  # 낮은 temperature: 정확한 도구 호출
                max_tokens=2000,
                api_key=openai_api_key
            )
            print(f"  ├─ Agent LLM: {AGENT_MODEL} (OpenAI)")
        else:
            agent_llm = ChatGroq(
                model=AGENT_MODEL,
                temperature=0.3,
                max_tokens=2000,
                api_key=groq_api_key
            )
            print(f"  ├─ Agent LLM: {AGENT_MODEL} (Groq)")

        # Response LLM (답변 생성 전용 - 항상 Groq)
        response_llm = ChatGroq(
            model=RESPONSE_MODEL,
            temperature=0.7,  # 높은 temperature: 자연스러운 답변
            max_tokens=1000,
            api_key=groq_api_key
        )
        print(f"  └─ Response LLM: {RESPONSE_MODEL} (Groq)")
    else:
        print(f"⚙️  단일 LLM 모드 (gemma2-9b-it)")
        # 단일 모드: 모든 LLM을 기본 llm으로 설정
        agent_llm = llm
        response_llm = llm

    print("✅ LLM 설정 완료!")

except Exception as e:
    print(f"❌ LLM 생성 실패: {e}")
    raise
