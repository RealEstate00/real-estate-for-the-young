# ⚠️ 나중에 확장할 기능 - PostGIS 설치

**이 파일은 Multi-Agent 시스템이 잘 작동하는 것을 확인한 후, Infra Agent 추가 시 사용할 예정입니다.**

---

# PostGIS 설치 문제 해결

## 문제

```
extension "postgis" is not available
The extension must first be installed on the system where PostgreSQL is running.
```

## 빠른 해결 방법

### 1. docker-compose.yml 이미지 변경

`backend/docker-compose.yml` 파일에서 PostgreSQL 이미지를 변경했습니다:

```yaml
postgres:
  image: ankane/pgvector:latest  # PostGIS + pgvector 모두 포함
```

### 2. 컨테이너 재시작

```bash
# 기존 컨테이너 중지 및 삭제
cd backend
docker-compose down

# 새 이미지로 시작
docker-compose up -d

# PostGIS 확장 설치 확인
docker exec -it seoul_housing_postgres psql -U postgres -d rey -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### 3. SQL 파일 재실행

```bash
sql-executor backend/services/db/schema/infra_spatial_views.sql
```

## 대안: 현재 컨테이너에 PostGIS 추가 설치

이미 데이터가 있어서 컨테이너를 재생성하기 어려운 경우:

```bash
# 컨테이너에 접속
docker exec -it seoul_housing_postgres bash

# PostGIS 설치
apt-get update
apt-get install -y postgresql-18-postgis-3

# 컨테이너 재시작
exit
docker restart seoul_housing_postgres

# 확장 설치
docker exec -it seoul_housing_postgres psql -U postgres -d rey -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

## 확인

PostGIS가 제대로 설치되었는지 확인:

```sql
SELECT PostGIS_Version();
```

결과가 나오면 성공입니다!

