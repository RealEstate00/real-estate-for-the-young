# RAG 시스템

5개 임베딩 모델을 사용한 Retrieval-Augmented Generation 시스템

## 구조

```
backend/services/rag/
├── cli/
│   ├── rag_cli.py           # 통합 CLI (평가, 임베딩 생성)
│   ├── main.py              # 기존 CLI (유지)
│   └── test_queries.txt     # 평가용 테스트 쿼리
├── config.py                # 5개 모델 설정
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
│   ├── vector_retriever.py  # 벡터 검색 리트리버
│   └── reranker.py          # 리랭킹
└── vectorstore/
    └── ingestion/
        └── store.py         # pgvector 스토리지
```

## 지원 모델 (5개)

1. **Multilingual E5 Small** (384차원) - 경량, 빠른 속도, 100개 언어 지원
2. **KakaoBank DeBERTa** (768차원) - 한국어 금융 도메인 특화
3. **Qwen3 Embedding 0.6B** (1024차원) - MTEB 1위급, 32k 토큰, MRL 지원
4. **EmbeddingGemma 300M** (768차원) - Google Gemma3 기반, Task-specific prompts

## 사용법

### 1. 데이터 로드 및 임베딩 생성

```bash
# 5개 모델로 임베딩 생성
python -m backend.services.loading.cli.load_cli vector_db \
  --data-dir backend/data/vector_db

# 또는 rag_cli 사용
python -m backend.services.rag.cli.rag_cli embed \
  --data-file backend/data/vector_db/structured/서울시_주거복지사업_pgvector_ready_cleaned.json
```

### 2. 모델 평가

```bash
# 사용 가능한 모델 목록
python -m backend.services.rag.cli.rag_cli list

# 단일 모델 평가
python -m backend.services.rag.cli.rag_cli model --model MULTILINGUAL_E5_SMALL

# 리랭킹 포함 평가
python -m backend.services.rag.cli.rag_cli model --model KAKAOBANK_DEBERTA --reranking

# 전체 모델 평가
python -m backend.services.rag.cli.rag_cli all

# 리랭킹 효과 비교
python -m backend.services.rag.cli.rag_cli reranking
```

## 📊 지원하는 모델

| 모델명                  | 식별자     | 차원 | 특징                    |
| ----------------------- | ---------- | ---- | ----------------------- |
| E5-Small (Multilingual) | `e5-small` | 384  | 빠른 추론, 다국어 지원  |
| KakaoBank DeBERTa       | `kakao`    | 768  | 한국어 금융 데이터 특화 |
| Qwen3 Embedding 0.6B    | `qwen`     | 1024 | 긴 문맥 처리, 고품질    |
| EmbeddingGemma 300M     | `gemma`    | 768  | Google Gemma 기반       |

## 🔧 고급 사용법

### 개별 스크립트 실행

```bash
# 1. 데이터 수집 및 임베딩 생성
python backend/services/rag/ingest_data.py

# 2. 성능 테스트
python backend/services/rag/performance_test.py

# 3. 개별 모델 테스트
python -c "
from backend.services.rag.retrieval.retriever import VectorRetriever
from backend.services.rag.embeddings.config import EmbeddingModelType

retriever = VectorRetriever(EmbeddingModelType.MULTILINGUAL_E5_SMALL)
results = retriever.search('신혼부부 임차보증금 이자지원', top_k=3)
for r in results:
    print(f'Similarity: {r[\"similarity\"]:.4f}')
    print(f'Content: {r[\"content\"][:100]}...')
    print()
"
```

### 커스텀 설정

```bash
# 청크 크기 조정
python backend/services/rag/run_tests.py --chunk-size 300 --batch-size 16

# 검색 결과 수 조정
python backend/services/rag/run_tests.py --top-k 10

# 데이터베이스 설정 변경
python backend/services/rag/run_tests.py \
    --db-host localhost \
    --db-port 5432 \
    --db-name rey \
    --db-user postgres \
    --db-password your_password
```

