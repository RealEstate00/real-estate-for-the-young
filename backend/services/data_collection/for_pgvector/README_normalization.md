# FAQ 데이터 정규화 (Normalization) 가이드

## 개요
이 문서는 FAQ 데이터를 임베딩하기 좋은 형태로 정규화(Normalization)하는 방법과 규칙을 설명합니다.

## 정규화 규칙

### 1. 구조 분리
- **"구분 답변"** 헤더 제거
- 페이지 마커(`-1-`, `-2-`) 제거 (메타데이터로 보관)
- 카테고리 헤더는 별도 필드로 분리

### 2. 질문-답변 쌍 생성
- **물음표(`?`)** 를 기준으로 질문과 답변 분리
- 각 FAQ를 독립적인 QA 단위로 처리
- 질문은 여러 줄에 걸쳐 있을 수 있음

### 3. 공백 정규화
- 여러 개의 공백 → 하나의 공백
- 여러 개의 줄바꿈 → 최대 2개
- 문장 끝이 아닌 곳의 줄바꿈 → 공백으로 연결

### 4. 번호 형식 통일
```
① ② ③ → 1. 2. 3.
1) 2) 3) → 1. 2. 3.
```

### 5. 특수문자 정리
```
※ → (참고)
```

### 6. URL 정규화
- 공백 제거
- 형식 통일

### 7. 메타데이터 추가
각 QA에 다음 정보 포함:
- `category`: 카테고리 (예: "신혼부부 임차보증금 지원")
- `page_number`: 원본 페이지 번호
- `source`: 문서 출처
- `document_type`: 문서 유형 (FAQ, 공고 등)
- `language`: 언어 (ko, en)

## 사용 방법

### Step 1: TXT 정규화
기본 정규화를 수행합니다.

```bash
cd backend/services/data_collection/for_pgvector
python normalize_faq.py
```

**입력**: `backend/data/raw/finance_support/pre_normalize/신혼부부 사업FAQ.txt`
**출력**: `backend/data/raw/finance_support/pre_normalize/신혼부부 사업FAQ_normalized.txt`

### Step 2: JSON 변환
정규화된 TXT를 JSON으로 변환합니다.

```bash
python convert_normalized_to_json.py
```

**입력**: `신혼부부 사업FAQ_normalized.txt`
**출력**: `신혼부부 사업FAQ_normalized.json`

## 출력 형식

### JSON 구조
```json
[
  {
    "question": "대출신청 절차는 어떻게 되나요 ?",
    "answer": "1. 은행에 방문하여 대출자격, 대출한도 확인...",
    "category": "신혼부부 임차보증금 지원",
    "page_number": 1,
    "metadata": {
      "source": "서울시 신혼부부 임차보증금 지원 FAQ",
      "document_type": "FAQ",
      "language": "ko"
    }
  }
]
```

## 임베딩 텍스트 생성

벡터 DB에 저장할 때는 다음 형식을 권장합니다:

```python
def to_embedding_text(qa):
    """임베딩용 텍스트 생성"""
    return f"[{qa['category']}] {qa['question']}\n\n{qa['answer']}"
```

**예시**:
```
[신혼부부 임차보증금 지원] 대출신청 절차는 어떻게 되나요 ?

1. 은행에 방문하여 대출자격, 대출한도 확인 및 계약체결 예정인 대상주택의 대출 가능여부 등 사전 상담
2. 대출한도 감안하여 임대차계약 체결
3. 서울주거포털 (housing.seoul.go.kr) 에서 추천서 발급 신청 및 출력(서울시 발급 승인 후)
4. 대출신청 (은행 지점 방문)
```

## 임베딩 최적화 팁

### 1. 청킹 전략
- **권장**: QA 단위로 분리된 상태에서 임베딩
- 너무 긴 답변(1000자 이상)은 문장 단위로 추가 분할 고려

### 2. 메타데이터 활용
- 검색 시 `category`로 필터링 가능
- `page_number`로 원본 문서 참조 가능
- `source`로 출처 추적

### 3. 다양한 질문 형태 처리
```python
# 원본 질문
"대출신청 절차는 어떻게 되나요?"

# 유사 질문 생성 (임베딩 품질 향상)
variations = [
    "대출신청 절차를 알려주세요",
    "대출 신청은 어떻게 하나요",
    "대출 절차가 어떻게 되나요"
]
```

### 4. 벡터 DB 스키마 예시
```sql
CREATE TABLE faq_embeddings (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    category TEXT,
    page_number INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 벡터 유사도 검색 인덱스
CREATE INDEX ON faq_embeddings USING ivfflat (embedding vector_cosine_ops);
```

## 파일 구조
```
backend/services/data_collection/for_pgvector/
├── normalize_faq.py              # 기본 정규화 (TXT → TXT)
├── convert_normalized_to_json.py  # JSON 변환 (TXT → JSON)
├── normalize_faq_improved.py      # 개선 버전 (참고용)
├── normalize_faq_v2.py           # 대안 버전 (참고용)
└── README_normalization.md        # 이 문서

backend/data/raw/finance_support/pre_normalize/
├── 신혼부부 사업FAQ.txt              # 원본
├── 신혼부부 사업FAQ_normalized.txt   # 정규화된 TXT
└── 신혼부부 사업FAQ_normalized.json  # 최종 JSON
```

## 주의사항

1. **인코딩**: 모든 파일은 UTF-8로 저장
2. **줄바꿈**: Windows CRLF와 Unix LF 모두 지원
3. **물음표**: 답변 안에도 물음표가 있을 수 있으므로 파싱 시 주의
4. **긴 텍스트**: 매우 긴 답변은 임베딩 전 적절히 분할

## 추가 개선 아이디어

### 1. 동의어 처리
```python
synonyms = {
    "융자": ["대출", "금융지원"],
    "추천서": ["신청서", "발급서"],
    "신혼부부": ["신혼", "부부"]
}
```

### 2. 키워드 추출
```python
from sklearn.feature_extraction.text import TfidfVectorizer

# 중요 키워드 추출하여 메타데이터에 추가
keywords = extract_keywords(qa['question'] + ' ' + qa['answer'])
qa['metadata']['keywords'] = keywords
```

### 3. 의미적 청킹
- 단순 문자 수 기반이 아닌 의미 단위로 분할
- 관련 정보를 함께 유지

## 참고 자료

- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [OpenAI Embeddings Best Practices](https://platform.openai.com/docs/guides/embeddings/what-are-embeddings)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
