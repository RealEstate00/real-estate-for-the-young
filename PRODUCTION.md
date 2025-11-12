# 🚀 프로덕션 환경 배포 가이드

## 📋 목차
1. [사전 요구사항](#사전-요구사항)
2. [권한 문제 해결](#권한-문제-해결)
3. [환경 설정](#환경-설정)
4. [배포 실행](#배포-실행)
5. [문제 해결](#문제-해결)

---

## 사전 요구사항

### 필수 소프트웨어
- Docker Engine 20.10 이상
- Docker Compose v2 이상
- 최소 10GB 이상의 여유 디스크 공간

### Docker 설치 확인
```bash
docker --version
docker-compose --version
```

---

## 권한 문제 해결

### ⚠️ 중요: 파일 권한 설정

프로덕션 환경에서는 Docker 컨테이너 내부의 `appuser` (UID 1000)가 파일에 접근합니다.
**권한 문제로 인해 다음 기능들이 작동하지 않을 수 있습니다:**
- OpenAI API 호출 실패
- 대화 요약 모델 다운로드 실패
- HuggingFace 모델 캐시 접근 실패
- 로그 파일 생성 실패

### 1. 필수 디렉토리 생성 및 권한 설정

```bash
# 프로젝트 루트에서 실행
cd /path/to/real-estate-for-the-young

# 필수 디렉토리 생성
mkdir -p backend/data
mkdir -p backend/logs
mkdir -p ~/.cache/huggingface

# 권한 설정 (UID 1000 = appuser)
sudo chown -R 1000:1000 backend/data
sudo chown -R 1000:1000 backend/logs
sudo chown -R 1000:1000 ~/.cache/huggingface

# 또는 현재 사용자와 공유
sudo chown -R $(id -u):$(id -g) backend/data
sudo chown -R $(id -u):$(id -g) backend/logs
chmod -R 775 backend/data
chmod -R 775 backend/logs
```

### 2. macOS에서 권한 문제 해결

macOS에서는 Docker Desktop의 파일 공유 설정이 필요합니다:

```bash
# Docker Desktop 설정 확인
# Settings > Resources > File Sharing에서 다음 경로 추가:
# - /Users/your-username/.cache/huggingface
# - /path/to/real-estate-for-the-young/backend

# 권한 재설정
sudo chown -R $(id -u):staff backend/data
sudo chown -R $(id -u):staff backend/logs
sudo chown -R $(id -u):staff ~/.cache/huggingface
chmod -R 755 backend/data
chmod -R 755 backend/logs
chmod -R 755 ~/.cache/huggingface
```

### 3. Linux에서 권한 문제 해결

```bash
# Docker 그룹에 사용자 추가
sudo usermod -aG docker $USER
newgrp docker

# 권한 설정
sudo chown -R 1000:1000 backend/data
sudo chown -R 1000:1000 backend/logs
sudo chown -R 1000:1000 ~/.cache/huggingface

# SELinux가 활성화된 경우
sudo chcon -Rt svirt_sandbox_file_t backend/data
sudo chcon -Rt svirt_sandbox_file_t backend/logs
sudo chcon -Rt svirt_sandbox_file_t ~/.cache/huggingface
```

---

## 환경 설정

### 1. 환경 변수 파일 생성

프로젝트 루트에 `.env` 파일을 생성합니다:

```bash
# .env 파일 생성
cat > .env << 'EOF'
# Django 설정
DJANGO_SECRET_KEY=your-super-secret-key-change-this-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# 데이터베이스 설정
PG_USER=postgres
PG_PASSWORD=your-secure-password-here
PG_DB=rey

# LLM API 키 (필수)
GROQ_API_KEY=your-groq-api-key-here

# OpenAI API 키 (선택사항 - 대화 요약 기능 사용 시)
OPENAI_API_KEY=your-openai-api-key-here

# HuggingFace 토큰 (선택사항)
HF_TOKEN=your-huggingface-token-here

# 임베딩 모델 선택 (E5_SMALL, E5_BASE, E5_LARGE, KAKAO)
RAG_EMBEDDING_MODEL=E5_LARGE
EOF

# 권한 설정 (보안)
chmod 600 .env
```

### 2. 환경 변수 설명

| 변수명 | 필수 여부 | 설명 |
|--------|----------|------|
| `DJANGO_SECRET_KEY` | ✅ 필수 | Django 암호화 키 (50자 이상 랜덤 문자열) |
| `ALLOWED_HOSTS` | ✅ 필수 | 허용할 호스트 도메인 (쉼표로 구분) |
| `CORS_ORIGINS` | ✅ 필수 | CORS 허용 도메인 (쉼표로 구분) |
| `PG_PASSWORD` | ✅ 필수 | PostgreSQL 비밀번호 (강력한 비밀번호 사용) |
| `GROQ_API_KEY` | ✅ 필수 | Groq API 키 (LLM 사용) |
| `OPENAI_API_KEY` | ⚠️ 권장 | OpenAI API 키 (대화 요약 기능) |
| `HF_TOKEN` | ❌ 선택 | HuggingFace 토큰 (비공개 모델 사용 시) |
| `RAG_EMBEDDING_MODEL` | ❌ 선택 | 임베딩 모델 (기본값: E5_LARGE) |

### 3. Django SECRET_KEY 생성

```bash
# Python으로 랜덤 SECRET_KEY 생성
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 배포 실행

### 1. Docker 이미지 가져오기

```bash
# Docker Hub에서 최신 이미지 가져오기
docker-compose -f docker-compose.prod.yml pull
```

### 2. 컨테이너 실행

```bash
# 백그라운드에서 실행
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. 데이터베이스 초기화

```bash
# PostgreSQL 컨테이너 접속하여 auth 테이블 생성
docker exec -i seoul_housing_postgres psql -U postgres -d rey < backend/services/db/schema/auth_schema.sql

# 또는 SQL 파일 직접 실행
docker exec -i seoul_housing_postgres psql -U postgres -d rey <<EOF
-- auth 스키마 생성
CREATE SCHEMA IF NOT EXISTS auth;

-- users 테이블 생성
CREATE TABLE IF NOT EXISTS auth.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    last_login TIMESTAMPTZ,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- conversations 테이블 생성
CREATE TABLE IF NOT EXISTS auth.conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- messages 테이블 생성
CREATE TABLE IF NOT EXISTS auth.messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES auth.conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON auth.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON auth.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON auth.messages(created_at);
EOF
```

### 4. 서비스 확인

```bash
# 헬스 체크
curl http://localhost:8000/api/llm/health

# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 로그 확인 (실시간)
docker-compose -f docker-compose.prod.yml logs -f api
```

### 5. 접속 정보

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **PostgreSQL**: localhost:55432 (호스트에서 접속 시)

---

## 문제 해결

### 1. API 응답이 없는 경우

**증상**: 프론트엔드에서 요청을 보냈지만 응답이 없음

**원인**:
- Docker 컨테이너 내부에서 파일 접근 권한 문제
- OpenAI API 키 누락으로 대화 요약 실패
- HuggingFace 모델 다운로드 실패

**해결 방법**:
```bash
# 1. 권한 확인
docker exec seoul_housing_api ls -la /app/data
docker exec seoul_housing_api ls -la /app/logs
docker exec seoul_housing_api ls -la /home/appuser/.cache/huggingface

# 2. 권한 재설정
sudo chown -R 1000:1000 backend/data
sudo chown -R 1000:1000 backend/logs
sudo chown -R 1000:1000 ~/.cache/huggingface

# 3. 컨테이너 재시작
docker-compose -f docker-compose.prod.yml restart api

# 4. 로그 확인
docker-compose -f docker-compose.prod.yml logs api | grep -i "error\|permission\|denied"
```

### 2. HuggingFace 모델 다운로드 실패

**증상**: `PermissionError` 또는 `OSError` 발생

**해결 방법**:
```bash
# 1. 캐시 디렉토리 권한 확인
ls -la ~/.cache/huggingface

# 2. 권한 재설정
sudo chown -R 1000:1000 ~/.cache/huggingface
chmod -R 755 ~/.cache/huggingface

# 3. 컨테이너 내부에서 직접 다운로드
docker exec -it seoul_housing_api bash
cd /home/appuser/.cache/huggingface
ls -la

# 4. 컨테이너 재시작
docker-compose -f docker-compose.prod.yml restart api
```

### 3. PostgreSQL 연결 실패

**증상**: `Connection refused` 또는 `could not connect to server`

**해결 방법**:
```bash
# 1. PostgreSQL 상태 확인
docker-compose -f docker-compose.prod.yml ps postgres

# 2. PostgreSQL 로그 확인
docker-compose -f docker-compose.prod.yml logs postgres

# 3. 데이터베이스 연결 테스트
docker exec -it seoul_housing_postgres psql -U postgres -d rey -c "SELECT 1;"

# 4. 네트워크 확인
docker network ls
docker network inspect real-estate-for-the-young_housing_network
```

### 4. 로그 파일 생성 실패

**증상**: 로그가 기록되지 않음

**해결 방법**:
```bash
# 1. 로그 디렉토리 권한 확인
ls -la backend/logs

# 2. 권한 재설정
sudo chown -R 1000:1000 backend/logs
chmod -R 775 backend/logs

# 3. 컨테이너 재시작
docker-compose -f docker-compose.prod.yml restart api
```

### 5. 포트 충돌

**증상**: `Address already in use`

**해결 방법**:
```bash
# 1. 포트 사용 확인
lsof -i :8000
lsof -i :3000
lsof -i :55432

# 2. docker-compose.prod.yml 포트 변경
# ports:
#   - "8001:8000"  # API 포트 변경
#   - "3001:3000"  # Frontend 포트 변경
#   - "55433:5432" # PostgreSQL 포트 변경

# 3. 변경 후 재시작
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### 6. 메모리 부족

**증상**: Container killed (OOM)

**해결 방법**:
```bash
# 1. Docker 메모리 확인
docker stats

# 2. docker-compose.prod.yml에 메모리 제한 추가
# services:
#   api:
#     deploy:
#       resources:
#         limits:
#           memory: 8G
#         reservations:
#           memory: 4G

# 3. 또는 더 작은 임베딩 모델 사용
# .env 파일에서:
# RAG_EMBEDDING_MODEL=E5_SMALL  # 대신 E5_LARGE
```

---

## 유지보수

### 로그 확인
```bash
# 전체 로그
docker-compose -f docker-compose.prod.yml logs

# 특정 서비스 로그
docker-compose -f docker-compose.prod.yml logs api
docker-compose -f docker-compose.prod.yml logs frontend
docker-compose -f docker-compose.prod.yml logs postgres

# 실시간 로그
docker-compose -f docker-compose.prod.yml logs -f api
```

### 컨테이너 재시작
```bash
# 전체 재시작
docker-compose -f docker-compose.prod.yml restart

# 특정 서비스 재시작
docker-compose -f docker-compose.prod.yml restart api
```

### 업데이트
```bash
# 최신 이미지 가져오기
docker-compose -f docker-compose.prod.yml pull

# 컨테이너 재생성
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

### 중지 및 삭제
```bash
# 서비스 중지
docker-compose -f docker-compose.prod.yml stop

# 컨테이너 삭제 (데이터 유지)
docker-compose -f docker-compose.prod.yml down

# 모든 데이터 삭제 (주의!)
docker-compose -f docker-compose.prod.yml down -v
```

---

## 보안 체크리스트

- [ ] `.env` 파일 권한이 600으로 설정됨
- [ ] `DJANGO_SECRET_KEY`가 강력한 랜덤 문자열로 설정됨
- [ ] `PG_PASSWORD`가 강력한 비밀번호로 설정됨
- [ ] `ALLOWED_HOSTS`가 실제 도메인으로 설정됨
- [ ] `CORS_ORIGINS`가 실제 프론트엔드 도메인으로 설정됨
- [ ] PostgreSQL 포트가 외부에 노출되지 않음 (또는 방화벽 설정)
- [ ] API 키가 `.env` 파일에만 저장되고 Git에 커밋되지 않음

---

## 추가 리소스

- [Django 보안 설정](https://docs.djangoproject.com/en/5.0/topics/security/)
- [Docker 보안 가이드](https://docs.docker.com/engine/security/)
- [PostgreSQL 보안](https://www.postgresql.org/docs/current/security.html)

---

## 문의

문제가 지속되면 GitHub Issues에 다음 정보와 함께 문의해주세요:
- OS 및 버전
- Docker 버전
- 에러 로그 (`docker-compose logs api`)
- `.env` 파일 설정 (민감한 정보는 제외)
