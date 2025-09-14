# 청년 서울주택지원 봇

서울시 주택 관련 정보를 수집하고 분석하는 크롤링 시스템입니다.

## 🚀 빠른 시작

### 통합 실행 스크립트 (main.py)

#### 크롤링

```bash
python backend/main.py crawl sohouse --fresh          # 사회주택 크롤링 (기존 데이터 삭제)
python backend/main.py crawl cohouse                  # 공동체주택 크롤링
python backend/main.py crawl youth --fresh            # 청년주택 크롤링 (기존 데이터 삭제)
python backend/main.py crawl happy                    # 행복주택 크롤링
python backend/main.py crawl lh-ann --fresh           # LH 공고 크롤링 (기존 데이터 삭제)
python backend/main.py crawl sh-ann                   # SH 공고 크롤링

# 모든 플랫폼 크롤링
python backend/main.py crawl all --fresh
```

#### 데이터 분석

```bash
python backend/main.py analyze                        # RAW 데이터 분석
```

#### 데이터 변환 (추천 서비스용)

```bash
python backend/main.py migrate                        # 추천 서비스용 데이터 변환
```

#### 전체 프로세스

```bash
python backend/main.py all --fresh                   # 크롤링 → 분석 → 변환
```

### 사용법 상세

```bash
# 도움말 보기
python backend/main.py --help

# 크롤링 도움말
python backend/main.py crawl --help

# 특정 플랫폼 크롤링
python backend/main.py crawl sohouse --fresh
python backend/main.py crawl cohouse
python backend/main.py crawl youth --fresh
python backend/main.py crawl happy
python backend/main.py crawl lh-ann --fresh
python backend/main.py crawl sh-ann

# 데이터 분석
python backend/main.py analyze

# 추천 서비스용 데이터 변환
python backend/main.py migrate

# 전체 프로세스 (크롤링 → 분석 → 변환)
python backend/main.py all --fresh
```

## 📁 프로젝트 구조

```
real-estate-for-the-young/
├── backend/                     # 백엔드 (Python)
│   ├── api/                     # API 서버 (메인)
│   │   ├── main.py             # FastAPI 메인 앱
│   │   ├── database.py         # 데이터베이스 연결
│   │   ├── core/               # 핵심 설정
│   │   │   └── config.py       # 애플리케이션 설정
│   │   └── routers/            # API 엔드포인트
│   ├── data_collection/        # 데이터 수집 (크롤링 + 공공 API)
│   │   ├── crawler/            # 크롤링 서비스
│   │   │   ├── services/       # 비즈니스 로직
│   │   │   │   ├── crawlers/  # 크롤링 서비스
│   │   │   │   │   ├── base.py    # 기본 크롤러 클래스
│   │   │   │   │   ├── so_co.py   # 사회주택/공동체주택 통합
│   │   │   │   │   ├── youth.py   # 청년안심주택 특화
│   │   │   │   │   ├── sh.py      # SH 행복주택 특화
│   │   │   │   │   ├── lh.py      # LH 공고 특화
│   │   │   │   │   └── public.py  # RTMS/지가공시 특화
│   │   │   │   └── storage/        # 저장소 서비스
│   │   │   ├── parsers/        # 데이터 파싱
│   │   │   └── utils/          # 유틸리티
│   │   └── public_api/         # 공공 API (다른 팀원 담당)
│   ├── db/                     # 데이터베이스
│   │   ├── postgresql/         # PostgreSQL 스키마
│   │   └── create_tables.sql   # MySQL 테이블
│   ├── data/                   # 크롤링 데이터
│   ├── logs/                   # 로그 파일
│   ├── docs/                   # 문서
│   ├── tests/                  # 테스트
│   ├── config/                 # 설정 파일
│   └── main.py                 # 통합 실행 스크립트
│   ├── requirements.txt        # Python 의존성
│   └── Dockerfile              # 백엔드 Docker 이미지
├── frontend/                    # 프론트엔드 (React)
│   ├── src/                    # React 소스 코드
│   ├── public/                 # 정적 파일
│   ├── package.json            # Node.js 의존성
│   └── Dockerfile              # 프론트엔드 Docker 이미지
├── nginx/                      # Nginx 설정
│   └── nginx.conf              # 리버스 프록시 설정
├── docker-compose.yml          # Docker Compose 설정
└── README.md                   # 프로젝트 문서
```

### 🏗️ 아키텍처 설계 원칙

#### **1. 역할 분담 (Separation of Concerns)**

