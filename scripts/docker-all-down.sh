#!/bin/bash

# DB와 앱을 모두 중지

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🛑 모든 컨테이너를 중지합니다"
echo "=========================================="
echo ""

# App 먼저 중지
echo "1️⃣  FastAPI 앱 중지 중..."
docker-compose down

echo ""
echo "2️⃣  MariaDB 중지 중..."
docker-compose -f docker-compose.db.yml down

echo ""
echo "=========================================="
echo "✅ 모든 서비스가 중지되었습니다!"
echo "=========================================="
echo ""

