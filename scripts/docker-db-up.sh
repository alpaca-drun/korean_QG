#!/bin/bash

# MariaDB 컨테이너 시작

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🗄️  MariaDB 컨테이너 시작"
echo "=========================================="
echo ""

# DB 컨테이너 시작
docker-compose -f docker-compose.db.yml up -d

echo ""
echo "=========================================="
echo "✅ MariaDB가 시작되었습니다!"
echo "=========================================="
echo ""
echo "🗄️  MariaDB: localhost:8001"
echo ""
echo "📊 로그 확인: docker-compose -f docker-compose.db.yml logs -f mariadb"
echo "🛑 중지: docker-compose -f docker-compose.db.yml down"
echo "🔄 재시작: docker-compose -f docker-compose.db.yml restart mariadb"
echo ""