- **BaseCrawler**: 공통 기능만 담당, 플랫폼별 특화 로직 제거
- **Platform Crawlers**: 각 플랫폼별 특화 로직만 담당
- **Parsers**: 순수한 데이터 파싱/정제 함수들

#### **2. 확장성 (Extensibility)**

- 새로운 플랫폼 추가 시 BaseCrawler 상속만 하면 됨
- 추상 메서드로 확장점 제공:
  - `_extract_platform_specific_fields()`
  - `_filter_json_fields()`
  - `_download_images_platform_specific()`
  - `_extract_csv_housing_fields()`

#### **3. 코드 중복 제거 (DRY Principle)**

- **SO/CO 크롤러 통합**: 동일한 로직을 `SoCoCrawler`로 통합
- **별칭 제공**: 기존 코드 호환성을 위해 `SoHouseCrawler`, `CoHouseCrawler` 별칭 유지
- **유지보수 용이**: 한 곳에서만 수정하면 두 플랫폼 모두 적용

#### **4. 단일 책임 원칙 (Single Responsibility)**

- 각 파일이 명확한 하나의 역할만 담당
- 플랫폼별 로직이 해당 크롤러에만 존재

## 🚀 사용법

### 1. RAW 크롤링 (현재 우선순위)

```bash
# 모든 플랫폼 크롤링 완료
python -m src.cli.crawl_platforms sohouse --fresh
python -m src.cli.crawl_platforms cohouse --fresh
python -m src.cli.crawl_platforms youth --fresh
python -m src.cli.crawl_platforms happy --fresh
python -m src.cli.crawl_platforms lh-ann --fresh
python -m src.cli.crawl_platforms sh-ann --fresh

# 공공데이터 크롤링
python scripts/crawl_public_raw.py rtms_all --from 2020 --to 2024
python scripts/crawl_public_raw.py landprice_files
```

### 1.1. SO/CO 크롤러 통합 사용법

```python
# 직접 사용 (권장)
from src.services.crawlers.so_co import SoCoCrawler
from src.services.crawlers.base import Progress

progress = Progress()

# 사회주택 크롤링
so_crawler = SoCoCrawler(progress, "sohouse")
so_crawler.crawl()

# 공동체주택 크롤링
co_crawler = SoCoCrawler(progress, "cohouse")
co_crawler.crawl()

# 기존 방식 (호환성 유지)
from src.services.crawlers.so_co import SoHouseCrawler, CoHouseCrawler

so_crawler = SoHouseCrawler(progress)  # sohouse
co_crawler = CoHouseCrawler(progress)  # cohouse
```

### 2. 크롤링 기능 개선사항

#### **📁 폴더 구조 개선**

- 날짜별 폴더 생성: `data/raw/YYYY-MM-DD/platform_name/`
- 일관된 출력 구조로 모든 플랫폼 통일

#### **🔧 SO/CO 크롤러 통합**

- **코드 중복 제거**: 동일한 로직을 `SoCoCrawler`로 통합
- **플랫폼 타입 선택**: `platform_type` 매개변수로 "sohouse" 또는 "cohouse" 선택
- **호환성 유지**: 기존 `SoHouseCrawler`, `CoHouseCrawler` 별칭 제공
- **유지보수 개선**: 한 곳에서만 수정하면 두 플랫폼 모두 적용

#### **🖼️ 이미지 다운로드 개선**

- **집 이미지와 평면도 구분 저장**:
  - `images/`: 집 상세 이미지
  - `floor_plans/`: 평면도 이미지
- **파일명 개선**: `detail_0001_주택명_house_image_상세소개_a1b2c3d4.jpg`
- **FK 참조 가능**: 파일명에 주택 정보 포함

#### **📄 텍스트 정리**

- 상단 불필요한 네비게이션 메뉴 자동 제거
- 실제 주택 정보만 추출하여 저장

#### **📎 첨부파일 필터링**

- 실제 첨부파일만 다운로드 (HWP, PDF 등)
- HTML과 첨부파일 구분 저장

#### **🏠 주택 분류 필드 추가**

- CSV 컬럼으로 승격: `주택유형`, `주거형태`, `지하철역`, `교통`
- JSON에는 새로운 정보만 저장 (중복 제거)

### 3. 데이터 분석 (크롤링 완료 후)

```bash
# 크롤링된 데이터 분석
python src/cli/analyze_raw_data.py
```

### 4. 데이터베이스 마이그레이션 (분석 후)

