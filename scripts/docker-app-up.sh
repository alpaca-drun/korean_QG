#!/bin/bash

# FastAPI 앱 컨테이너 시작

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🚀 FastAPI 앱 컨테이너 시작"
echo "=========================================="
echo ""

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo "   .env.example을 참고하여 .env 파일을 생성하세요."
    echo ""
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 네트워크 확인 및 생성
if ! docker network inspect dev_dong_network >/dev/null 2>&1; then
    echo "⚠️  네트워크가 없습니다. DB를 먼저 시작해주세요."
    echo "   scripts/docker-db-up.sh를 실행하세요."
    exit 1
fi

# App 컨테이너 시작
echo "📦 컨테이너 빌드 및 시작..."
docker-compose up --build -d

echo ""
echo "=========================================="
echo "✅ FastAPI 앱이 시작되었습니다!"
echo "=========================================="
echo ""
echo "🌐 FastAPI 서버: http://localhost:8000"
echo "📚 Swagger UI: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo ""
echo "📊 로그 확인: docker-compose logs -f app"
echo "🛑 중지: docker-compose down"
echo "🔄 재시작: docker-compose restart app"
echo ""

