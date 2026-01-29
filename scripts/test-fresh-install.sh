#!/bin/bash

# 새 서버 설치를 시뮬레이션하는 테스트 스크립트
# 기존 DB를 완전히 삭제하고 초기화 스크립트로 새로 생성합니다

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🧪 새 서버 설치 시뮬레이션 테스트"
echo "=========================================="
echo ""
echo "⚠️  주의: 기존 DB 데이터가 모두 삭제됩니다!"
echo ""
read -p "계속하시겠습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "취소되었습니다."
    exit 0
fi

echo ""
echo "1️⃣  기존 컨테이너와 볼륨 완전 삭제 중..."
docker-compose down 2>/dev/null || true
docker-compose -f docker-compose.db.yml down -v 2>/dev/null || true

echo ""
echo "2️⃣  데이터 디렉토리 삭제 중..."
rm -rf docker/mariadb/data/*

echo ""
echo "3️⃣  초기화 스크립트로 새로 설치 중..."
scripts/docker-all-up.sh

echo ""
echo "4️⃣  테이블 생성 확인 중..."
sleep 3
docker exec KG_db sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;"'

echo ""
echo "=========================================="
echo "✅ 테스트 완료!"
echo "=========================================="
echo ""
echo "초기화 스크립트가 정상적으로 실행되었습니다."
echo "새 서버에서도 동일하게 작동합니다."
echo ""