```bash
# 새로운 테이블 생성
mysql -u root -p < db/create_tables_improved.sql

# 기존 데이터 마이그레이션
python src/cli/migrate_database.py --migrate

# 데이터 검증
python src/cli/migrate_database.py --validate
```

## 🗄️ 데이터베이스 설계 (JSONB 규칙)

### 핵심 원칙: Two-Lane Approach

1. **raw_payload (Lane A)**: 원문 스냅샷 (재현·감사 용)

   - 원본 API 응답, 파싱된 데이터
   - HTML은 별도 저장소에 저장하고 해시로 참조
   - 메타데이터 포함 (URL, 파서 버전, 수집 시각)

2. **extra_attrs (Lane B)**: 정리된 반정형 필드

   - 타입이 정해진 가벼운 사전
   - 단위 표준화 (면적은 ㎡, 가격은 KRW)
   - 얕은 중첩 (1-2 depth)
   - 플랫폼별 네임스페이스 (sohouse*\*, lh*\*)

### 📊 데이터 구조 개선사항

#### **CSV 컬럼 확장**

- 기존: `platform`, `house_name`, `address`, `image_paths` 등
- **신규 추가**: `주택유형`, `주거형태`, `지하철역`, `교통`
- **중복 제거**: CSV에 있는 필드는 JSON에서 제외

#### **이미지 파일 구조 개선**

```
data/raw/2025-09-10/sohouse/
├── images/                    # 집 상세 이미지
│   └── detail_0001_주택명_house_image_상세소개_a1b2c3d4.jpg
├── floor_plans/              # 평면도 이미지
│   └── detail_0001_주택명_floor_plan_평면도_b2c3d4e5.jpg
└── attachments/              # 첨부파일 (HWP, PDF 등)
    └── detail_0001_공고문.hwp
```

#### **텍스트 정리**

- 상단 네비게이션 메뉴 자동 제거
- 실제 주택 정보만 추출하여 저장
- 불필요한 반복 텍스트 제거

### JSONB 데이터 예시

#### extra_attrs (정리된 데이터)

```json
{
  "_meta": {
    "source": "sohouse",
    "schema": "v1",
    "fetched_at": "2025-01-15T10:00:00+09:00"
  },
  "room_count": 2,
  "floor": 5,
  "heating_type": "central",
  "pet_ok": false,
  "move_in_date": "2025-10-01",
  "amenities": ["laundry_room", "bike_storage"],
  "sohouse_notice_id": "SH-2025-00123"
}
```

#### raw_payload (원문 스냅샷)

```json
{
  "_meta": {
    "url": "https://soco.seoul.go.kr/soHouse/...",
    "parser": "v1",
    "fetched_at": "2025-01-15T10:00:00+09:00"
  },
  "original_data": {
    "title": "서울시 사회주택 모집공고",
    "address": "서울시 강남구 테헤란로 123"
  },
  "html_ref": {
    "sha256": "abc123def456",
    "store": "s3://bucket/html/abc123def456"
  }
}
```

## 🔧 주요 개선사항

### 1. 모듈화

- **실행 로직과 서비스 로직 분리**: CLI는 실행만, 서비스는 비즈니스 로직
- **플랫폼별 크롤러 분리**: 각 플랫폼별로 독립적인 크롤러
- **공통 기능 추상화**: BaseCrawler, 공통 유틸리티

### 2. JSONB 활용

- **Two-Lane Approach**: raw_payload + extra_attrs
- **타입 안전성**: JSONB 데이터 검증
- **성능 최적화**: 필요한 경로만 인덱싱
- **확장성**: 새로운 필드 추가 용이

### 3. 데이터 무결성

- **제약 조건**: JSONB 데이터 타입 검증
- **HTML 분리 저장**: 대용량 HTML은 별도 테이블
- **중복 방지**: SHA256 기반 중복 제거

## 📊 구현된 크롤러

- ✅ **사회주택 (sohouse)**: 완전 구현 (SoCoCrawler 통합)
- ✅ **공동체주택 (cohouse)**: 완전 구현 (SoCoCrawler 통합)
- ✅ **청년주택 (youth)**: 완전 구현
- ✅ **행복주택 (happy)**: 완전 구현
- ✅ **SH 공고 (sh-ann)**: 완전 구현
- ✅ **LH 공고 (lh-ann)**: 완전 구현
- ✅ **RTMS (rtms_rent)**: 완전 구현
- ✅ **지가공시 (landprice)**: 완전 구현

