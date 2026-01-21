# MariaDB Docker 설정

이 디렉토리는 Docker Compose를 사용한 MariaDB 설정을 관리합니다.

## 디렉토리 구조

- `data/`: MariaDB 데이터 파일 저장 (Git 제외)
- `backups/`: 데이터베이스 백업 파일 저장 (Git 제외)
- `init/`: 초기화 SQL 스크립트 (컨테이너 최초 실행 시 자동 실행)
- `conf.d/`: MariaDB 설정 파일 (my.cnf 등)

## 사용 방법

### 1. 환경 변수 설정

`.env` 파일에 다음 변수들을 설정하세요:

```env
DB_ROOT_PASSWORD=rootpassword
DB_DATABASE=curriculum_db
DB_USER=curriculum_user
DB_PASSWORD=curriculum_password
DB_PORT=3306
```

또는 `docker-compose.yml`의 기본값을 사용할 수 있습니다.

### 2. MariaDB 시작

```bash
docker-compose up -d mariadb
```

### 3. MariaDB 중지

```bash
docker-compose down
```

### 4. 데이터 백업

```bash
# 백업 실행
docker-compose exec mariadb mysqldump -u root -p${DB_ROOT_PASSWORD} ${DB_DATABASE} > docker/mariadb/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# 또는 백업 스크립트 사용 (scripts/backup_db.sh)
```

### 5. 데이터 복원

```bash
# 백업 파일로 복원
docker-compose exec -T mariadb mysql -u root -p${DB_ROOT_PASSWORD} ${DB_DATABASE} < docker/mariadb/backups/backup_YYYYMMDD_HHMMSS.sql
```

### 6. 로그 확인

```bash
docker-compose logs -f mariadb
```

## 초기화 스크립트

`init/` 디렉토리에 `.sql` 파일을 넣으면 컨테이너 최초 실행 시 자동으로 실행됩니다.
이미 데이터가 있는 경우에는 실행되지 않습니다.

## 주의사항

- `data/`와 `backups/` 디렉토리는 Git에 포함되지 않습니다.
- 데이터를 완전히 삭제하려면 `docker-compose down -v`를 사용하세요 (주의: 모든 데이터가 삭제됩니다).










