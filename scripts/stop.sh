#!/bin/bash

# 서버 중지 스크립트

set -e

PORT=${PORT:-8000}

echo "포트 $PORT에서 실행 중인 서버를 찾는 중..."

# 해당 포트에서 실행 중인 프로세스 찾기
PID=$(lsof -ti:$PORT 2>/dev/null || echo "")

if [ -z "$PID" ]; then
    echo "❌ 포트 $PORT에서 실행 중인 서버를 찾을 수 없습니다."
    exit 1
fi

echo "프로세스 ID: $PID"
echo "서버를 중지합니다..."

# 프로세스 종료
kill -TERM $PID

# 종료 대기
sleep 2

# 여전히 실행 중이면 강제 종료
if ps -p $PID > /dev/null 2>&1; then
    echo "강제 종료 중..."
    kill -KILL $PID
fi

echo "✅ 서버가 중지되었습니다."

