"""
LLM 모델 설정 - Fallback 체인 패턴
- 자동 백업: Groq → HuggingFace → OpenAI
- 무료 토큰 소진 시 자동 모델 전환
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
<<<<<<<< Updated upstream:backend/services/llm/inha/models/llm.py
# from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
# from transformers import pipeline
========
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import pipeline
import transformers
import torch 

>>>>>>>> Stashed changes:backend/services/llm/inha/models/inha/llm_inha.py

# 환경 변수 로드
load_dotenv()
# GPU 있으면 GPU(양수), 없으면 CPU(0,음수)
device = 0 if torch.cuda.is_available() else -1


# 기본llm 모드 설정
FORCE_LLM_PROVIDER = os.getenv("FORCE_LLM_PROVIDER", "huggingface")  # groq, huggingface, openai 등 .env파일에서 설정하면 됨
# 하이브리드 모드 설정
# USE_HYBRID = os.getenv("USE_HYBRID_LLM", "false").lower() == "true"
# 하이브리드 모드 설정 (비활성화)
USE_HYBRID = False


openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=1000,
    api_key=os.getenv("OPENAI_API_KEY")
)

groq_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.5,
    max_tokens=2000,
    api_key=os.getenv("GROQ_API_KEY")
)

# 공식 문서 방식으로 수정 - transformers.pipeline 직접 사용
# 로컬 CPU용 경량 모델 선택 (한국어 지원)
MODEL_CHOICES = {
    "korean_electra": "beomi/KcELECTRA-base",  # 한국어 ELECTRA (추천)
    "korean_bert": "beomi/KcBERT-base",        # 한국어 BERT
    "klue_roberta": "klue/roberta-base",       # KLUE 한국어 모델
    "dialogpt": "microsoft/DialoGPT-small",    # 대화형 생성
    "gpt2": "gpt2",                            # 기본 GPT-2
    "distilgpt2": "distilgpt2",                # 경량 GPT-2
}

# 사용할 모델 직접 선택 (코드에서 설정)
SELECTED_MODEL = "korean_electra"  # 원하는 모델로 변경 가능
model_name = MODEL_CHOICES.get(SELECTED_MODEL, MODEL_CHOICES["korean_electra"])

print(f"🔄 로컬 CPU 모델 로딩: {model_name}")

# 공식 문서 방식으로 pipeline 생성 (CPU 최적화)
hf_pipeline = transformers.pipeline(
    "text-generation",
    model=model_name,
    model_kwargs={
        "torch_dtype": torch.float32,  # CPU용 float32 사용
        "use_auth_token": os.getenv("HUGGINGFACEHUB_API_TOKEN")  # HuggingFace 토큰 추가
        #"device_map": "cpu",           # CPU 강제 사용
    },
    cache_dir=".\backend\data\models\hf",  # 모델이 저장될 폴더 지정
)

# 공식 문서처럼 eval 모드 설정
hf_pipeline.model.eval()
# HuggingFace pipeline 객체를 그냥 전달하면 langchain 에서 직접 지원하는 인터페이스와 다를 수 있으므로,
# HuggingFacePipeline으로 한 번 래핑(wrap)해서 전달해야 ChatHuggingFace에서 일관된 LLM interface로 사용할 수 있다.
# 즉, HuggingFacePipeline은 transformers의 pipeline을 langchain의 LLM 객체로 변환해주는 어댑터 역할을 한다.
huggingface_llm = ChatHuggingFace(
    llm=HuggingFacePipeline(pipeline=hf_pipeline)
    )


<<<<<<<< Updated upstream:backend/services/llm/inha/models/llm.py
openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=2000,
    api_key=os.getenv("OPENAI_API_KEY")
)
========
>>>>>>>> Stashed changes:backend/services/llm/inha/models/inha/llm_inha.py



def _create_specific_model(provider):
    """특정 제공자의 모델 생성"""
    if provider == 'groq':
        return groq_llm
    # elif provider == 'huggingface':
    #     return huggingface_llm
    elif provider == 'openai':
        return openai_llm
    else:
        raise ValueError(f"지원하지 않는 제공자: {provider}")

def create_llm(force_provider=None):
    """모델 제공자 강제 지정 또는 자동 선택"""
    
    if force_provider:
        print(f"🔄 {force_provider} 모델 강제 사용")
        return _create_specific_model(force_provider)
    
    # 자동 선택: Groq → OpenAI (HuggingFace 제외)
    providers = ['groq', 'openai']
    
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
    """Groq → OpenAI 자동 전환 (HuggingFace 제외)"""
    
    # 1차: Groq 시도
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            print("🔄 Groq 모델 연결 시도...")
            return groq_llm
    except Exception as e:
        print(f"⚠️ Groq 연결 실패: {e}")
    
    # 2차: OpenAI 백업
    try:
        print("🔄 OpenAI 백업 모델 연결 시도...")
        return openai_llm
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
    """토큰 한도 도달 시 OpenAI로 전환"""
    print("🔄 토큰 한도 도달, OpenAI로 전환...")
    global llm, agent_llm, response_llm
    
    try:
        new_llm = create_llm('openai')
        llm = new_llm
        agent_llm = new_llm
        response_llm = new_llm
        print("✅ OpenAI 모델로 전환 완료")
        return llm
    except Exception as e:
        print(f"❌ OpenAI 전환 실패: {e}")
        raise
