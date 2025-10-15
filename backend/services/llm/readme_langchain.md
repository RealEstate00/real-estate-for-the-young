# 주택 추천 LangChain 시스템

## 📌 개요

서울시 청년 주택 검색 및 추천 시스템입니다.
- **2가지 실행 방식**: Chain (단순) vs Agent (똑똑)
- **2가지 LLM 모드**: 단일 (빠름) vs 하이브리드 (정확)

---

## 🔀 실행 방식

### 1. Chain 모드 (단순 파이프라인)
**파일**: `langchain/chains/inha/housing_chain_inha.py`

```python
검색(고정 k=5) → 프롬프트 → LLM → 스트리밍 출력
```

**특징**:
- ✅ 빠르고 간단
- ✅ 스트리밍 지원
- ❌ 고정된 검색 (항상 5개)

**사용 예시**:
```python
from backend.services.llm.langchain.chains.inha.housing_chain_inha import stream_recommendation

for chunk in stream_recommendation("서초구 청년주택"):
    print(chunk, end="", flush=True)
```

---

### 2. Agent 모드 (똑똑한 도구 선택)
**파일**: `langchain/chains/inha/housing_agent_inha.py`

```python
질문 → Agent (도구 선택) → 검색 실행 → 답변 생성
```

**특징**:
- ✅ 사용자 의도 파악 ("모두 보여줘" vs "추천해줘")
- ✅ 동적 검색 조건 변경
- ✅ 확장 가능 (도구 추가)
- ❌ 약간 느림

**사용 예시**:
```python
from backend.services.llm.langchain.chains.inha.housing_agent_inha import housing_assistant

# "모두" 감지 → comprehensive 모드 (20개)
answer = housing_assistant("서초구 주택 모두 보여줘")

# "추천" 감지 → diverse 모드 (5개, MMR)
answer = housing_assistant("강남구 좋은 주택 추천해줘")
```

---

## 🤖 LLM 모드

### 모드 1: 단일 LLM (기본, 추천)
**모델**: Groq `llama-3.3-70b-versatile`

```
모든 작업을 하나의 LLM으로 처리
```

**장점**:
- ⚡ 빠름
- 💰 무료 (Groq 무료 tier)
- 🎯 70B 모델이라 성능 우수

**단점**:
- 없음 (llama-3.3-70b는 충분히 강력)

---

### 모드 2: 하이브리드 LLM (고급)
**Agent**: OpenAI `gpt-4o-mini` (도구 호출)  
**Response**: Groq `llama-3.3-70b-versatile` (답변 생성)

```
질문 → GPT-4o-mini (도구 선택) → Groq (답변 생성)
```

**장점**:
- 🎯 정확한 도구 호출 (GPT-4o-mini)
- ⚡ 빠른 답변 생성 (Groq)
- 💰 비용 효율적

**단점**:
- 🐢 약간 느림 (2단계)
- 💵 OpenAI API 비용 발생

**언제 사용?**:
- 복잡한 멀티스텝 추론 필요
- 여러 도구 조합 필요 
  (향후 확장시 적용하기 좋을 것으로 사료됨)
  (여러 도구 추가하여 Groq모델이 일처리 못하면 하이브리드모드로 변경하여 사용하는 쪽으로 확정하기)
- 프로덕션 환경

---

## ⚙️ 설정 방법

### 1. 환경 변수 설정 (`.env`)

**단일 모드 (기본, 추천)**:
```bash
# API Key
GROQ_API_KEY=gsk_your_key_here 입력

# LLM 모드 설정
.env 파일에서 USE_HYBRID_LLM=False  # 단일 모드
(RESPONSE_MODEL=llama-3.3-70b-versatile)
```

**하이브리드 모드**:
```bash
env.example 하단의 llm 및 api키 부분 복사하여 .env 파일에 붙여넣기
.env 파일에서 USE_HYBRID_LLM=True로 변경 시 하이브리드 모드 활성화
```

### 2. 모드 전환

터미널에서 확인:
```bash
# 로그 출력 확인
⚙️  단일 LLM 모드 (llama-3.3-70b-versatile)  # 기본
# 또는
🔀 하이브리드 LLM 모드 활성화
  ├─ Agent LLM: gpt-4o-mini (OpenAI)
  └─ Response LLM: llama-3.3-70b-versatile (Groq)
```

