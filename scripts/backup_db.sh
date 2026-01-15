#!/bin/bash

# MariaDB 백업 스크립트
# 사용법: ./scripts/backup_db.sh

set -e

# 환경 변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 기본값 설정
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD:-rootpassword}
DB_DATABASE=${DB_DATABASE:-curriculum_db}
CONTAINER_NAME=${CONTAINER_NAME:-KG_db}
BACKUP_DIR="./docker/mariadb/backups"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

# 백업 파일명 생성 (날짜/시간 포함)
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

echo "백업 시작: $BACKUP_FILE"

# 백업 실행
docker-compose exec -T mariadb mysqldump \
    -u root \
    -p"$DB_ROOT_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    "$DB_DATABASE" > "$BACKUP_FILE"

# 백업 파일 압축 (선택사항)
if command -v gzip &> /dev/null; then
    echo "백업 파일 압축 중..."
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
fi

# 오래된 백업 파일 삭제 (30일 이상 된 파일)
if [ -d "$BACKUP_DIR" ]; then
    find "$BACKUP_DIR" -name "backup_*.sql*" -type f -mtime +30 -delete
    echo "30일 이상 된 백업 파일 삭제 완료"
fi

echo "백업 완료: $BACKUP_FILE"
echo "백업 크기: $(du -h "$BACKUP_FILE" | cut -f1)"

