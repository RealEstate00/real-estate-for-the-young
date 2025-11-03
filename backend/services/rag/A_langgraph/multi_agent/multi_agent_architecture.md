# Multi-Agent LangGraph 추천 시스템 아키텍처 설계

## 개요

이 문서는 LangGraph와 Multi-Agent 시스템을 활용한 **대화형 주거 매물 추천 시스템** 설계를 다룹니다. 전문화된 에이전트들이 협업하여 사용자 선호도를 파악하고, 복잡한 다단계 추론을 통해 최적의 매물을 추천하는 시스템입니다.

**핵심 특징:**
- ✅ **대화형 추천**: 사용자와 대화하며 선호도 파악
- ✅ **복잡한 다단계 추론**: 여러 단계를 거쳐 정확한 추천 생성
- ✅ **여러 데이터 소스 동적 통합**: 주택, 인프라, 대출 정책, 실거래가 등 실시간 통합
- ✅ **사용자 피드백 실시간 반영**: 피드백을 즉시 반영하여 추천 개선

---

## Multi-Agent 시스템 아키텍처

### 전체 플로우

```
[사용자 요청]
    ↓
[질문 분류] - LLM으로 housing/finance/general 판별
    ↓
┌─────────────────────────────────────────────────┐
│ housing 질문                                     │
│    ↓                                            │
│ [Housing Agent] → 주택 매물 검색 (RDB)         │
│    ↓                                            │
│ [Commute Agent] → 출퇴근 시간 계산             │
│    ↓                                            │
│ [Price Comparison Agent] → 주변 시세 비교      │
│    ↓                                            │
│ [Recommendation Agent] → 점수화 및 최종 추천     │
│    ↓                                            │
│ [END]                                           │
├─────────────────────────────────────────────────┤
│ finance 질문                                     │
│    ↓                                            │
│ [Loan Agent] → 대출 정보 검색 (Vector DB)       │
│    ↓                                            │
│ [END]                                           │
├─────────────────────────────────────────────────┤
│ general 질문                                     │
│    ↓                                            │
│ [General LLM] → 직접 답변                       │
│    ↓                                            │
│ [END]                                           │
└─────────────────────────────────────────────────┘
```

**핵심 특징:**
- **스마트 라우팅**: 질문 분류에 따라 적절한 Agent로 자동 라우팅
- **전문화된 Agent**: 각 Agent가 자신의 도메인에 특화
- **확장성**: 새 Agent 추가 용이

---

## 에이전트 목록

### ✅ 현재 구현된 에이전트 (Single Agent 기반)

#### 1. RDB Search Agent
- **위치**: `backend/services/rag/A_langgraph/single_agent/tools.py`
- **기능**: 
  - 사회주택 및 공동체주택 공고 정보 검색
  - PostgreSQL RDB에서 주택 정보 조회
  - 자연어 질문 → SQL 쿼리 변환
- **데이터 소스**: 
  - `housing.notices` (주택 공고)
  - `housing.units` (호실 정보)
  - `housing.addresses` (주소 정보)
- **사용 도구**: `rdb_search` Tool
- **상태**: ✅ 구현 완료

#### 2. Vector Search Agent
- **위치**: `backend/services/rag/A_langgraph/single_agent/tools.py`
- **기능**:
  - 주택 관련 금융 정보 검색
  - Vector DB에서 유사도 기반 검색
  - 재검색 로직 (Query Rewriting)
- **데이터 소스**:
  - `vector_db.embeddings_e5_large` (정책 문서 임베딩)
  - `vector_db.document_chunks` (문서 청크)
- **사용 모델**: `MULTILINGUAL_E5_LARGE`
- **사용 도구**: `vector_search` Tool
- **상태**: ✅ 구현 완료

---

### 📋 앞으로 구현할 에이전트

#### 3. Commute Time Agent (출퇴근 시간 계산)
- **기능**:
  - 사용자로부터 주소/건물명/회사명 입력 받기
  - 주택 위치와 회사 위치 간 거리 계산
  - 출퇴근 소요 시간 계산 (대중교통, 자가용)
- **입력 데이터**:
  - 주택 주소 (from: `housing.addresses`)
  - 회사 주소/건물명/회사명 (from: 사용자 입력)
- **출력 데이터**:
  - 출퇴근 소요 시간 (분 단위)
  - 대중교통 경로 정보
  - 자가용 경로 정보 (선택)
- **구현 방법**:
  - Google Maps API 또는 Kakao Map API 활용
  - 대중교통 경로 계산 (지하철, 버스)
  - 거리 기반 점수 부여
- **상태**: ⏳ 구현 예정

#### 4. Price Comparison Agent (시세 비교)
- **기능**:
  - 해당 주택 주변 지역의 평균 시세 조회
  - 주택 가격과 주변 시세 비교
  - 시세 대비 할인/프리미엄 퍼센트 계산
- **입력 데이터**:
  - 주택 가격 (from: `housing.units`)
  - 주택 위치 (from: `housing.addresses`)
  - 주변 지역 실거래가 (from: `rtms.transactions_rent`)
- **출력 데이터**:
  - 주변 지역 평균 시세
  - 시세 대비 할인/프리미엄 퍼센트
  - 가격 적정성 점수 (0-100)
- **구현 방법**:
  - RTMS 데이터 활용하여 주변 실거래가 조회
  - 동일 건물 타입, 면적대별 평균 시세 계산
  - 할인율/프리미엄율 계산 및 점수화
- **상태**: ⏳ 구현 예정

#### 5. Recommendation Agent (최종 추천 및 평가)
- **기능**:
  - 모든 에이전트의 결과를 종합 분석
  - 각 주택에 대한 종합 점수 계산
  - 좋은 주택인지 평가하고 최종 추천 리스트 생성
