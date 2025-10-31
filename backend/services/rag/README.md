# RAG 시스템

4개 임베딩 모델을 사용한 Retrieval-Augmented Generation 시스템

## 구조

```
backend/services/rag/
├── cli/
│   ├── rag_cli.py           # 통합 CLI (평가, 임베딩 생성)
│   ├── main.py              # 기존 CLI (유지)
│   └── test_queries.txt     # 평가용 테스트 쿼리
├── models/
│   ├── config.py           # 4개 모델 설정
├── core/
│   ├── embedder.py          # 다중 모델 임베딩 생성
│   ├── evaluator.py         # RAG 성능 평가
│   ├── metrics.py           # 성능 지표 계산 (Precision@K, MRR, NDCG 등)
│   └── search.py            # 벡터 검색 및 리트리버
├── models/
│   ├── encoder.py           # 임베딩 인코더
│   ├── loader.py            # 모델 로더
│   └── comparator.py        # 모델 비교기
├── retrieval/
│   ├── retriever.py         # 벡터 검색 리트리버
│   └── reranker.py          # 리랭킹 (LLM 기반 키워드 추출)
├── augmentation/
│   ├── augmenter.py         # 문서 증강
│   └── formatters.py       # 컨텍스트 포맷터
├── generation/
│   └── generator.py         # LLM 답변 생성 (Ollama)
├── rag_system.py            # 통합 RAG 시스템
└── vectorstore/
    └── ingestion/
        └── store.py         # pgvector 스토리지
```

## 지원 모델 (4개)

1. **Multilingual E5 Small** (384차원) - 경량, 빠른 속도, 100개 언어 지원
2. **Multilingual E5 Base** (768차원) - 균형잡힌 성능, 100개 언어 지원
3. **Multilingual E5 Large** (1024차원) - 높은 정확도, 대규모 데이터셋 처리
4. **KakaoBank DeBERTa** (768차원) - 한국어 금융 도메인 특화

## 사용법

### 1. 데이터 로드 및 임베딩 생성

```bash
# 4개 모델로 임베딩 생성
python -m backend.services.loading.cli.load_cli vector_db \
  --data-dir backend/data/vector_db

# 특정 모델만 선택하여 임베딩 생성
python -m backend.services.loading.cli.load_cli vector_db \
  --data-dir backend/data/vector_db \
  --models e5 e5_base e5_large kakaobank
```

### 2. RAG 시스템 평가

#### 2.1 임베딩 모델 비교 평가

```bash
# 여러 임베딩 모델의 검색 품질 비교
rag eval embedding "청년 전세대출 조건과 금리"
```

이 명령은 다음을 수행합니다:

- E5_SMALL, E5_BASE, E5_LARGE, KAKAO 모델로 동일한 쿼리 검색
- 각 모델의 유사도, 검색 시간, 키워드 커버리지 비교
- 마크다운 보고서 생성 (`backend/services/rag/results/embedding_model_comparison_*.md`)

#### 2.2 답변 비교 평가 (전체 RAG 파이프라인)

```bash
# 단일 질문으로 평가
rag eval answering "청년 전세대출 금리"

# test_queries.txt의 모든 질문으로 평가 (질문 미지정 시)
rag eval answering
```

이 명령은 다음을 수행합니다:

- 전체 RAG 파이프라인 실행 (검색 + 리랭킹 + 증강 + 생성)
- 여러 임베딩 모델별 최종 답변 비교
- 생성 시간, 토큰 사용량, 답변 품질 비교
- 마크다운 보고서 생성 (`backend/services/rag/results/answer_comparison_*.md`)

### 3. RAG 파이프라인 실행 (답변 생성)

```bash
# 기본 사용 (E5_SMALL, gemma2:2b)
rag generate "청년 전세대출 조건"

# 모델 선택 및 옵션
rag generate "청년 전세대출 금리" \
  --model E5_LARGE \
  --llm-model gemma3:4b \
  --top-k 5 \
  --reranking \
  --format enhanced \
  --temperature 0.7 \
  --max-tokens 2000
```

## 📊 지원하는 모델

| 모델명                  | 식별자     | 차원 | HuggingFace 모델명               | 특징                       |
| ----------------------- | ---------- | ---- | -------------------------------- | -------------------------- |
| E5-Small (Multilingual) | `E5_SMALL` | 384  | `intfloat/multilingual-e5-small` | 빠른 추론, 다국어 지원     |
| E5-Base (Multilingual)  | `E5_BASE`  | 768  | `intfloat/multilingual-e5-base`  | 균형잡힌 성능, 다국어 지원 |
| E5-Large (Multilingual) | `E5_LARGE` | 1024 | `intfloat/multilingual-e5-large` | 높은 정확도, 대규모 처리   |
| KakaoBank DeBERTa       | `KAKAO`    | 768  | `kakaobank/kf-deberta-base`      | 한국어 금융 데이터 특화    |

## 🔧 CLI 명령어 요약

### 평가 명령어

