# Real Estate for the Young - 명령어 가이드

이 문서는 프로젝트의 모든 CLI 명령어와 사용법을 정리한 가이드입니다.

## 📋 목차

- [데이터 수집 명령어](#데이터-수집-명령어)
- [데이터베이스 관리 명령어](#데이터베이스-관리-명령어)
- [데이터 로딩 명령어](#데이터-로딩-명령어)
- [환경 설정](#환경-설정)

---

## 🏠 데이터 수집 명령어

### `data-collection-housing`

주택 관련 데이터 수집 명령어

```bash
# 도움말 보기
data-collection-housing --help

# 크롤링 명령어
data-collection-housing crawl --help
data-collection-housing crawl cohouse --fresh
data-collection-housing crawl sohouse --fresh

# 데이터 정규화 명령어
data-collection-housing normalized --help
data-collection-housing normalized process --platform cohouse
```

**주요 기능:**

- 주택 플랫폼 크롤링 (cohouse, sohouse 등)
- 원시 데이터 정규화
- 정규화된 데이터를 `backend/data/normalized/housing/`에 저장

### `data-collection-infra`

인프라 및 API 데이터 수집 명령어

```bash
# 도움말 보기
data-collection-infra --help

# API 데이터 수집
data-collection-infra api --help
data-collection-infra api load

# 서울시 공공데이터 API
data-collection-infra seoul --help
data-collection-infra seoul normalize
data-collection-infra seoul load
```

**주요 기능:**

- 공공 API 데이터 수집
- 서울시 공공데이터 API 활용
- 인프라 데이터 정규화

---

## 🗄️ 데이터베이스 관리 명령어

### `data-db`

데이터베이스 스키마 및 테이블 관리

```bash
# 도움말 보기
data-db --help

# 데이터베이스 생성
data-db create

# 테이블 삭제 (주의!)
data-db drop                    # 모든 스키마 테이블 삭제
data-db drop housing           # housing 스키마만 삭제
data-db drop infra             # infra 스키마만 삭제
data-db drop rtms              # rtms 스키마만 삭제
data-db drop all               # 모든 스키마 테이블 삭제

# 데이터베이스 초기화 (삭제 + 생성)
data-db reset

# 테이블 목록 확인
data-db list

# 특정 테이블 구조 확인
data-db structure <table_name>

# 데이터베이스 연결 테스트
data-db test
```

**스키마 구성:**

- **housing**: 주택 관련 데이터 (공고, 유닛, 주소 등)
- **infra**: 공공시설 데이터 (지하철역, 버스정류소, 공원, 학교, 병원 등)
- **rtms**: 실거래가 및 시장 분석 데이터

---

## 📥 데이터 로딩 명령어

### `data-load`

정규화된 데이터를 데이터베이스에 적재

```bash
# 도움말 보기
data-load --help

# 주택 데이터 로드
data-load housing
data-load housing --data-dir /path/to/data
data-load housing --verbose

# 실거래가 데이터 로드 (현재 housing과 동일하게 처리)
data-load rtms
data-load rtms --data-dir /path/to/data

# 공공시설 데이터 로드
data-load infra
data-load infra --verbose

# 모든 데이터 통합 로드
data-load all
data-load all --data-dir /path/to/data
```

**데이터 소스 경로:**

- **housing**: `backend/data/normalized/housing/`
- **infra**: `backend/data/normalized/infra/`
- **rtms**: `backend/data/normalized/` (기본값)

---

## ⚙️ 환경 설정

### 필수 환경 변수

```bash
# 데이터베이스 연결 정보
export DATABASE_URL="postgresql+psycopg://postgres:post1234@localhost:5432/rey"
export PG_USER="postgres"
export PG_PASSWORD="post1234"
export PG_DB="rey"
export PG_HOST="localhost"
export PG_PORT="5432"
```

### 가상환경 활성화

```bash
# 가상환경 활성화
source .venv/bin/activate

# 프로젝트 설치
uv pip install -e .
```

---

## 🚀 일반적인 워크플로우

### 1. 초기 설정

```bash
# 가상환경 활성화
source .venv/bin/activate

# 데이터베이스 생성
data-db create

# 연결 테스트
data-db test
```

### 2. 주택 데이터 수집 및 로드

```bash
# 주택 데이터 크롤링
data-collection-housing crawl cohouse --fresh
data-collection-housing crawl sohouse --fresh

# 데이터 정규화
data-collection-housing normalized process --platform cohouse
data-collection-housing normalized process --platform sohouse

# 데이터베이스에 로드
data-load housing
```

### 3. 공공시설 데이터 수집 및 로드

```bash
# 공공시설 데이터 수집
data-collection-infra api load
data-collection-infra seoul normalize

# 데이터베이스에 로드
data-load infra
```

### 4. 데이터 확인

```bash
# 테이블 현황 확인
data-db list

# 특정 테이블 구조 확인
data-db structure addresses
```

---

## 🔧 문제 해결

### 명령어를 찾을 수 없는 경우

```bash
# 가상환경이 활성화되었는지 확인
which python
which data-db

# 프로젝트 재설치
uv pip install -e .
```

### 데이터베이스 연결 오류

```bash
# 연결 테스트
data-db test

# 환경 변수 확인
echo $DATABASE_URL
echo $PG_USER
```

### 데이터 로딩 오류

```bash
# 상세 로그와 함께 실행
data-load housing --verbose
data-load infra --verbose
```

---

## 📁 프로젝트 구조

```
backend/
├── data/
│   ├── normalized/
│   │   ├── housing/          # 주택 정규화 데이터
│   │   └── infra/            # 공공시설 정규화 데이터
│   └── raw/                  # 원시 크롤링 데이터
├── db/
│   ├── housing/              # 주택 스키마 관련
│   ├── infra/                # 인프라 스키마 관련
│   └── db_manager.py         # data-db 명령어
├── services/
│   └── data_collection/
│       ├── cli/
│       │   ├── housing/      # data-collection-housing
│       │   └── infra/        # data-collection-infra
│       ├── crawlers/         # 크롤링 모듈
│       └── normalized/       # 정규화 모듈
└── load_normalized_data.py   # data-load 명령어
```

---

**마지막 업데이트**: 2025-09-28
