#!/bin/bash

# 의존성 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. 먼저 ./scripts/setup.sh를 실행하세요."
    exit 1
fi

# 가상환경 활성화
source venv/bin/activate

echo "=========================================="
echo "의존성 설치 중..."
echo "=========================================="

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt

echo ""
echo "✅ 의존성 설치가 완료되었습니다!"

