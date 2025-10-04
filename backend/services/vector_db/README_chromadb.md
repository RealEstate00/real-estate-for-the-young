# ChromaDB 벡터 데이터베이스 가이드

## 📋 개요

이 프로젝트는 ChromaDB와 한국어 특화 임베딩 모델(`jhgan/ko-sbert-nli`)을 사용하여 주택 데이터의 의미적 검색을 제공합니다. 사용자는 자연어로 주택을 검색하고, 유사한 특성을 가진 주택들을 찾을 수 있습니다.

## 🏗️ 아키텍처

```
Vector Database Service
├── ChromaDB (벡터 저장소)
├── ko-sbert-nli (한국어 임베딩 모델)
├── Housing Collection (주택 데이터 컬렉션)
└── CLI Interface (명령어 인터페이스)
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 필요한 패키지 설치
pip install -r backend/requirements.txt

# 프로젝트 설치 (CLI 명령어 등록)
pip install -e .

# chromadb관련 프로그램 안깔리는 경우, 전역에 설치
pip install chromadb
pip install pydantic-settings

```

### 2. 데이터 로딩

```bash
# CSV 데이터를 벡터 데이터베이스에 로딩
vector-db load-data

# 기존 데이터 삭제 후 새로 로딩
vector-db load-data --clear

# 진행 상황 확인
vector-db info
```

### 3. 검색 테스트

```bash
# 하이브리드 검색 (추천!) - 키워드 + 벡터 검색
vector-db search "반려동물을 키울 수 있는 주택을 추천해줘" --hybrid

# 지역 기반 하이브리드 검색
vector-db search "홍대 근처 청년주택" --hybrid

# 기본 벡터 검색
vector-db search "홍대 근처 청년주택"

# 결과 예시:
# ┌──────┬─────────────────────┬──────────────────────┬────────────┬──────────────────┐
# │ Rank │ Housing Name        │ Location             │ Similarity │ Theme            │
# ├──────┼─────────────────────┼──────────────────────┼────────────┼──────────────────┤
# │ 1    │ 함께주택3호 - 하얀집 │ 마포구 동교동        │ 0.377      │                  │
# │ 2    │ 어쩌다 집 연남       │ 마포구 연남동        │ 0.363      │                  │
# └──────┴─────────────────────┴──────────────────────┴────────────┴──────────────────┘
```

## 📚 CLI 명령어 가이드

### 데이터 관리

#### `load-data` - 데이터 로딩
```bash
# 기본 로딩
vector-db load-data

# 옵션 사용
vector-db load-data --csv-path ./custom_data.csv --batch-size 16 --clear
```

**옵션:**
- `--csv-path, -c`: CSV 파일 경로 (기본값: `backend/data/raw/for_vectorDB/housing_vector_data.csv`)
- `--batch-size, -b`: 배치 크기 (기본값: 32)
- `--clear`: 기존 데이터 삭제 후 로딩

#### `clear` - 데이터베이스 초기화
```bash
vector-db clear
# ⚠️ 주의: 모든 데이터가 삭제됩니다!
```

### 검색 기능

#### `search` - 스마트 검색 시스템
```bash
# 기본 벡터 검색
vector-db search "원하는 주택 조건"

# 하이브리드 검색 (추천!) - 키워드 + 벡터 결합
vector-db search "반려동물을 키울 수 있는 주택을 추천해줘" --hybrid

# 지역 필터링
vector-db search "지하철역 가까운 곳" --district "강남구" --dong "대치동"

# 테마 필터링
vector-db search "반려동물 키울 수 있는 곳" --theme "반려동물"

# 최소 유사도 필터링
vector-db search "홍대 근처 청년주택" --min-sim 0.3

# 결과 개수 조정
vector-db search "신혼부부 주택" --limit 20
```

**옵션:**
- `--limit, -n`: 결과 개수 (기본값: 10)
- `--district, -d`: 시군구 필터
- `--dong`: 동 필터
- `--theme, -t`: 테마 필터
- `--hybrid`: 하이브리드 검색 사용 (키워드 + 벡터)
- `--min-sim`: 최소 유사도 임계값 (0.0-1.0)

#### 검색 예시

```bash
# 1. 위치 기반 검색
vector-db search "홍대입구역 도보 10분" --district "마포구"

# 2. 테마 기반 검색
vector-db search "청년 1인 가구" --theme "청년형"

# 3. 시설 기반 검색
vector-db search "병원 가까운 곳"

# 4. 복합 조건 검색
vector-db search "지하철 2호선 신혼부부" --limit 15
```

