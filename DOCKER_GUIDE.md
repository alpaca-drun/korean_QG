# Docker 컨테이너 관리 가이드

## 📋 개요

DB(MariaDB)와 앱(FastAPI)이 별도의 docker-compose 파일로 분리되어 있습니다.
이를 통해 DB와 앱을 독립적으로 관리할 수 있습니다.

## 📁 파일 구조

```
docker-compose.yml        # FastAPI 앱 전용
docker-compose.db.yml     # MariaDB 전용
scripts/
  ├── docker-all-up.sh    # DB + 앱 모두 시작
  ├── docker-all-down.sh  # DB + 앱 모두 중지
  ├── docker-db-up.sh     # DB만 시작
  ├── docker-app-up.sh    # 앱만 시작
  └── docker-up.sh        # 기존 스크립트 (legacy)
```

## 🚀 사용 방법

### 1️⃣ 모든 서비스 시작 (DB + 앱)

```bash
scripts/docker-all-up.sh
```

### 2️⃣ DB만 시작

```bash
scripts/docker-db-up.sh

# 또는
docker-compose -f docker-compose.db.yml up -d
```

### 3️⃣ 앱만 시작 (DB가 이미 실행 중일 때)

```bash
scripts/docker-app-up.sh

# 또는
docker-compose up -d
```

### 4️⃣ 모든 서비스 중지

```bash
scripts/docker-all-down.sh
```

### 5️⃣ 앱만 중지 (DB는 계속 실행)

```bash
docker-compose down
```

### 6️⃣ DB만 중지 (앱은 계속 실행)

```bash
docker-compose -f docker-compose.db.yml down
```

## 📊 로그 확인

### 앱 로그

```bash
docker-compose logs -f app
```

### DB 로그

```bash
docker-compose -f docker-compose.db.yml logs -f mariadb
```

### 모든 로그

```bash
docker-compose logs -f app & docker-compose -f docker-compose.db.yml logs -f mariadb
```

## 🔄 재시작

### 앱만 재시작

```bash
docker-compose restart app
```

### DB만 재시작

```bash
docker-compose -f docker-compose.db.yml restart mariadb
```

## 🗄️ 데이터 관리

### 데이터 백업 위치

- DB 데이터: `./docker/mariadb/data/`
- 백업 파일: `./docker/mariadb/backups/`

### 데이터 완전 삭제 (주의!)

```bash
# 컨테이너와 볼륨 모두 삭제
docker-compose -f docker-compose.db.yml down -v

# 데이터 폴더 직접 삭제
rm -rf ./docker/mariadb/data/
```

## 🌐 접속 정보

- **FastAPI 서버**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **MariaDB**: localhost:8001

## 🔧 문제 해결

### 네트워크 오류 발생 시

```bash
# 네트워크 수동 생성
docker network create dev_dong_network

# 다시 시작
scripts/docker-all-up.sh
```

### 컨테이너 이름 충돌 시

```bash
# 기존 컨테이너 강제 제거
docker rm -f KG_db KG_app

# 다시 시작
scripts/docker-all-up.sh
```

### 포트 충돌 시

`.env` 파일에서 포트 변경:

```bash
APP_PORT=8080  # 앱 포트
DB_PORT=8002   # DB 포트
```

## 💡 팁

### DB는 계속 실행, 앱만 재시작

코드 수정 후 앱만 재시작하고 싶을 때:

```bash
docker-compose restart app
```

### 로컬에서 앱 실행 (DB만 Docker)

```bash
# DB만 시작
scripts/docker-db-up.sh

# 로컬에서 앱 실행
uvicorn app.main:app --reload
```

### 외부 DB 사용

`.env` 파일에서 DB 호스트 변경:

```bash
DB_HOST=192.168.1.100  # 외부 DB 주소
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_DATABASE=your_database
```

그리고 앱만 실행:

```bash
docker-compose up -d
```

## 🎯 권장 워크플로우

### 개발 시작

```bash
scripts/docker-all-up.sh
```

### 코드 수정 중

- Hot reload가 활성화되어 있어 코드 변경 시 자동 재시작됨
- 필요시 `docker-compose restart app`으로 수동 재시작

### 개발 종료

```bash
# 앱만 중지 (DB는 유지)
docker-compose down

# 또는 모두 중지
scripts/docker-all-down.sh
```

### DB 스키마 변경

```bash
# DB 재시작
docker-compose -f docker-compose.db.yml restart mariadb

# 또는 완전히 초기화 (주의: 데이터 손실!)
docker-compose -f docker-compose.db.yml down -v
scripts/docker-db-up.sh
```