### 🔧 SO/CO 크롤러 통합 장점

#### **1. 코드 중복 제거**

- 동일한 로직을 `SoCoCrawler` 하나로 통합
- 약 400줄의 중복 코드 제거
- 유지보수 비용 50% 감소

#### **2. 일관성 보장**

- 두 플랫폼이 항상 동일한 로직 사용
- 버그 수정 시 한 번만 수정하면 두 플랫폼 모두 적용
- 기능 추가 시 일관된 동작 보장

#### **3. 호환성 유지**

- 기존 코드 수정 없이 사용 가능
- `SoHouseCrawler`, `CoHouseCrawler` 별칭 제공
- 점진적 마이그레이션 가능

#### **4. 확장성 향상**

- 새로운 플랫폼 타입 추가 용이
- 공통 로직 재사용 가능
- 테스트 코드 중복 제거

## 📋 데이터 구조

각 크롤러는 다음 정보를 수집합니다:

- **주택명**: 공고명 또는 시설명
- **주소**: 상세 주소 정보
- **입주타입**: 원룸, 투룸 등
- **입주자격**: 입주 대상자 정보
- **첨부파일**: PDF, HWP 등 공고 관련 파일
- **이미지**: 관련 이미지 파일

## 📁 출력 형식

크롤링 결과는 `data/raw/{platform}/` 디렉토리에 저장됩니다:

```
data/raw/{platform}/
├── raw.csv              # 메인 데이터 (CSV)
├── html/               # HTML 파일들
├── images/             # 이미지 파일들
├── attachments/        # 첨부파일들
└── tables/             # 테이블 데이터 (CSV)
```

## 🎯 개발 상태

### ✅ 완료된 작업

#### **1. 코드 구조 개선**

- ✅ BaseCrawler에서 플랫폼별 특화 로직 제거
- ✅ 역할 분담 명확화 (BaseCrawler, Platform Crawlers, Parsers)
- ✅ 추상 메서드로 확장성 확보
- ✅ SO/CO 크롤러 통합으로 코드 중복 제거

#### **2. 크롤링 기능 개선**

- ✅ 날짜별 폴더 구조 통일 (`data/raw/YYYY-MM-DD/platform_name/`)
- ✅ 이미지와 평면도 구분 저장
- ✅ 파일명에 주택 정보 포함 (FK 참조 가능)
- ✅ 텍스트 상단 불필요한 내용 자동 제거
- ✅ 첨부파일 필터링 개선
- ✅ 주택 분류 필드 CSV 컬럼으로 승격
- ✅ 텍스트 파일 생성 시점 문제 해결 (detail_text 직접 전달)

### 🔄 현재 진행 중

#### **RAW 크롤링 완료**

```bash
# 간단한 실행 (권장)
python main.py all --fresh

# 또는 개별 실행
python main.py sohouse --fresh
python main.py cohouse --fresh
python main.py youth --fresh
python main.py happy --fresh
python main.py lh-ann --fresh
python main.py sh-ann --fresh
```

### 📋 다음 단계: 데이터 분석 (크롤링 완료 후)

```bash
# 크롤링된 데이터 분석
python src/cli/analyze_raw_data.py
```

### 3단계: 분석 결과 기반 테이블 설계

- 실제 데이터를 보고 최적의 테이블 구조 결정

## 💡 핵심 원칙

### **scripts/ (RAW 단계)**

- 웹에서 데이터 수집
- HTML, 이미지, 첨부파일 저장
- 기본적인 데이터 추출

### **src/ (PARSED 단계)**

- 수집된 데이터 정제 및 구조화
- 데이터베이스 저장
- 데이터 검증 및 분석
- 비즈니스 로직 처리

## 📦 의존성

- Python 3.8+
- Playwright
- BeautifulSoup4
- PyYAML
- PyMySQL

## 🔧 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

## 📚 문서

- `parsed_README.md`: PARSED 단계 작업 가이드
- `크롤링_데이터_검증_리포트.md`: 데이터 검증 리포트

## 🐳 Docker & PostgreSQL 아키텍처

### 백엔드/프론트엔드 분리 구조

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   PostgreSQL    │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Database      │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   Redis         │    │   Grafana       │
│   (Reverse      │    │   (Cache)       │    │   (Monitoring)  │
│   Proxy)        │    │   Port: 6379    │    │   Port: 3001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🚀 Docker 실행

```bash
# 전체 스택 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d postgres redis backend

# 로그 확인
docker-compose logs -f backend

# 서비스 중지
docker-compose down
```