### 정보 및 통계

#### `stats` - 데이터베이스 통계
```bash
vector-db stats
```

**출력 예시:**
```
Vector Database Statistics

Total Housing Records: 131

Top Districts:
┌─────────────┬───────┐
│ District    │ Count │
├─────────────┼───────┤
│ 서대문구    │ 12    │
│ 금천구      │ 11    │
│ 관악구      │ 10    │
└─────────────┴───────┘

Top Themes:
┌─────────────┬───────┐
│ Theme       │ Count │
├─────────────┼───────┤
│ 인증통과    │ 89    │
│ 청년형      │ 23    │
│ 제한없음    │ 18    │
└─────────────┴───────┘
```

#### `info` - 데이터베이스 정보
```bash
vector-db info
```

#### `preview` - 임베딩 미리보기
```bash
vector-db preview --samples 3
```

## 🧠 하이브리드 검색 시스템

### 검색 방식 비교

#### 1. **벡터 검색** (기본값)
```bash
vector-db search "반려동물을 키울 수 있는 주택"
```
- **장점**: 의미적 유사성 검색, 유연한 검색
- **단점**: 때로는 부정확한 결과 (키워드 없는 주택도 검색됨)
- **유사도**: 낮은 점수 (0.1-0.3) 가능

#### 2. **하이브리드 검색** (추천!)
```bash
vector-db search "반려동물을 키울 수 있는 주택" --hybrid
```
- **장점**: 정확성 + 유연성 결합
- **동작**: 키워드 필터링 → 벡터 검색
- **유사도**: 높은 점수 (0.3-0.8) 보장

### 하이브리드 검색 동작 과정

#### **사용자 쿼리**: "홍대 근처에서 반려동물 키울 수 있는 청년주택 찾아줘"

**1단계: 스마트 키워드 추출**
```python
keywords = {
    "지역": ["홍대"],
    "테마": ["반려동물", "청년"],
    "주택": ["주택"]
}
```

**2단계: 우선순위 필터링**
```python
# 1순위: 테마 기반 필터링
theme_filter = ["반려동물", "청년"]
filtered_houses = get_houses_with_themes(theme_filter)

# 2순위: 지역 기반 필터링 (테마 결과가 없을 때)
location_filter = ["마포구", "서대문구"]  # 홍대 주변
```

**3단계: 벡터 유사도 계산**
```python
# 필터링된 주택들 중에서 쿼리와 가장 유사한 순으로 정렬
results = rank_by_similarity(filtered_houses, original_query)
```

### 지원하는 키워드 카테고리

#### **테마 키워드** (최우선)
- `청년`, `신혼`, `육아`, `시니어`, `예술`, `반려동물`, `여성안심`

#### **지역 키워드**
- `구`: 강남구, 마포구, 서대문구 등
- `동`: 홍은동, 연남동, 독산동 등

#### **지하철 키워드**
- `역`: 홍대입구역, 신림역, 강남역 등
- `지하철`, `전철`

#### **주택 유형 키워드**
- `주택`, `아파트`, `빌라`, `원룸`, `투룸`, `쉐어하우스`, `공동체주택`

### 유사도 점수 해석

#### **색상 코딩**
- 🟢 **0.5 이상**: 높은 유사도 (매우 관련성 높음)
- 🟡 **0.3-0.5**: 중간 유사도 (관련성 있음)
- 🔴 **0.3 미만**: 낮은 유사도 (관련성 낮음)
- ⚫ **음수**: 반대 의미 또는 전혀 관련 없음

#### **실제 의미**
- **0.8 이상**: 거의 완벽한 매칭 ✅
- **0.5-0.8**: 높은 관련성 ✅
- **0.2-0.5**: 중간 관련성 ⚠️
- **0.0-0.2**: 낮은 관련성 ❌
- **음수**: 관련 없음 ❌

## 🔧 기술 세부사항

### 임베딩 모델
- **모델**: `jhgan/ko-sbert-nli`
- **차원**: 768차원
- **특징**: 한국어 자연어 추론(NLI) 데이터셋으로 학습
- **성능**: KorSTS에서 82-83% 상관계수

### 데이터 구조
**데이터 소스**: `backend/data/raw/for_vectorDB/housing_vector_data.csv`  
**총 레코드 수**: 130개 주택 정보  
**벡터DB 저장 위치**: `backend/data/chroma_db/`

