#!/bin/bash
# Docker 디스크 공간 정리 스크립트

echo "=== Docker 디스크 공간 정리 ==="
echo ""

# 1. 중복/미사용 이미지 정리
echo "1. 중복/미사용 이미지 정리..."
docker image prune -a --filter "until=24h" -f
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

