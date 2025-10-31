# Real Estate for the Young - 명령어 가이드

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 활성화
uv venv .venv --python 3.12
source .venv/bin/activate

# 프로젝트 설치
uv pip install -e .
```

### 2. 데이터베이스 설정

```bash
# 데이터베이스 테이블 생성
data-db create

# 연결 테스트
data-db test
```

### 3. 데이터 수집 및 로드

```bash
# 주택 데이터 크롤링
data-collection-housing crawl cohouse
data-collection-housing crawl sohouse

# 공공시설 데이터 수집
data-collection-infra api collect
data-collection-infra normalized process

# 실거래 데이터 정규화
data-collection-rtms normalized process

# 데이터베이스에 로드
data-load housing
data-load infra
data-load rtms
```

### 4. 서버 실행

```bash
# 1. FastAPI 백엔드 서버 시작 (첫 번째 터미널) -- 실행은 되는데 아직 서버연결이 안된듯
api

# 2. React 프론트엔드 시작 (두 번째 터미널) 
cd frontend/react
npm install
cd ../..
python -m frontend.react.cli
```

**접속 정보:**
- FastAPI 서버: http://localhost:8000
- FastAPI 문서: http://localhost:8000/docs
- React 프론트엔드: http://localhost:3000

---

## 📋 명령어 목록

### 웹 애플리케이션 서버

#### `api` - FastAPI 백엔드 서버

```bash
# API 서버 시작
api

# API 서버 재시작 (기존 프로세스 종료 후 재시작)
python -m backend.services.api.cli restart

# 수동 실행 (Python 모듈로)
python -m backend.services.api.cli
```

**접속 정보:**
- API 서버: http://localhost:8000
- API 문서 (Swagger): http://localhost:8000/docs
- API 문서 (ReDoc): http://localhost:8000/redoc

#### `python -m frontend.react.cli` - React 프론트엔드

```bash
# React 개발 서버 시작
python -m frontend.react.cli

# 또는 직접 npm 실행
cd frontend/react
npm run dev
```

**접속 정보:**
- 프론트엔드: http://localhost:3000
- API URL: http://localhost:8000 (환경 변수로 설정 가능)

### 데이터 수집

#### `data-collection-housing` - 주택 데이터 수집

```bash
# 크롤링
data-collection-housing crawl cohouse
data-collection-housing crawl sohouse

# 데이터 정규화
data-collection-housing normalized process --platform cohouse
data-collection-housing normalized process --platform sohouse
```

#### `data-collection-infra` - 공공시설 데이터 수집

```bash
# API 데이터 수집
data-collection-infra api collect

# 데이터 정규화
data-collection-infra normalized process
```

#### `data-collection-rtms` - 실거래 데이터 수집 

```bash
# 데이터 정규화 (모든 주택유형)
data-collection-rtms normalized process

# 크롤링 csv 다운 -> 해당 파일로 노말라이징 안함

# 상세 로그와 함께 실행
data-collection-rtms normalized process --verbose
```



### 데이터베이스 관리

#### `data-db` - 데이터베이스 관리

```bash
# 데이터베이스 생성
data-db create

# 테이블 삭제 (주의!)
data-db drop                    # 모든 스키마 테이블 삭제
data-db drop housing           # housing 스키마만 삭제
data-db drop infra             # infra 스키마만 삭제
data-db drop rtms             # rtms 스키마만 삭제

# 데이터베이스 초기화 (삭제 + 생성)
data-db drop && data-db create

# 테이블 목록 확인
data-db list

# 데이터베이스 연결 테스트
data-db test
```

### 데이터 로딩

#### `data-load` - 정규화된 데이터를 데이터베이스에 적재

```bash
# 주택 데이터 로드
data-load housing

# 공공시설 데이터 로드
data-load infra

# 실거래 데이터 로드
data-load rtms

# 모든 데이터 통합 로드 (주택 + 공공시설 + 실거래)
data-load all
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
```

### 데이터 로딩 오류

```bash
# 상세 로그와 함께 실행
data-load housing --verbose
data-load infra --verbose
```

---

**마지막 업데이트**: 2025-09-30