- **입력 데이터**:
  - Housing Agent 결과 (주택 목록)
  - Commute Agent 결과 (출퇴근 시간)
  - Price Comparison Agent 결과 (시세 비교)
  - Loan Agent 결과 (대출 정보, 선택적)
- **출력 데이터**:
  - 종합 점수가 높은 주택 상위 N개
  - 각 주택별 평가 요약
  - 추천 이유 설명
- **점수화 기준**:
  - 출퇴근 시간 (30%): 시간이 짧을수록 높은 점수
  - 시세 적정성 (30%): 할인율이 높을수록 높은 점수
  - 대출 정보 일치도 (20%): 대출 가능한 경우 가산점
  - 주택 조건 (20%): 면적, 방 개수, 보증금 등
- **구현 방법**:
  - 가중 평균 방식으로 종합 점수 계산
  - LLM을 활용한 평가 요약 생성
  - 사용자 선호도 반영 (나중에 확장)
- **상태**: ⏳ 구현 예정

---

## 에이전트 상세 정보

### 에이전트 비교표

| 에이전트 | 데이터 소스 | 주요 기능 | 구현 상태 |
|---------|------------|----------|-----------|
| **RDB Search Agent** | PostgreSQL (housing schema) | 주택 공고 정보 검색 | ✅ 완료 |
| **Vector Search Agent** | Vector DB (embeddings_e5_large) | 금융 정책 정보 검색 | ✅ 완료 |
| **Commute Time Agent** | Google Maps API / Kakao Map API | 출퇴근 시간 계산 | ⏳ 예정 |
| **Price Comparison Agent** | RTMS (rtms.transactions_rent) | 주변 시세 비교 및 할인율 계산 | ⏳ 예정 |
| **Recommendation Agent** | 모든 에이전트 결과 | 종합 점수화 및 최종 추천 | ⏳ 예정 |

### 에이전트 실행 순서 (Housing 질문 기준)

```
1. RDB Search Agent
   → 초기 주택 목록 후보 수집
   
2. Commute Time Agent (병렬 실행 가능)
   → 각 주택별 출퇴근 시간 계산
   
3. Price Comparison Agent (병렬 실행 가능)
   → 각 주택별 주변 시세 비교
   
4. Recommendation Agent
   → 모든 정보 종합하여 점수화
   → 상위 N개 선별 및 추천
```

---

## 데이터 흐름

### 1. RDB Search Agent
```
사용자 질문: "강서구 주택 추천해줘"
    ↓
자연어 → SQL 변환 (LLM)
    ↓
PostgreSQL 쿼리 실행
    ↓
결과: 주택 목록 50건
```

### 2. Commute Time Agent
```
입력: 
  - 주택 주소: "서울 강서구 강서로47길 60"
  - 회사 정보: "삼성전자 서초사옥" (사용자 입력)
    ↓
위치 좌표 변환 (주소 → 좌표)
    ↓
경로 계산 API 호출
    ↓
결과: 
  - 대중교통: 45분
  - 자가용: 30분
  - 점수: 75점 (30분 기준)
```

### 3. Price Comparison Agent
```
입력:
  - 주택 가격: 전세 1억원
  - 주택 위치: "서울 강서구 내발산동"
    ↓
주변 실거래가 조회 (RTMS)
  - 동일 건물 타입: 아파트
  - 면적대: 30-40㎡
    ↓
평균 시세 계산: 1억 2천만원
    ↓
결과:
  - 평균 시세: 1억 2천만원
  - 할인율: 16.7% (시세 대비 저렴)
  - 점수: 85점 (할인율 기준)
```

### 4. Recommendation Agent
```
입력:
  - 주택 목록: 50건
  - 출퇴근 시간 점수: {주택1: 75점, 주택2: 60점, ...}
  - 시세 비교 점수: {주택1: 85점, 주택2: 70점, ...}
    ↓
종합 점수 계산 (가중 평균)
  - 주택1: (75×30%) + (85×30%) + (80×20%) + (70×20%) = 76.5점
  - 주택2: (60×30%) + (70×30%) + (75×20%) + (65×20%) = 67.5점
    ↓
점수 순 정렬
    ↓
결과: 상위 10개 추천 + 평가 요약
```

---

## 그래프 구조

### 예상 그래프 플로우

```
[START]
    ↓
[질문 분류 노드]
    ├─→ housing → [RDB Search Agent]
    ├─→ finance → [Vector Search Agent] → [END]
    └─→ general → [General LLM] → [END]
    
[RDB Search Agent]
    ↓
[Commute Time Agent] (병렬)
    ↓
[Price Comparison Agent] (병렬)
    ↓
[Recommendation Agent]
    ↓
[END]
```

---

## 구현 우선순위

### Phase 1: 기본 에이전트 구현
- [x] RDB Search Agent ✅
- [x] Vector Search Agent ✅
- [ ] Commute Time Agent
- [ ] Price Comparison Agent
- [ ] Recommendation Agent

### Phase 2: 통합 및 최적화
- [ ] LangGraph 통합
- [ ] 에이전트 간 데이터 전달 최적화
- [ ] 병렬 실행 최적화
- [ ] 에러 핸들링

### Phase 3: 확장 기능
- [ ] 사용자 선호도 반영
- [ ] 피드백 루프 구현
- [ ] 캐싱 추가
- [ ] 성능 모니터링

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [SQL Agent Toolkit](https://python.langchain.com/docs/integrations/toolkits/sql_database)

---

**작성일**: 2025-01-XX
**버전**: 5.0 (에이전트 목록 정리 버전)
**다음 단계**: Commute Time Agent 구현 시작
