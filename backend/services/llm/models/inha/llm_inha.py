"""
LLM 모델 설정 - Fallback 체인 패턴
- 자동 백업: Groq → HuggingFace → OpenAI
- 무료 토큰 소진 시 자동 모델 전환
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import pipeline

# 환경 변수 로드
load_dotenv()

# 기본llm 모드 설정
FORCE_LLM_PROVIDER = os.getenv("FORCE_LLM_PROVIDER", "openai")  # groq, huggingface, openai 등 .env파일에서 설정하면 됨

# 하이브리드 모드 설정
USE_HYBRID = os.getenv("USE_HYBRID_LLM", "false").lower() == "true"



groq_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.5,
    max_tokens=800,
    api_key=os.getenv("GROQ_API_KEY")
)


# 좋은 모델 써보려하니 안됨. 왜 그런지 물어보기
# hf_pipeline = pipeline(
#     "text-generation",
#     model="MLP-KTLim/llama-3-Korean-Bllossom-8B",
#     max_new_tokens=1000,
#     temperature=0.7,
#     return_full_text=False,
#     truncation=True,
#     max_length=8192,  # 모델의 max_position_embeddings(실제 최대 토큰 길이)에 맞춤
#     do_sample=True,
#     top_p=0.9,
#     repetition_penalty=1.1,
#     # 특별한 토큰 설정
#     pad_token_id=128009,  # eos_token_id 사용
#     eos_token_id=128009,
#     bos_token_id=128000,
#     # 데이터 타입 설정 - 모델의 데이터 타입 맞춤 
#     torch_dtype="bfloat16",
#     # 메모리 최적화
#     device_map="auto", # 메모리 자동 관리
#     low_cpu_mem_usage=True
# )

# HuggingFace pipeline 객체를 그냥 전달하면 langchain 에서 직접 지원하는 인터페이스와 다를 수 있으므로,
# HuggingFacePipeline으로 한 번 래핑(wrap)해서 전달해야 ChatHuggingFace에서 일관된 LLM interface로 사용할 수 있다.
# 즉, HuggingFacePipeline은 transformers의 pipeline을 langchain의 LLM 객체로 변환해주는 어댑터 역할을 한다.
# huggingface_llm = ChatHuggingFace(
#     llm=HuggingFacePipeline(pipeline=hf_pipeline)
# )

openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=1000,
    api_key=os.getenv("OPENAI_API_KEY")
)



def _create_specific_model(provider):
    """특정 제공자의 모델 생성"""
    if provider == 'groq':
        return groq_llm
    elif provider == 'huggingface':
        return huggingface_llm
    elif provider == 'openai':
        return openai_llm
    else:
        raise ValueError(f"지원하지 않는 제공자: {provider}")

def create_llm(force_provider=None):
    """모델 제공자 강제 지정 또는 자동 선택"""
    
    if force_provider:
        print(f"🔄 {force_provider} 모델 강제 사용")
        return _create_specific_model(force_provider)
    
    # 자동 선택: Groq → HuggingFace → OpenAI
    providers = ['groq', 'huggingface', 'openai']
    
    for provider in providers:
        try:
            print(f"🔄 {provider} 모델 연결 시도...")
            model = _create_specific_model(provider)
            print(f"✅ {provider} 모델 연결 성공")
            return model
        except Exception as e:
            print(f"⚠️ {provider} 모델 연결 실패: {e}")
            continue
    
    raise ValueError("사용 가능한 모델이 없습니다")

def create_llm_with_fallback():
    """Groq → HuggingFace 자동 전환"""
    
    # 1차: Groq 시도
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            print("🔄 Groq 모델 연결 시도...")
            return groq_llm
    except Exception as e:
        print(f"⚠️ Groq 연결 실패: {e}")
    
    # 2차: HuggingFace 백업
    try:
        print("🔄 HuggingFace 백업 모델 연결 시도...")
        return huggingface_llm
    except Exception as e:
        print(f"❌ 모든 모델 연결 실패: {e}")
        raise

# LLM 모델 설정
print("LLM 모델 연결 중...")

# 기본 LLM 생성 (자동 백업 포함)
llm = create_llm(FORCE_LLM_PROVIDER)

# 하이브리드 모드 설정
if USE_HYBRID:
    print(f"🔀 하이브리드 LLM 모드 활성화")
    
    # Agent LLM (도구 호출 전용) - OpenAI 우선
    try:
        agent_llm = openai_llm
        print(f"  ├─ Agent LLM: gpt-4o-mini (OpenAI)")
    except Exception as e:
        print(f"⚠️ OpenAI Agent LLM 실패, Groq 사용: {e}")
        agent_llm = llm
        print(f"  ├─ Agent LLM: llama-3.3-70b-versatile (Groq)")
    
    # Response LLM (답변 생성 전용) - 기본 LLM 사용
    response_llm = llm
    print(f"  └─ Response LLM: {llm.__class__.__name__}")
else:
    print(f"⚙️  단일 LLM 모드")
    # 단일 모드: 모든 LLM을 기본 llm으로 설정
    agent_llm = llm
    response_llm = llm

print("✅ LLM 설정 완료!")

# 토큰 부족 감지 시 모델 전환 함수
def handle_token_limit_exceeded():
    """토큰 한도 도달 시 HuggingFace로 전환"""
    print("🔄 토큰 한도 도달, HuggingFace로 전환...")
    global llm, agent_llm, response_llm
    
    try:
        new_llm = create_llm('huggingface')
        llm = new_llm
        agent_llm = new_llm
        response_llm = new_llm
        print("✅ HuggingFace 모델로 전환 완료")
        return llm
    except Exception as e:
        print(f"❌ HuggingFace 전환 실패: {e}")
        raise
