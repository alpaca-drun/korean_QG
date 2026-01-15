#!/bin/bash

# API 테스트 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 기본값 설정
BASE_URL=${BASE_URL:-http://localhost:8000}

echo "=========================================="
echo "API 테스트 시작"
echo "=========================================="
echo "서버 주소: $BASE_URL"
echo ""

# 헬스 체크
echo "1. 헬스 체크 테스트..."
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health" || echo "")
if [ -z "$HEALTH_RESPONSE" ]; then
    echo "❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."
    exit 1
fi
echo "✅ 헬스 체크 성공: $HEALTH_RESPONSE"
echo ""

# 대단원 리스트 조회
echo "2. 대단원 리스트 조회 테스트..."
LARGE_UNITS_RESPONSE=$(curl -s "$BASE_URL/api/v1/large-units")
echo "✅ 대단원 리스트:"
echo "$LARGE_UNITS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LARGE_UNITS_RESPONSE"
echo ""

# 소단원 리스트 조회 (대단원 ID 1 사용)
echo "3. 소단원 리스트 조회 테스트 (large_unit_id=1)..."
SMALL_UNITS_RESPONSE=$(curl -s "$BASE_URL/api/v1/small-units?large_unit_id=1")
echo "✅ 소단원 리스트:"
echo "$SMALL_UNITS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SMALL_UNITS_RESPONSE"
echo ""

# 성취기준 리스트 조회 (소단원 ID 1 사용)
echo "4. 성취기준 리스트 조회 테스트 (small_unit_id=1)..."
ACHIEVEMENT_RESPONSE=$(curl -s "$BASE_URL/api/v1/achievement-standards?small_unit_id=1")
echo "✅ 성취기준 리스트:"
echo "$ACHIEVEMENT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ACHIEVEMENT_RESPONSE"
echo ""

# 지문 리스트 조회 (성취기준 ID 1 사용)
echo "5. 지문 리스트 조회 테스트 (achievement_standard_id=1)..."
PASSAGES_RESPONSE=$(curl -s "$BASE_URL/api/v1/passages?achievement_standard_id=1")
echo "✅ 지문 리스트:"
echo "$PASSAGES_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PASSAGES_RESPONSE"
echo ""

echo "=========================================="
echo "✅ 모든 테스트가 완료되었습니다!"
echo "=========================================="