각 주택 레코드는 다음과 같이 구조화됩니다:

```python
# 예시 텍스트 구성
"""
주택명: 오늘공동체주택
주소: 서울특별시 도봉구 도봉로191길 80 (도봉동)
지역: 도봉구
동: 도봉동
특성: 테마:인증통과 육아형 취미형, 지하철:도봉산역, 자격요건:제한없음, 마트:세븐일레븐 도봉산길점, 병원:부부약국, 학교:도봉초등학교, 시설:김근태기념도서관, 카페:유영정원
"""
```

### 메타데이터 구조
```json
{
  "주택명": "오늘공동체주택",
  "지번주소": "서울특별시 도봉구 도봉동 351-2",
  "도로명주소": "서울특별시 도봉구 도봉로191길 80 (도봉동)",
  "시군구": "도봉구",
  "동명": "도봉동",
  "태그": "테마:인증통과 육아형 취미형, 지하철:도봉산역...",
  "theme": "인증통과 육아형 취미형",
  "subway": "도봉산역",
  "requirements": "제한없음",
  "mart": "세븐일레븐 도봉산길점",
  "hospital": "부부약국",
  "school": "도봉초등학교",
  "facilities": "김근태기념도서관",
  "cafe": "유영정원"
}
```

## 🎯 사용 사례

### 1. 자연어 쿼리 (하이브리드 검색 추천)
```bash
# 반려동물 관련
vector-db search "반려동물을 키울 수 있는 주택을 추천해줘" --hybrid

# 지역 + 테마 복합
vector-db search "홍대 근처에서 청년이 살기 좋은 곳 알려줘" --hybrid

# 교통 + 라이프스타일
vector-db search "지하철 2호선 근처 신혼부부 주택" --hybrid

# 편의시설 중심
vector-db search "병원이랑 마트 가까운 육아하기 좋은 주택" --hybrid
```

### 2. 정확한 키워드 검색
```bash
# 테마별 검색
vector-db search "주택" --theme "반려동물"
vector-db search "주택" --theme "청년형"
vector-db search "주택" --theme "신혼형"

# 지역별 검색
vector-db search "주택" --district "강남구"
vector-db search "주택" --district "마포구" --dong "홍은동"
```

### 3. 유사도 필터링
```bash
# 높은 정확도 요구
vector-db search "홍대입구역 도보 5분" --min-sim 0.5

# 중간 정확도
vector-db search "강남 테헤란로 근처" --min-sim 0.3

# 관련성만 확인
vector-db search "지하철역 가까운 곳" --min-sim 0.1
```

### 4. 복합 조건 검색
```bash
# 하이브리드 + 지역 필터
vector-db search "반려동물 키울 수 있는 곳" --hybrid --district "마포구"

# 하이브리드 + 유사도 필터
vector-db search "청년 1인 가구 주택" --hybrid --min-sim 0.4

# 모든 옵션 조합
vector-db search "홍대 근처 예술가를 위한 주택" --hybrid --district "마포구" --min-sim 0.3 --limit 15
```

### 5. 검색 결과 비교
```bash
# 일반 벡터 검색
vector-db search "반려동물 주택"
# → 결과: 관련 없는 주택도 포함, 낮은 유사도

# 하이브리드 검색
vector-db search "반려동물 주택" --hybrid  
# → 결과: 반려동물 태그가 있는 주택만, 높은 유사도

# 정확한 필터 검색
vector-db search "주택" --theme "반려동물"
# → 결과: 100% 정확한 반려동물 주택만
```

## 📊 성능 최적화

### 배치 크기 조정
```bash
# 메모리가 부족한 경우
vector-db load-data --batch-size 8

# 메모리가 충분한 경우
vector-db load-data --batch-size 64
```

### 검색 결과 수 조정
```bash
# 빠른 검색 (적은 결과)
vector-db search "쿼리" --limit 5

# 정확한 검색 (많은 결과)
vector-db search "쿼리" --limit 50
```
<!-- 
## 🔍 고급 사용법

### Python API 사용
```python
from backend.services.vector_db import VectorDBClient, KoreanEmbedder, HousingCollection

# 클라이언트 초기화
client = VectorDBClient()
embedder = KoreanEmbedder()
collection = HousingCollection(client, embedder)

# 연결 및 모델 로딩
client.connect()
embedder.load_model()

# 검색 수행
results = collection.search_similar("홍대 근처 청년주택", n_results=10)

# 결과 처리
for result in results:
    print(f"주택명: {result['metadata']['주택명']}")
    print(f"유사도: {result['similarity']:.3f}")
    print(f"위치: {result['metadata']['시군구']} {result['metadata']['동명']}")
    print("---")
``` -->

