#!/bin/bash

# MariaDB 복원 스크립트
# 사용법: ./scripts/restore_db.sh <백업파일경로>

set -e

if [ -z "$1" ]; then
    echo "사용법: $0 <백업파일경로>"
    echo "예시: $0 docker/mariadb/backups/backup_20240101_120000.sql"
    exit 1
fi

BACKUP_FILE="$1"

# 백업 파일 존재 확인
if [ ! -f "$BACKUP_FILE" ]; then
    echo "오류: 백업 파일을 찾을 수 없습니다: $BACKUP_FILE"
    exit 1
fi

# 환경 변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 기본값 설정
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD:-rootpassword}
DB_DATABASE=${DB_DATABASE:-curriculum_db}

echo "경고: 이 작업은 현재 데이터베이스의 모든 데이터를 덮어씁니다!"
read -p "계속하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "복원이 취소되었습니다."
    exit 0
fi

echo "복원 시작: $BACKUP_FILE"

# gzip 압축 파일인지 확인
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "압축 해제 중..."
    gunzip -c "$BACKUP_FILE" | docker-compose exec -T mariadb mysql -u root -p"$DB_ROOT_PASSWORD" "$DB_DATABASE"
else
    docker-compose exec -T mariadb mysql -u root -p"$DB_ROOT_PASSWORD" "$DB_DATABASE" < "$BACKUP_FILE"
fi

echo "복원 완료!"