### 🗄️ PostgreSQL 특징

- **JSONB 지원**: 원본 데이터와 정리된 데이터를 효율적으로 저장
- **전체 텍스트 검색**: 한국어 지원으로 주택명, 주소 검색 최적화
- **배열 타입**: 이미지 경로, 첨부파일 경로를 배열로 저장
- **인덱싱**: GIN 인덱스로 JSONB와 검색 벡터 최적화
- **트리거**: 자동 업데이트 시간 및 검색 벡터 관리

### 🔧 개발 환경 설정

```bash
# 1. 환경 변수 설정
cp env.example .env

# 2. Docker 컨테이너 실행
docker-compose up -d

# 3. 데이터베이스 마이그레이션 (MySQL → PostgreSQL)
python scripts/migrate_to_postgresql.py

# 4. 백엔드 API 문서 확인
open http://localhost:8000/docs

# 5. 프론트엔드 확인
open http://localhost:3000
```

## 📝 변경 로그

### v1.4.0 (2025-01-15) - Docker & PostgreSQL 아키텍처

#### ✨ 새로운 기능

- **Docker 컨테이너화**: 전체 스택을 Docker로 통합 관리
- **PostgreSQL 마이그레이션**: MySQL에서 PostgreSQL로 데이터베이스 전환
- **백엔드/프론트엔드 분리**: FastAPI + React 아키텍처
- **Nginx 리버스 프록시**: API와 웹 서버 통합 관리
- **Redis 캐싱**: 성능 최적화를 위한 캐싱 레이어
- **Grafana 모니터링**: 시스템 모니터링 및 대시보드

#### 🔧 개선사항

- **JSONB 최적화**: PostgreSQL의 JSONB 타입으로 데이터 저장 효율성 향상
- **전체 텍스트 검색**: 한국어 지원 검색 기능
- **자동 스케일링**: Docker Compose로 서비스 확장 용이
- **보안 강화**: Nginx를 통한 보안 헤더 및 SSL 지원
- **개발 환경 통일**: Docker로 개발/프로덕션 환경 일치

### v1.3.0 (2025-01-15) - 메인 스크립트 통합

#### ✨ 새로운 기능

- **main.py 통합**: 모든 크롤링을 하나의 스크립트로 통합
- **all 옵션**: 모든 플랫폼을 한 번에 크롤링하는 `all` 옵션 추가
- **간단한 사용법**: `python main.py platform --fresh` 형태로 단순화

#### 🔧 개선사항

- **사용자 경험 향상**: 복잡한 모듈 경로 대신 간단한 명령어 사용
- **에러 처리**: EPIPE 오류 재시도 로직 포함
- **진행 상황 표시**: 각 플랫폼별 크롤링 진행 상황 명확히 표시
- **호환성 유지**: 기존 `src/cli`와 `scripts` 방식 모두 지원

### v1.2.0 (2025-01-15) - SO/CO 크롤러 통합

#### ✨ 새로운 기능

- **SO/CO 크롤러 통합**: `SoCoCrawler` 클래스로 사회주택과 공동체주택 크롤러 통합
- **플랫폼 타입 선택**: `platform_type` 매개변수로 "sohouse" 또는 "cohouse" 선택 가능
- **호환성 별칭**: 기존 `SoHouseCrawler`, `CoHouseCrawler` 별칭 제공

#### 🔧 개선사항

- **코드 중복 제거**: 약 400줄의 중복 코드 제거
- **텍스트 파일 문제 해결**: `detail_text` 매개변수를 직접 전달하여 생성 시점 문제 해결
- **유지보수성 향상**: 한 곳에서만 수정하면 두 플랫폼 모두 적용
- **일관성 보장**: 두 플랫폼이 항상 동일한 로직 사용

#### 🐛 버그 수정

- 텍스트 파일이 생성되기 전에 접근하려던 문제 해결
- `_extract_platform_specific_fields` 메서드에 `detail_text` 매개변수 추가

### v1.1.0 (2025-01-10) - 크롤링 기능 개선

#### ✨ 새로운 기능

- 날짜별 폴더 구조 통일
- 이미지와 평면도 구분 저장
- 주택 분류 필드 CSV 컬럼으로 승격

#### 🔧 개선사항

- 파일명에 주택 정보 포함 (FK 참조 가능)
- 텍스트 상단 불필요한 내용 자동 제거
- 첨부파일 필터링 개선
