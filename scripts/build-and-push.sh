#!/bin/bash
# Docker 이미지 빌드 및 Docker Hub 푸시 스크립트 (멀티플랫폼 지원)
# AMD64(윈도우/리눅스)와 ARM64(Mac M1/M2) 모두 지원

set -e  # 오류 발생 시 중단

echo "=== Docker 멀티플랫폼 이미지 빌드 및 푸시 ==="
echo ""

# Docker Hub 로그인 확인
if ! docker info | grep -q "Username"; then
    echo "🔐 Docker Hub 로그인이 필요합니다."
    docker login
fi

# Docker Buildx 설치 확인
if ! docker buildx version >/dev/null 2>&1; then
    echo "❌ Docker Buildx가 설치되어 있지 않습니다."
    echo ""
    echo "📦 Buildx 설치 방법:"
    echo ""
    echo "1. Docker Desktop 사용 시:"
    echo "   - Docker Desktop > Settings > Features in development"
    echo "   - 'Use containerd for pulling and storing images' 활성화 (선택)"
    echo "   - 또는 Docker Desktop 재시작"
    echo ""
    echo "2. Homebrew로 설치 (Mac):"
    echo "   brew install docker-buildx"
    echo ""
    echo "3. 수동 설치:"
    echo "   mkdir -p ~/.docker/cli-plugins"
    echo "   curl -L https://github.com/docker/buildx/releases/latest/download/buildx-v$(curl -s https://api.github.com/repos/docker/buildx/releases/latest | grep tag_name | cut -d '\"' -f 4 | cut -d 'v' -f 2).darwin-$(uname -m) -o ~/.docker/cli-plugins/docker-buildx"
    echo "   chmod +x ~/.docker/cli-plugins/docker-buildx"
    echo ""
    echo "4. 또는 Docker Desktop 설치 (권장):"
    echo "   brew install --cask docker"
    echo ""
    exit 1
fi

echo "✅ Docker Buildx 확인 완료: $(docker buildx version | head -1)"
echo ""

# Docker Buildx 빌더 확인 및 설정
if ! docker buildx ls 2>/dev/null | grep -q "multiarch"; then
    echo "🔧 Buildx 빌더 생성 중..."
    docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch 2>/dev/null || true
    docker buildx inspect --bootstrap
fi

# 서비스 선택 (인자로 전달: backend, frontend, 또는 모두)
SERVICE="${1:-all}"  # 기본값: all (모두 빌드)

echo "📦 멀티플랫폼 이미지 빌드 중..."
echo "지원 플랫폼: linux/amd64 (윈도우/리눅스), linux/arm64 (Mac M1/M2)"
echo "빌드 대상: $SERVICE"
echo ""

# 백엔드 빌드 및 푸시
if [ "$SERVICE" = "backend" ] || [ "$SERVICE" = "all" ]; then
    echo "1. 백엔드 이미지 멀티플랫폼 빌드 (jina1003/seoul-housing-api:latest)..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --tag jina1003/seoul-housing-api:latest \
        --file Dockerfile.backend \
        --push \
        .
    echo "✅ 백엔드 이미지 빌드 및 푸시 완료"
    echo ""
fi

# 프론트엔드 빌드 및 푸시
if [ "$SERVICE" = "frontend" ] || [ "$SERVICE" = "all" ]; then
    echo "2. 프론트엔드 이미지 멀티플랫폼 빌드 (jina1003/seoul-housing-frontend:latest)..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --tag jina1003/seoul-housing-frontend:latest \
        --file Dockerfile.frontend \
        --push \
        .
    echo "✅ 프론트엔드 이미지 빌드 및 푸시 완료"
    echo ""
fi

echo "✅ 모든 작업 완료!"
echo ""
echo "이제 모든 플랫폼(윈도우, Mac Intel, Mac M1/M2, 리눅스)에서 이미지를 받을 수 있습니다:"
echo "  docker-compose -f docker-compose.prod.yml pull"
echo "  docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "💡 참고: docker-compose.prod.yml은 멀티플랫폼 이미지를 자동으로 선택합니다."
echo "   - Windows/Intel Mac: linux/amd64 이미지 사용"
echo "   - Mac M1/M2: linux/arm64 이미지 사용 (네이티브 성능)"
echo ""
echo "📝 사용법:"
echo "  ./scripts/build-and-push.sh          # 백엔드 + 프론트엔드 모두 빌드"
echo "  ./scripts/build-and-push.sh backend  # 백엔드만 빌드"
echo "  ./scripts/build-and-push.sh frontend # 프론트엔드만 빌드"

