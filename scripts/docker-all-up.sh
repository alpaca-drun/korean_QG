#!/bin/bash

# DB와 앱을 모두 시작

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🐳 DB와 앱을 모두 시작합니다"
echo "=========================================="
echo ""

# DB 먼저 시작
echo "1️⃣  MariaDB 시작 중..."
docker-compose -f docker-compose.db.yml up -d

echo ""
echo "⏳ DB가 healthy 상태가 될 때까지 대기 중..."
sleep 5

# DB health check
for i in {1..30}; do
    if docker exec KG_db healthcheck.sh --connect --innodb_initialized >/dev/null 2>&1; then
        echo "✅ DB가 준비되었습니다!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  DB health check 타임아웃. 계속 진행합니다..."
    fi
    sleep 2
done

echo ""
echo "2️⃣  FastAPI 앱 시작 중..."
docker-compose up --build -d

echo ""
echo "=========================================="
echo "✅ 모든 서비스가 시작되었습니다!"
echo "=========================================="
echo ""
echo "🗄️  MariaDB: localhost:8001"
echo "🌐 FastAPI 서버: http://localhost:8000"
echo "📚 Swagger UI: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo ""
echo "📊 로그 확인:"
echo "   - DB: docker-compose -f docker-compose.db.yml logs -f mariadb"
echo "   - App: docker-compose logs -f app"
echo ""
echo "🛑 중지:"
echo "   - 모두: scripts/docker-all-down.sh"
echo "   - DB만: docker-compose -f docker-compose.db.yml down"
echo "   - App만: docker-compose down"
echo ""