```bash
# 임베딩 모델 검색 품질 비교
rag eval embedding <query>

# 전체 RAG 파이프라인 답변 비교
rag eval answering [query]
```

### 생성 명령어

```bash
# RAG 파이프라인으로 답변 생성
rag generate <query> [옵션]
```

## 🏗️ RAG 파이프라인 구조

현재 시스템은 다음 단계로 구성됩니다:

```
[사용자 질문]
  ↓
[1. Query Embedding] 쿼리 텍스트 → 벡터 변환
  ↓
[2. Retrieval] 벡터 검색 (pgvector)
  ↓
[3. Reranking] LLM 기반 키워드 추출 + 리랭킹
  ↓
[4. Augmentation] 문서 포맷팅 (EnhancedPromptFormatter)
  ↓
[5. Generation] LLM 답변 생성 (Ollama + gemma3:4b)
  ↓
[최종 답변]
```

### 주요 컴포넌트

- **Retriever**: 벡터 검색 수행 (`retrieval/retriever.py`)
- **Reranker**: 검색 결과 리랭킹 (`retrieval/reranker.py`)
  - LLM 기반 키워드 추출 (기본 활성화, gemma3:4b 사용)
- **Augmenter**: 검색 결과를 LLM용 컨텍스트로 변환 (`augmentation/augmenter.py`)
- **Generator**: LLM으로 최종 답변 생성 (`generation/generator.py`)

## 📈 성능 평가

### 평가 방법

#### 1. 임베딩 모델 비교 (`rag eval embedding`)

- 여러 임베딩 모델의 검색 품질 비교
- 유사도, 검색 시간, 키워드 커버리지 측정
- 마크다운 보고서 생성

#### 2. 답변 비교 (`rag eval answering`)

- 전체 RAG 파이프라인을 통한 최종 답변 비교
- 생성 시간, 토큰 사용량, 답변 품질 비교
- 마크다운 보고서 생성

### 평가 지표

- **검색 품질**: 평균 유사도, 최고 유사도
- **검색 속도**: 평균 검색 시간 (ms)
- **생성 품질**: 답변 길이, 토큰 사용량, 생성 시간
- **리랭킹 효과**: 리랭킹 전후 유사도 변화

## 📊 결과 해석

### 성능 비교 결과 예시

```
🏆 최고 성능 모델:
  가장 빠른 모델: intfloat/multilingual-e5-small
  가장 정확한 모델: intfloat/multilingual-e5-large
  키워드 커버리지 최고: kakaobank/kf-deberta-base

⚡ 속도 순위:
  1. intfloat/multilingual-e5-small: 45.23ms
  2. kakaobank/kf-deberta-base: 67.89ms
  3. intfloat/multilingual-e5-base: 72.15ms
  4. intfloat/multilingual-e5-large: 89.12ms

🎯 품질 순위 (평균 유사도):
  1. intfloat/multilingual-e5-large: 0.8234
  2. kakaobank/kf-deberta-base: 0.8156
  3. intfloat/multilingual-e5-base: 0.8098
  4. intfloat/multilingual-e5-small: 0.7956
```

### 권장사항

- **빠른 응답이 필요한 경우**: E5-Small (384차원, 가장 빠름)
- **균형잡힌 성능**: E5-Base (768차원, 속도와 정확도 균형)
- **높은 정확도가 필요한 경우**: E5-Large (1024차원, 가장 정확)
- **한국어 특화**: KakaoBank DeBERTa (한국어 금융 도메인 특화)

## 🐛 문제 해결

### 일반적인 문제

#### 1. Ollama 서버 연결 오류

```bash
# Ollama 서버 상태 확인
ollama list

# Ollama 서버 시작 (백그라운드)
ollama serve

# 또는 별도 터미널에서 실행
# 기본 포트: http://localhost:11434
```

#### 2. 데이터베이스 연결 오류

```bash
# PostgreSQL 서비스 확인
sudo systemctl status postgresql

# 데이터베이스 연결 테스트
psql -h localhost -p 5432 -U postgres -d rey

# 환경 변수 설정
export PG_HOST=localhost
export PG_PORT=5432
export PG_DB=rey
export PG_USER=postgres
export PG_PASSWORD=post1234
```

#### 3. 모델 다운로드 실패

```bash
# HuggingFace 캐시 확인
ls ~/.cache/huggingface/

# 캐시 삭제 후 재시도
rm -rf ~/.cache/huggingface/hub/*

# 수동 모델 다운로드
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('intfloat/multilingual-e5-small')
"
```

#### 4. 메모리 부족 오류

```bash
# CPU 모드로 실행 (환경 변수)
export CUDA_VISIBLE_DEVICES=""

# 또는 배치 크기 줄이기 (코드에서)
# batch_size=16 → batch_size=8
```

## 📝 결과 파일

평가 실행 후 다음 위치에 마크다운 보고서가 생성됩니다:

- **임베딩 모델 비교**: `backend/services/rag/results/embedding_model_comparison_*.md`
- **답변 비교**: `backend/services/rag/results/answer_comparison_*.md`
