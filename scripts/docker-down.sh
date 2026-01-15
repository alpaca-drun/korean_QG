#!/bin/bash

# Docker Compose 환경 종료

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🛑 Docker Compose 환경 종료"
echo "=========================================="

docker-compose down

echo ""
echo "✅ 모든 컨테이너가 종료되었습니다."
echo ""

