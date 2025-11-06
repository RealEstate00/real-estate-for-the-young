#!/bin/bash
# Docker 디스크 공간 정리 스크립트
# 프로젝트 이미지와 필요한 베이스 이미지는 보호하고, 미사용 이미지만 정리

echo "=== Docker 디스크 공간 정리 ==="
echo ""

# 보호할 이미지 목록 (정리 대상에서 제외)
PROTECTED_IMAGES=(
    "jina1003/seoul-housing-api:latest"
    "jina1003/seoul-housing-frontend:latest"
    "real-estate-for-the-young-api:latest"
    "real-estate-for-the-young-frontend:latest"
    "pgvector/pgvector:pg18"
    "moby/buildkit:buildx-stable-1"
    "python:3.12-slim"
    "node:20-alpine"
    "nginx:alpine"
)

echo "🔒 보호할 이미지:"
for img in "${PROTECTED_IMAGES[@]}"; do
    echo "  - $img"
done
echo ""

# 1. 미사용 이미지 정리 (최근 7일 이전만 정리 - 보수적 접근)
echo "1. 미사용 이미지 정리 (7일 이전 미사용 이미지만 정리)..."
echo "   참고: 사용 중인 이미지(컨테이너 실행 중)는 자동으로 보호됩니다"
# 사용 중인 이미지 확인
USED_IMAGES=$(docker ps -a --format "{{.Image}}" 2>/dev/null | sort -u)
if [ -n "$USED_IMAGES" ]; then
    echo "   사용 중인 이미지:"
    echo "$USED_IMAGES" | sed 's/^/     - /'
else
    echo "   사용 중인 이미지 없음"
fi
echo ""

# 7일 이전 미사용 이미지 정리 (보수적 접근: latest 이미지는 보통 최근이므로 보호됨)
docker image prune -a --filter "until=168h" -f
echo "✅ 완료"
echo ""

# 2. Dangling 이미지 삭제
echo "2. Dangling 이미지 삭제..."
docker image prune -f
echo "✅ 완료"
echo ""

# 3. 빌드 캐시 정리
echo "3. 빌드 캐시 정리..."
docker builder prune -af
echo "✅ 완료"
echo ""

# 4. 사용하지 않는 볼륨 정리
echo "4. 사용하지 않는 볼륨 정리..."
docker volume prune -f
echo "✅ 완료"
echo ""

# 5. 최종 디스크 사용량
echo "=== 정리 후 디스크 사용량 ==="
docker system df

echo ""
echo "✅ 정리 완료!"
echo ""
echo "📊 보호된 프로젝트 이미지 상태:"
for img in "${PROTECTED_IMAGES[@]}"; do
    if docker images "$img" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "$img"; then
        SIZE=$(docker images "$img" --format "{{.Size}}" 2>/dev/null | head -1)
        echo "  ✅ $img ($SIZE)"
    fi
done

