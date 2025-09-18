# 🏙️ OpenAPI 데이터 수집 파이프라인

서울 열린데이터광장, 로컬데이터 포털(Open LocalData) API를 통해  
지정된 정보를 **CSV 저장** 및 **PostgreSQL DB 적재**까지 처리하는 파이프라인입니다.

---

## 📦 프로젝트 실행 방법

```bash
python run.py --source [SOURCE] --service [SERVICE] [--csv] [--db]
````

### 🔧 공통 인자 설명

| 옵션          | 설명                                          |
| ----------- | ------------------------------------------- |
| `--source`  | `localdata` 또는 `seoul` 중 선택                 |
| `--service` | `seoul` 전용: 아래의 서비스명 중 택 1 또는 `all` (전체 순회) |
| `--csv`     | CSV로 저장할 경우 추가                              |
| `--db`      | PostgreSQL로 저장할 경우 추가                       |

---

## 📍 실행 예시

### ✅ 로컬데이터 포털

| 목적                      | 명령어                                           |
| ----------------------- | --------------------------------------------- |
| 어제 하루 변동분 → CSV 저장      | `python run.py --source localdata --csv`      |
| 어제 하루 변동분 → DB 저장       | `python run.py --source localdata --db`       |
| 어제 하루 변동분 → CSV + DB 저장 | `python run.py --source localdata --csv --db` |

> 📆 기본 날짜 범위는 어제 하루 (`bgnYmd = 어제`, `endYmd = 어제`)이며, 내부 설정을 바꾸면 조절 가능합니다.

---

### ✅ 서울 열린데이터광장

| 서비스명                        | 설명              |
| --------------------------- | --------------- |
| `SearchSTNBySubwayLineInfo` | 노선별 지하철역 정보     |
| `TbPharmacyOperateInfo`     | 서울시 약국 운영 정보    |
| `ChildCareInfo`             | 서울시 어린이집 정보     |
| `childSchoolInfo`           | 서울시 유치원 일반현황    |
| `neisSchoolInfo`            | 서울시 학교 정보 (초중고) |
| `SebcCollegeInfoKor`        | 서울시 대학 및 전문대학   |
| `SearchParkInfoService`     | 서울시 주요 공원현황     |
| `all`                       | 위의 전체 서비스 순회    |

#### 예시:

| 목적                | 명령어                                                           |
| ----------------- | ------------------------------------------------------------- |
| 어린이집 정보 → CSV 저장  | `python run.py --source seoul --service ChildCareInfo --csv`  |
| 유치원 정보 → DB 저장    | `python run.py --source seoul --service childSchoolInfo --db` |
| 모든 서비스 → CSV + DB | `python run.py --source seoul --service all --csv --db`       |

---

## 💾 저장 위치

| 타입      | 폴더               |
| ------- | ---------------- |
| 로컬데이터   | `data/localdata` |
| 서울열린데이터 | `data/openseoul` |

---

## 🐘 PostgreSQL 설정 (.env 또는 시스템 환경변수)

```env
PG_DSN=postgresql+psycopg2://[유저]:[비번]@[호스트]:[포트]/[DB명]
```

예시:

```env
PG_DSN=postgresql+psycopg2://root:root1234@localhost:5432/postgres
```

> DB 저장은 `external_api_raw` 테이블에 저장되며, 스키마는 `config.py`의 `TARGET_SCHEMA`로 지정 가능합니다.

---

## 📌 패키지 설치

```bash
1) 가상환경 .venv 설치
uv venv .venv --python 3.13

가상환경 실행 
.venv\Scripts\activate

필요한 라이브러리 설치
uv pip install --upgrade pip
uv pip install -r requirements.txt
```
