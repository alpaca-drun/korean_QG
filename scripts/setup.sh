#!/bin/bash

# 교육과정 관리 API 초기 설정 스크립트
# 가상환경 생성 및 의존성 설치

set -e

echo "=========================================="
echo "교육과정 관리 API 초기 설정을 시작합니다"
echo "=========================================="

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "프로젝트 루트: $PROJECT_ROOT"

# Python 버전 확인
echo ""
echo "Python 버전 확인 중..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"

# 가상환경 생성
echo ""
echo "가상환경 생성 중..."
if [ -d "venv" ]; then
    echo "⚠️  가상환경이 이미 존재합니다. 기존 가상환경을 사용합니다."
else
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
fi

# 가상환경 활성화
echo ""
echo "가상환경 활성화 중..."
source venv/bin/activate

# pip 업그레이드
echo ""
echo "pip 업그레이드 중..."
pip install --upgrade pip

# 의존성 설치
echo ""
echo "의존성 설치 중..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✅ 초기 설정이 완료되었습니다!"
echo "=========================================="
echo ""
echo "다음 명령어로 서버를 실행할 수 있습니다:"
echo "  ./scripts/run.sh          # 개발 모드"
echo "  ./scripts/run_prod.sh     # 프로덕션 모드"
echo ""
echo "가상환경 활성화:"
echo "  source venv/bin/activate"
echo ""

