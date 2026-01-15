#!/bin/bash

# 프로덕션 환경 배포 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🚀 프로덕션 환경 배포"
echo "=========================================="
echo ""

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다."
    exit 1
fi

# JWT_SECRET_KEY 확인
if grep -q "your-secret-key-change-this-in-production" .env; then
    echo "⚠️  경고: JWT_SECRET_KEY가 기본값입니다!"
    echo "   프로덕션에서는 반드시 강력한 키로 변경하세요."
    echo ""
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 프로덕션 이미지 빌드 및 배포..."
docker-compose -f docker-compose.prod.yml up --build -d

echo ""
echo "=========================================="
echo "✅ 프로덕션 환경이 시작되었습니다!"
echo "=========================================="
echo ""
echo "🌐 FastAPI 서버: http://localhost:${APP_PORT:-8000}"
echo ""
echo "📊 로그 확인: docker-compose -f docker-compose.prod.yml logs -f"
echo "🛑 중지: docker-compose -f docker-compose.prod.yml down"
echo ""

