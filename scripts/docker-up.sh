#!/bin/bash

# Docker Compose로 개발 환경 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🐳 Docker Compose로 개발 환경 시작"
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

# Docker Compose 실행
echo "📦 컨테이너 빌드 및 시작..."
docker-compose up --build -d

echo ""
echo "=========================================="
echo "✅ 개발 환경이 시작되었습니다!"
echo "=========================================="
echo ""
echo "🌐 FastAPI 서버: http://localhost:8000"
echo "📚 Swagger UI: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo ""
echo "🗄️  MariaDB: localhost:8001"
echo ""
echo "📊 로그 확인: docker-compose logs -f app"
echo "🛑 중지: docker-compose down"
echo "🔄 재시작: docker-compose restart app"
echo ""

