# Backend Dockerfile for Real Estate for the Young
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 (context가 프로젝트 루트이므로)
COPY requirements.txt /app/requirements.txt

# Python 의존성 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일들 복사
COPY backend/ /app/backend/
COPY setup.py /app/
COPY pyproject.toml /app/

# data와 logs 디렉토리 생성
RUN mkdir -p /app/data /app/logs

# 포트 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# FastAPI 서버 실행 (uvicorn 사용)
CMD ["uvicorn", "backend.services.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
