#!/bin/bash
# Docker 이미지 빌드 및 Docker Hub 푸시 스크립트

set -e  # 오류 발생 시 중단

echo "=== Docker 이미지 빌드 및 푸시 ==="
echo ""

# Docker Hub 로그인 확인
if ! docker info | grep -q "Username"; then
    echo "🔐 Docker Hub 로그인이 필요합니다."
    docker login
fi

echo "📦 이미지 빌드 중..."
echo ""

# 1. 백엔드 이미지 빌드
echo "1. 백엔드 이미지 빌드 (jina1003/seoul-housing-api:latest)..."
docker build -t jina1003/seoul-housing-api:latest -f Dockerfile.backend .
echo "✅ 백엔드 이미지 빌드 완료"
echo ""

# 2. 프론트엔드 이미지 빌드
echo "2. 프론트엔드 이미지 빌드 (jina1003/seoul-housing-frontend:latest)..."
docker build -t jina1003/seoul-housing-frontend:latest -f Dockerfile.frontend .
echo "✅ 프론트엔드 이미지 빌드 완료"
echo ""

# 3. Docker Hub에 푸시
echo "🚀 Docker Hub에 푸시 중..."
echo ""

echo "3. 백엔드 이미지 푸시..."
docker push jina1003/seoul-housing-api:latest
echo "✅ 백엔드 이미지 푸시 완료"
echo ""

echo "4. 프론트엔드 이미지 푸시..."
docker push jina1003/seoul-housing-frontend:latest
echo "✅ 프론트엔드 이미지 푸시 완료"
echo ""

echo "✅ 모든 작업 완료!"
echo ""
echo "이제 팀원들이 다음 명령어로 이미지를 받을 수 있습니다:"
echo "  docker-compose -f docker-compose.prod.yml pull"
echo "  docker-compose -f docker-compose.prod.yml up -d"