---

## 🚀 사용 가이드

### Chain 모드 실행
```bash
# 스트리밍 테스트
python -m backend.services.llm.langchain.chains.inha.housing_chain_inha
```


### Agent 모드 실행
```bash
# Agent 테스트
python -m backend.services.llm.langchain.chains.inha.housing_agent_inha
```

**Agent의 똑똑한 판단**:
(prompt_inha.py 파일 참고)
```python
# 질문: "서초구 주택 모두 보여줘"
→ search_housing(query="서초구 주택", search_mode="comprehensive", max_results=20)

# 질문: "강남구 좋은 주택 추천해줘"
→ search_housing(query="강남구 좋은 주택", search_mode="diverse", max_results=5)
```

---

## 💰 비용 비교 (간단 버전)

| 모드 | 모델 | 비용 | 추천도 |
|------|------|------|--------|
| **단일 (추천)** | llama-3.3-70b | 무료* | ⭐⭐⭐⭐⭐ |
| **하이브리드** | gpt-4o-mini + llama-3.3-70b | ~$0.001/회 | ⭐⭐⭐⭐ |

*Groq 무료 tier: 일일 14,400 requests

**실제 비용 예시 (하이브리드)**:
- 월 100회: ~$0.10
- 월 1,000회: ~$1.00
- 월 10,000회: ~$10.00

**결론**: 단일 모드로 시작 → 필요시 하이브리드 전환

---

## 🔧 주요 컴포넌트

```
backend/services/llm/
├── models/inha/
│   └── llm_inha.py              # LLM 설정 (단일/하이브리드)
├── prompts/inha/
│   └── prompt_inha.py           # 프롬프트 템플릿
├── langchain/
│   ├── chains/inha/
│   │   ├── housing_chain_inha.py   # Chain 모드 (스트리밍)
│   │   └── housing_agent_inha.py   # Agent 모드
│   └── retrievers/inha/
│       └── retriever_inha.py       # 벡터 검색 (MMR/유사도)
└── utils/inha/
    ├── housing_tools_inha.py    # Agent 도구 정의
    └── output_parser_inha.py    # 출력 파서
```

---

## 📝 추가 정보

### 검색 모드 (Agent에서 자동 선택)

**Diverse 모드** (기본):
- 유사도 높은 순 정렬
- 기본 5개 결과
- 사용: "추천해줘", "좋은 곳"

**Comprehensive 모드** (전체):
- 유사도 높은 순 정렬
- 기본 20개 결과
- 모든 매칭 결과
- 사용: "모두 보여줘", "전부"

**참고**: 이전 버전의 MMR(Maximal Marginal Relevance)은 제거되었습니다. 주택 검색에서는 "다양성"보다 "관련성"이 더 중요하며, 각 주택이 이미 고유한 매물이기 때문에 유사도 순 정렬이 더 실용적입니다.

### 향후 확장

Agent 모드에 도구 추가 가능:
```python
# 예정된 도구
- calculate_commute_time()  # 통근시간 계산
- filter_by_price()         # 가격 필터링
- get_area_info()           # 지역 정보
```

---

## ❓ FAQ

**Q: Chain vs Agent 어떤 걸 써야 하나요?**  
A: 일반적인 검색 → Chain, 복잡한 조건 → Agent

**Q: 하이브리드 모드가 필요한가요?**  
A: llama-3.3-70b만으로도 충분합니다. 나중에 복잡한 도구가 추가되면 고려하세요.

**Q: MMR 오류가 납니다**  
A: 수정 완료. `.env`에서 `RESPONSE_MODEL=llama-3.3-70b-versatile` 확인

**Q: 비용이 걱정됩니다**  
A: 단일 모드는 Groq 무료 tier로 충분합니다 (일 14,400회)

---

## 🎯 빠른 시작

```bash
# 1. .env 설정
GROQ_API_KEY=your_key
USE_HYBRID_LLM=False

# 2. Chain 모드 테스트 (스트리밍)
python -m backend.services.llm.langchain.chains.inha.housing_chain_inha

# 3. Agent 모드 테스트 (똑똑한 검색)
python -m backend.services.llm.langchain.chains.inha.housing_agent_inha
```

끝! 🚀