## 📈 성능 지표

테스트는 다음 지표들을 측정합니다:

### 1. 속도 지표

- **평균 검색 시간**: 쿼리당 평균 응답 시간 (ms)
- **처리량**: 초당 처리 가능한 쿼리 수

### 2. 품질 지표

- **평균 유사도**: 검색 결과의 평균 코사인 유사도
- **최고 유사도**: 가장 높은 유사도 점수
- **키워드 커버리지**: 예상 키워드가 검색 결과에 포함된 비율

### 3. 리랭킹 효과

- **유사도 개선**: 리랭킹 전후 유사도 변화
- **다양성 개선**: 중복 제거 효과

## 📋 테스트 쿼리

시스템은 다음 8개의 테스트 쿼리로 성능을 평가합니다:

1. **신혼부부 임차보증금 이자지원** (주거지원)
2. **대출 한도와 소득 기준** (자격요건)
3. **신청 절차와 필요 서류** (신청방법)
4. **이자지원 금리와 기간** (지원내용)
5. **대상주택 조건과 제외사항** (대상주택)
6. **반환보증 보증료 지원** (추가지원)
7. **대출 연장과 중단 사유** (관리)
8. **예비신혼부부 자격과 서류** (특수케이스)

## 📊 결과 해석

### 성능 비교 결과 예시

```
🏆 최고 성능 모델:
  가장 빠른 모델: intfloat/multilingual-e5-small
  가장 정확한 모델: Qwen/Qwen3-Embedding-0.6B
  키워드 커버리지 최고: kakaobank/kf-deberta-base

⚡ 속도 순위:
  1. intfloat/multilingual-e5-small: 45.23ms
  2. google/embeddinggemma-300m: 67.89ms
  3. Qwen/Qwen3-Embedding-0.6B: 89.12ms

🎯 품질 순위 (평균 유사도):
  1. Qwen/Qwen3-Embedding-0.6B: 0.8234
  2. kakaobank/kf-deberta-base: 0.8156
  3. google/embeddinggemma-300m: 0.8098
```

### 권장사항

- **빠른 응답이 필요한 경우**: E5-Small 또는 EmbeddingGemma
- **높은 정확도가 필요한 경우**: Qwen3 또는 KakaoBank DeBERTa
- **한국어 특화**: KakaoBank DeBERTa
- **균형잡힌 성능**: EmbeddingGemma 300M

## 🐛 문제 해결

### 일반적인 문제

1. **데이터베이스 연결 오류**

   ```bash
   # PostgreSQL 서비스 확인
   sudo systemctl status postgresql

   # 데이터베이스 연결 테스트
   psql -h localhost -p 5432 -U postgres -d rey
   ```

2. **메모리 부족 오류**

   ```bash
   # 배치 크기 줄이기
   python backend/services/rag/run_tests.py --batch-size 16

   # CPU 사용
   export CUDA_VISIBLE_DEVICES=""
   ```

3. **모델 다운로드 실패**

   ```bash
   # 캐시 디렉토리 확인
   ls ~/.cache/huggingface/

   # 수동으로 모델 다운로드
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
   ```

### 로그 확인

```bash
# 상세 로그로 실행
python backend/services/rag/run_tests.py --log-level DEBUG

# 특정 모듈 로그만 확인
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from backend.services.rag.retrieval.retriever import VectorRetriever
# ... 테스트 코드
"
```

## 📝 결과 파일

테스트 실행 후 다음 파일들이 생성됩니다:

- `performance_results.json`: 전체 성능 테스트 결과
- `reranking_results.json`: 리랭킹 테스트 결과 (해당하는 경우)

이 파일들을 통해 상세한 성능 분석이 가능합니다.

## 🤝 기여하기

새로운 모델을 추가하거나 성능 지표를 개선하려면:

1. `embeddings/config.py`에 새 모델 추가
2. `performance_test.py`에 테스트 쿼리 추가
3. `run_tests.py`에 모델 매핑 추가

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
