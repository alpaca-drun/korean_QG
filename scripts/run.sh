#!/bin/bash

# 교육과정 관리 API 개발 모드 실행 스크립트

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

# 환경 변수 로드 (있는 경우)
if [ -f ".env" ]; then
    # 주석, 빈 줄, 특수 문자를 안전하게 처리
    set -a
    # 주석 제거, 빈 줄 제거, 줄 끝 주석 제거, 값 trim 후 export
    while IFS= read -r line || [ -n "$line" ]; do
        # 빈 줄 건너뛰기
        [[ -z "${line// /}" ]] && continue
        # 주석 줄 건너뛰기
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        # 줄 끝 주석 제거
        clean_line="${line%%#*}"
        # KEY=VALUE 형식인지 확인
        if [[ "$clean_line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]// /}"  # 키에서 공백 제거
            value="${BASH_REMATCH[2]}"     # 값
            # 값의 앞뒤 공백 제거 (trim)
            value="${value#"${value%%[![:space:]]*}"}"  # 앞 공백 제거
            value="${value%"${value##*[![:space:]]}"}"  # 뒤 공백 제거
            export "${key}=${value}"
        fi
    done < .env
    set +a
fi

# 기본값 설정
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8003}

echo "=========================================="
echo "교육과정 관리 API 개발 서버 시작"
echo "=========================================="
echo "서버 주소: http://$HOST:$PORT"
echo "Swagger UI: http://$HOST:$PORT/docs"
echo "ReDoc: http://$HOST:$PORT/redoc"
echo ""
echo "서버를 중지하려면 Ctrl+C를 누르세요"
echo "=========================================="
echo ""

# 개발 모드로 실행 (--reload 옵션 사용, docker 디렉토리 제외)
uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --reload-exclude "docker/*" \
    --reload-exclude "*.sql" \
    --reload-exclude "*.sql.gz" \
    --reload-exclude "venv/*" \
    --reload-exclude "__pycache__/*"

