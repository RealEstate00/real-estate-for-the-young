# Real Estate for the Young

서울시 주택 관련 정보를 수집하고 분석하는 데이터 수집 및 관리 시스템입니다.

## 📋 시스템 요구사항

- **Python**: 3.12+ (권장: 3.12)
- **OS**: macOS, Linux, Windows
- **데이터베이스**: PostgreSQL (선택사항)

## 🚀 빠른 시작

### 1. 저장소 클론 및 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd real-estate-for-the-young

# uv 설치 (아직 설치하지 않은 경우)
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 가상환경 생성 및 패키지 설치
uv venv --python 3.12
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\Activate.ps1
uv pip install -e .

# Playwright 브라우저 설치 (크롤링용)
playwright install chromium
```

### 2. 데이터베이스 설정 (선택사항)

```bash
# PostgreSQL 설정 후
data-db create    # 데이터베이스 테이블 생성
data-db test      # 연결 테스트
```

### 3. 데이터 수집 및 로드

```bash
# 주택 데이터 크롤링
data-collection-housing crawl sohouse --fresh
data-collection-housing crawl cohouse --fresh

# 데이터 정규화
data-collection-housing normalized process --platform sohouse
data-collection-housing normalized process --platform cohouse

# 데이터베이스에 로드
data-load housing

# 공공시설 데이터 수집 및 로드
data-collection-infra api load
data-load infra
```

## 📋 주요 명령어

### 데이터 수집 명령어

#### `data-collection-housing` - 주택 데이터 수집

```bash
# 크롤링
data-collection-housing crawl sohouse --fresh
data-collection-housing crawl cohouse --fresh

# 데이터 정규화
data-collection-housing normalized process --platform sohouse
data-collection-housing normalized process --platform cohouse
```

#### `data-collection-infra` - 공공시설 데이터 수집

```bash
# API 데이터 수집
data-collection-infra api load

# 서울시 공공데이터 API
data-collection-infra seoul normalize
data-collection-infra seoul load
```

### 데이터베이스 관리 명령어

#### `data-db` - 데이터베이스 관리

```bash
# 데이터베이스 생성
data-db create

# 테이블 삭제 (주의!)
data-db drop                    # 모든 스키마 테이블 삭제
data-db drop housing           # housing 스키마만 삭제
data-db drop infra             # infra 스키마만 삭제

# 데이터베이스 초기화 (삭제 + 생성)
data-db reset

# 테이블 목록 확인
data-db list

# 특정 테이블 구조 확인
data-db structure <table_name>

# 데이터베이스 연결 테스트
data-db test
```

### 데이터 로딩 명령어

#### `data-load` - 정규화된 데이터를 데이터베이스에 적재

```bash
# 주택 데이터 로드
data-load housing
data-load housing --data-dir /path/to/data

# 실거래가 데이터 로드
data-load rtms

# 공공시설 데이터 로드
data-load infra

# 모든 데이터 통합 로드
data-load all
```

## 🗄️ 데이터베이스 스키마

### 스키마 구성

- **housing**: 주택 관련 데이터 (공고, 유닛, 주소 등)
- **infra**: 공공시설 데이터 (지하철역, 버스정류소, 공원, 학교, 병원 등)
- **rtms**: 실거래가 및 시장 분석 데이터

### 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env

# 데이터베이스 연결 정보
export DATABASE_URL="postgresql+psycopg://postgres:post1234@localhost:5432/rey"
export PG_USER="postgres"
export PG_PASSWORD="post1234"
export PG_DB="rey"
export PG_HOST="localhost"
export PG_PORT="5432"
```

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
```

### 데이터 로딩 오류

```bash
# 상세 로그와 함께 실행
data-load housing --verbose
data-load infra --verbose
```

## 📊 수집 가능한 데이터

### 주택 데이터

- 사회주택 공고 (sohouse)
- 공동체주택 공고 (cohouse)
- 청년주택 공고 (youth)

### 공공시설 데이터

- 지하철역 정보
- 버스정류소 정보
- 공원 정보
- 학교 정보
- 병원 정보
- 약국 정보

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
data-collection-housing crawl sohouse --fresh
data-collection-housing crawl cohouse --fresh

# 데이터 정규화
data-collection-housing normalized process --platform sohouse
data-collection-housing normalized process --platform cohouse

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

## 📚 추가 문서

- [COMMANDS.md](COMMANDS.md) - 상세한 명령어 가이드
- [backend/env.example](backend/env.example) - 환경 변수 예시

## 🎯 개발 상태

### ✅ 완료된 기능

- 주택 데이터 크롤링 (사회주택, 공동체주택)
- 데이터 정규화 및 품질 개선
- PostgreSQL 데이터베이스 통합
- 공공시설 데이터 수집 (서울시 API)
- CLI 명령어 체계 구축

### 🔄 진행 중

- 청년주택 크롤링 개선
- 데이터 분석 및 시각화
- 웹 인터페이스 개발

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

**마지막 업데이트**: 2025-09-28
