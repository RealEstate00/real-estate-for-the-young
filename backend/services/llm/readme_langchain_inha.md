# 하이브리드 LLM Agent 시스템

## 개요

주택 검색 Agent 시스템으로, **단일 LLM** 또는 **하이브리드 LLM** 모드로 작동합니다.

---

## 작동 모드

### 1. 단일 LLM 모드 (기본)
- **모델**: `gemma2-9b-it` (Groq)
- **사용**: 도구 호출 + 답변 생성 모두 하나의 LLM
- **비용**: 무료 (일일 14,400 requests 한도)
- **장점**: 간단하고 빠름
- **단점**: Tool calling 정확도 낮을 수 있음

### 2. 하이브리드 LLM 모드 (권장)
- **Agent LLM**: `gpt-4o-mini` (OpenAI, 도구 호출 전용)
  - 매우 정확한 tool calling
  - 낮은 temperature (0.3) - 정확성 우선
  - 비용: Input $0.15/1M, Output $0.60/1M tokens
- **Response LLM**: `gemma2-9b-it` (Groq, 답변 생성 전용)
  - 빠른 응답
  - 높은 temperature (0.7) - 자연스러운 답변
  - 비용: Input/Output $0.20/1M tokens (무료 한도 초과 시)
- **장점**: 정확한 도구 호출 + 저렴한 비용
- **단점**: 약간 느림 (2단계 처리)

**대안**: Agent를 `gpt-4o`로 변경 시 최고 품질 (비용 증가)

---

## 설정 방법

### .env 파일
```bash
# API Keys
GROQ_API_KEY=gsk_xxx...
OPENAI_API_KEY=sk-xxx...  # 하이브리드 모드 시 필요

# 하이브리드 모드 활성화/비활성화
USE_HYBRID_LLM=False  # True로 변경 시 하이브리드 활성화

# Agent LLM 설정
AGENT_PROVIDER=openai  # openai 또는 groq
AGENT_MODEL=gpt-4o-mini  # OpenAI 사용 시 (권장)
# AGENT_MODEL=llama-3.1-70b-versatile  # Groq 사용 시

# Response LLM 설정
RESPONSE_MODEL=gemma2-9b-it  # Groq (무료/저렴)
```

---

## 사용 예시

### 기본 사용
```python
from backend.services.llm.langchain.agents.inha.housing_agent_inha import recommend_housing

# 사용자 질문에 자동으로 응답
answer = recommend_housing("강남구 청년주택 모두 보여줘")
print(answer)
```

### Agent의 자동 판단

#### 예시 1: "모두" 키워드 감지
```python
질문: "강남구 청년주택 모두 보여줘"

Agent 판단:
→ search_housing(
    query="강남구 청년주택",
    search_mode="comprehensive",  # "모두" 감지
    max_results=20
  )
```

#### 예시 2: 다양한 옵션 추천
```python
질문: "강남구 근처 좋은 주택 추천해줘"

Agent 판단:
→ search_housing(
    query="강남구 좋은 주택",
    search_mode="diverse",  # 다양성 우선
    max_results=5
  )
```

---

## 실행 흐름

### 단일 LLM 모드 (USE_HYBRID_LLM=False)
```
사용자 질문
    ↓
gemma2-9b-it (Agent)
    ├─ 도구 호출 결정
    ├─ search_housing 실행
    └─ 결과 바탕 답변 생성
    ↓
최종 답변
```

### 하이브리드 모드 (USE_HYBRID_LLM=True)
```
사용자 질문
    ↓
gpt-4o-mini (Agent LLM, OpenAI)
    ├─ 도구 호출 결정 (매우 정확)
    └─ search_housing 실행
    ↓
검색 결과
    ↓
gemma2-9b-it (Response LLM, Groq)
    └─ 친절한 답변 생성 (빠름)
    ↓
최종 답변
```

---

## 현재 사용 가능한 도구

### search_housing
주택 검색 도구

**파라미터:**
- `query` (str): 검색 쿼리
- `search_mode` (str):
  - `"diverse"`: 다양한 옵션 탐색 (MMR 사용, 기본 5개)
  - `"comprehensive"`: 모든 결과 검색 (유사도만, 기본 20개)
- `max_results` (int, optional): 최대 결과 수

**Agent의 자동 선택 기준:**
- "모두", "전부", "모든", "전체" → `comprehensive`
- "추천", "좋은", "괜찮은" → `diverse`

---

## 향후 확장 계획

### 추가 예정 도구

```python
# 1. 통근시간 계산
@tool
def calculate_commute_time(start_address: str, housing_address: str) -> int:
    """KakaoMap API로 통근시간 계산 (분 단위)"""
    pass

# 2. 통근시간 필터링
@tool
def filter_by_commute(housings: List, max_minutes: int) -> List:
    """통근시간으로 주택 필터링"""
    pass
```

### 확장 시나리오
```python
질문: "회사 주소는 강남역이야. 1시간 이내로 출퇴근 가능한 청년주택 찾아줘"

Agent의 자동 추론:
1. search_housing("청년주택", search_mode="comprehensive")
2. calculate_commute_time("강남역", 각 주택 주소)
3. filter_by_commute(주택리스트, max_minutes=60)
4. 최종 답변 생성
```

---

## 언제 하이브리드 모드를 사용할까?

### 하이브리드 활성화 권장:
- ✅ 복잡한 도구 조합 필요 (KakaoMap API + 검색 등)
- ✅ Tool calling 정확도가 중요
- ✅ 프로덕션 환경

### 단일 LLM으로 충분:
- ✅ 단순 주택 검색만
- ✅ 개발/테스트 환경
- ✅ 비용 절감 최우선

---

## 비용 비교

### 무료 한도 (Groq)
- 일일 14,400 requests/day
- 분당 30 requests/minute
- 초과 시 유료: gemma2-9b-it ($0.20/1M tokens)

### 월별 비용 예시 (무료 한도 초과 시)

| 모드 | Agent | Response | 1회 비용 | 월 100회 | 월 500회 | 추천도 |
|------|-------|----------|---------|---------|---------|-------|
| **단일 Groq** | gemma2-9b | gemma2-9b | 무료* | 무료* | 무료* | ⭐⭐⭐ |
| **하이브리드 (추천)** | gpt-4o-mini | gemma2-9b | $0.000375 | $1.13 | $5.63 | ⭐⭐⭐⭐⭐ |
| **GPT-4o 하이브리드** | gpt-4o | gpt-4o-mini | $0.00261 | $7.83 | $39.15 | ⭐⭐⭐⭐ |
| **단일 GPT-4o-mini** | gpt-4o-mini | gpt-4o-mini | $0.000495 | $1.49 | $7.43 | ⭐⭐⭐⭐ |

*무료 한도(일 14,400회) 내 사용 시

### 100달러로 사용 가능 기간

| 모드 | 월 100회 | 월 500회 | 월 1,000회 |
|------|----------|----------|-----------|
| 하이브리드 (GPT-4o-mini + Groq) | 88개월 (7년) | 17개월 | 8.8개월 |
| GPT-4o + GPT-4o-mini | 12개월 | 2.5개월 | 1.3개월 |

**결론**:
- **개발/테스트**: 단일 Groq (무료)
- **프로덕션**: 하이브리드 GPT-4o-mini + Groq (월 $1-5)
- **최고 품질**: GPT-4o + GPT-4o-mini (월 $7-39)