### 데이터 업데이트
```python
from backend.services.vector_db.data_loader import HousingDataLoader

# 새 데이터 추가
loader = HousingDataLoader()
new_record = {
    "주택명": "새로운 주택",
    "도로명주소": "서울특별시 강남구 테헤란로 123",
    "시군구": "강남구",
    "동명": "역삼동",
    "태그": "테마:청년형, 지하철:역삼역"
}

loader.update_single_record(new_record)
```

## 🛠️ 문제 해결

### 일반적인 문제

#### 1. CLI 명령어 인식 안됨
```bash
# 에러: 'vector-db' 용어가 cmdlet으로 인식되지 않습니다
```
**해결책**: 프로젝트 설치
```bash
pip install -e .
```

#### 2. 모델 로딩 실패
```bash
# 에러: Failed to load Korean embedding model
```
**해결책**: 인터넷 연결 확인 후 다시 시도
```bash
pip install --upgrade sentence-transformers
```

#### 3. 메모리 부족
```bash
# 에러: CUDA out of memory 또는 RAM 부족
```
**해결책**: 배치 크기 줄이기
```bash
vector-db load-data --batch-size 8
```

#### 4. CSV 파일 경로 오류
```bash
# 에러: FileNotFoundError
```
**해결책**: 올바른 경로 확인
```bash
# 기본 경로: backend/data/raw/for_vectorDB/housing_vector_data.csv
vector-db load-data --csv-path "your/custom/path.csv"
```

#### 5. 검색 결과 없음 또는 낮은 유사도
```bash
# 결과: No results found 또는 유사도 < 0.2
```
**해결책**: 
- 하이브리드 검색 사용: `--hybrid`
- 최소 유사도 낮추기: `--min-sim 0.1`
- 데이터 로딩 확인: `vector-db info`

#### 6. 컬렉션 삭제 오류
```bash
# 에러: Collection does not exist
```
**해결책**: 안전한 clear 동작 (자동 처리됨)
```bash
vector-db load-data --clear  # 이제 안전하게 동작
```

### 로그 확인
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 📈 성능 벤치마크

### 하드웨어 요구사항
- **최소**: 4GB RAM, CPU
- **권장**: 8GB+ RAM, CPU
- **최적**: 16GB+ RAM, GPU (선택사항)

### 처리 속도
- **임베딩 생성**: ~7 문서/초 (CPU, ko-sbert-nli)
- **검색 속도**: ~10ms/쿼리
- **로딩 시간**: ~18초 (130개 문서)
- **모델 로딩**: 초기 10-20초 (500MB 모델)

## 🔮 향후 계획

### 예정된 기능
- [ ] 실시간 데이터 업데이트
- [ ] 웹 인터페이스
- [ ] 다중 언어 지원
- [ ] 고급 필터링 옵션
- [ ] 검색 결과 랭킹 개선

### 모델 업그레이드 옵션
- `klue/roberta-large`: 더 큰 한국어 모델
- `openai/text-embedding-3-small`: OpenAI 임베딩 (유료)
- 커스텀 파인튜닝 모델

---

## 📊 현재 상태 (2025년 10월 4일)

### ✅ 구현 완료
- **데이터 로딩**: 130개 주택 레코드 성공적으로 임베딩
- **하이브리드 검색**: 키워드 + 벡터 검색 시스템
- **CLI 인터페이스**: 완전한 명령어 세트
- **경로 수정**: 올바른 CSV 파일 경로 설정
- **안전한 삭제**: 컬렉션 존재 여부 확인 후 삭제

### 🎯 검증된 기능
- **반려동물 검색**: 하이브리드 검색으로 정확한 결과
- **지역 기반 검색**: 홍대, 강남 등 지역별 필터링
- **테마 검색**: 청년형, 신혼형, 육아형 등
- **유사도 필터링**: 0.3 이상 고품질 결과만 표시

### 📁 파일 구조
```
backend/data/
├── raw/for_vectorDB/housing_vector_data.csv  # 원본 데이터 (130개)
├── chroma_db/                                # 벡터DB 저장소
└── PDF/vector_db/                           # PDF 문서화
```

---

**마지막 업데이트**: 2025년 10월 4일  
**버전**: 1.0.0  
**데이터 버전**: 130개 레코드  
**라이선스**: MIT
