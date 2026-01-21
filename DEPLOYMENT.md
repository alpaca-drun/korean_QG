# 새 서버 배포 가이드

## 📋 개요

이 가이드는 새로운 서버에서 프로젝트를 처음부터 설치하는 방법을 설명합니다.

## 🔧 사전 요구사항

새 서버에 다음이 설치되어 있어야 합니다:

- Docker (20.10 이상)
- Docker Compose (1.29 이상)
- Git

### Docker 설치 (Ubuntu 기준)

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인하거나
newgrp docker

# Docker Compose 설치 (최신 버전)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🚀 배포 절차

### 1단계: 코드 가져오기

```bash
# 저장소 클론
git clone <your-repository-url>
cd dev_dong

# 또는 특정 브랜치
git clone -b main <your-repository-url>
cd dev_dong
```

### 2단계: 환경 변수 설정

`.env` 파일을 생성합니다:

```bash
cat > .env << 'EOF'
# ===========================
# Database Configuration
# ===========================
DB_ROOT_PASSWORD=rootpassword
DB_DATABASE=KG_db
DB_USER=curriculum_user
DB_PASSWORD=curriculum_password
DB_PORT=8001

# ===========================
# Application Configuration
# ===========================
APP_PORT=8000
DEBUG=True

# ===========================
# LLM API Configuration
# ===========================
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEYS=key1,key2,key3
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_LLM_PROVIDER=gemini

# ===========================
# JWT Configuration
# ===========================
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
EOF
```

**⚠️ 중요: 실제 API 키와 비밀키로 변경하세요!**

### 3단계: 디렉토리 구조 확인

```bash
# 필요한 디렉토리가 자동으로 생성되지만, 미리 확인
ls -la docker/mariadb/init/  # 초기화 스크립트 확인
```

다음 파일들이 있어야 합니다:
- `docker/mariadb/init/00-init-db.sql` - 기본 설정
- `docker/mariadb/init/01-schema.sql` - 테이블 스키마

### 4단계: 서비스 시작

```bash
# 모든 서비스 시작 (DB + 앱)
scripts/docker-all-up.sh
```

실행 과정:
1. MariaDB 컨테이너 시작
2. 초기화 스크립트 실행 (최초 1회)
   - `00-init-db.sql` → 기본 설정
   - `01-schema.sql` → 테이블 생성
3. DB가 healthy 상태가 될 때까지 대기
4. FastAPI 앱 시작

### 5단계: 확인

```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker-compose logs -f app
docker-compose -f docker-compose.db.yml logs -f mariadb

# 테이블 생성 확인
docker exec KG_db sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;"'

# API 테스트
curl http://localhost:8000/docs
```

## ✅ 성공 확인

다음이 정상적으로 동작하면 성공입니다:

- ✅ 컨테이너 2개 실행 중 (KG_db, KG_app)
- ✅ http://localhost:8000/docs 접속 가능
- ✅ 데이터베이스에 테이블 생성됨

```bash
# 예상 출력
NAMES        STATUS
KG_app       Up XX seconds (healthy)
KG_db        Up XX seconds (healthy)
```

## 🎯 서비스 접속 정보

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Base URL**: http://localhost:8000
- **MariaDB**: localhost:8001

## 🔧 문제 해결

### 포트 충돌

다른 서비스가 8000 또는 8001 포트를 사용 중인 경우:

```bash
# .env 파일에서 포트 변경
APP_PORT=8080
DB_PORT=8002
```

### 권한 문제

```bash
# 스크립트 실행 권한 부여
chmod +x scripts/*.sh
```

### 네트워크 오류

```bash
# 네트워크 수동 생성
docker network create dev_dong_network
```

### 컨테이너 재시작

```bash
# 전체 재시작
scripts/docker-all-down.sh
scripts/docker-all-up.sh
```

## 🗄️ 데이터베이스 관리

### 백업

```bash
# DB 백업
docker exec KG_db sh -c 'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 복원

```bash
# 백업에서 복원
docker exec -i KG_db sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' < backup_20240121_120000.sql
```

### 완전 초기화 (주의: 모든 데이터 삭제)

```bash
docker-compose -f docker-compose.db.yml down -v
scripts/docker-db-up.sh
```

## 📝 프로덕션 배포 시 추가 고려사항

### 1. 보안 설정

```bash
# .env 파일에서 강력한 비밀번호 사용
DB_ROOT_PASSWORD=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 64)

# DEBUG 모드 끄기
DEBUG=False
```

### 2. HTTPS 설정

Nginx 또는 Traefik을 사용하여 리버스 프록시 설정 권장

### 3. 방화벽 설정

```bash
# UFW 사용 예시
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp  # DB 외부 접근이 필요한 경우만
```

### 4. 로그 로테이션

Docker 로그가 너무 커지지 않도록 설정

### 5. 자동 재시작

`restart: unless-stopped` 정책이 docker-compose.yml에 설정되어 있어
시스템 재부팅 시 자동으로 시작됩니다.

## 🔄 업데이트 절차

새 버전 배포 시:

```bash
# 최신 코드 가져오기
git pull origin main

# 앱만 재시작 (DB는 유지)
docker-compose build app
docker-compose up -d app

# 또는 전체 재시작
scripts/docker-all-down.sh
scripts/docker-all-up.sh
```

## 📚 추가 문서

- [Docker 관리 가이드](DOCKER_GUIDE.md)
- [MariaDB 설정](docker/mariadb/README.md)
- [초기화 스크립트](docker/mariadb/init/README.md)

## 💡 팁

- DB는 계속 실행하고 앱만 재시작: `docker-compose restart app`
- 로그 실시간 확인: `docker-compose logs -f app`
- 컨테이너 내부 접근: `docker exec -it KG_app bash`
- DB 접속: `docker exec -it KG_db mysql -u curriculum_user -p`


