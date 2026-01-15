# Docker 가이드

이 프로젝트는 Docker와 Docker Compose를 사용하여 개발 및 프로덕션 환경을 쉽게 관리할 수 있습니다.

## 📋 목차

- [사전 요구사항](#사전-요구사항)
- [개발 환경 실행](#개발-환경-실행)
- [프로덕션 환경 실행](#프로덕션-환경-실행)
- [유용한 명령어](#유용한-명령어)
- [문제 해결](#문제-해결)

---

## 🔧 사전 요구사항

### 필수 설치

- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상

### 설치 확인

```bash
docker --version
docker-compose --version
```

### 환경 변수 설정

1. `.env` 파일을 생성합니다:

```bash
cp .env.example .env
```

2. `.env` 파일을 수정하여 필요한 값을 설정합니다 (자세한 내용은 `ENV_SETUP.md` 참고)

---

## 🚀 개발 환경 실행

### 방법 1: 스크립트 사용 (권장)

```bash
# 시작
scripts/docker-up.sh

# 종료
scripts/docker-down.sh
```

### 방법 2: Docker Compose 직접 사용

```bash
# 빌드 및 시작
docker-compose up --build -d

# 종료
docker-compose down
```

### 접속 정보

- **FastAPI 서버**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **MariaDB**: localhost:8001

### 개발 모드 특징

✅ **Hot Reload 활성화** - 코드 변경 시 자동 재시작  
✅ **로컬 코드 마운트** - 실시간 코드 반영  
✅ **디버깅 용이** - 로그 실시간 확인  

---

## 🏭 프로덕션 환경 실행

```bash
# 빌드 및 시작
docker-compose -f docker-compose.prod.yml up --build -d

# 종료
docker-compose -f docker-compose.prod.yml down
```

### 프로덕션 모드 특징

✅ **최적화된 이미지** - 코드 복사, Hot Reload 비활성화  
✅ **보안 강화** - DEBUG 모드 비활성화  
✅ **안정성** - restart: always 설정  

---

## 📝 유용한 명령어

### 로그 확인

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f app
docker-compose logs -f mariadb

# 최근 100줄만 보기
docker-compose logs --tail=100 app
```

### 컨테이너 상태 확인

```bash
# 실행 중인 컨테이너 확인
docker-compose ps

# 상세 정보
docker ps
```

### 컨테이너 재시작

```bash
# 특정 서비스만 재시작
docker-compose restart app

# 전체 재시작
docker-compose restart
```

### 컨테이너 접속

```bash
# FastAPI 앱 컨테이너 접속
docker exec -it KG_app bash

# MariaDB 컨테이너 접속
docker exec -it KG_db bash

# MariaDB 클라이언트 직접 접속
docker exec -it KG_db mysql -u curriculum_user -p
```

### 데이터베이스 백업

```bash
# 백업
docker exec KG_db mysqldump -u curriculum_user -p curriculum_db > backup.sql

# 복원
docker exec -i KG_db mysql -u curriculum_user -p curriculum_db < backup.sql
```

### 이미지 재빌드

```bash
# 캐시 없이 완전히 새로 빌드
docker-compose build --no-cache

# 빌드 후 시작
docker-compose up --build -d
```

### 리소스 정리

```bash
# 중지된 컨테이너 제거
docker-compose down

# 볼륨까지 제거 (주의: 데이터베이스 데이터 삭제됨!)
docker-compose down -v

# 사용하지 않는 이미지 제거
docker image prune -a
```

---

## 🐛 문제 해결

### 1. 포트가 이미 사용 중인 경우

**문제**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**해결**:
```bash
# 사용 중인 프로세스 확인
lsof -i :8000

# 프로세스 종료 또는 .env 파일에서 APP_PORT 변경
```

### 2. 데이터베이스 연결 실패

**문제**: `Can't connect to MySQL server`

**해결**:
```bash
# 데이터베이스 상태 확인
docker-compose logs mariadb

# 헬스체크 확인
docker inspect KG_db | grep -A 10 Health

# 재시작
docker-compose restart mariadb
```

### 3. 코드 변경이 반영되지 않음

**문제**: 코드를 수정했는데 변경사항이 적용되지 않음

**해결**:
```bash
# 개발 모드 확인 (docker-compose.yml 사용 중인지)
docker-compose ps

# 볼륨 마운트 확인
docker inspect KG_app | grep -A 20 Mounts

# 수동 재시작
docker-compose restart app
```

### 4. 권한 문제

**문제**: `Permission denied`

**해결**:
```bash
# storage 디렉토리 권한 확인
ls -la storage/

# 권한 부여
sudo chown -R $USER:$USER storage/
chmod -R 755 storage/
```

### 5. 이미지 빌드 실패

**문제**: 의존성 설치 중 오류

**해결**:
```bash
# requirements.txt 확인
cat requirements.txt

# 캐시 없이 재빌드
docker-compose build --no-cache app

# 로컬에서 테스트
pip install -r requirements.txt
```

---

## 📊 모니터링

### 리소스 사용량 확인

```bash
# 실시간 리소스 사용량
docker stats

# 특정 컨테이너만
docker stats KG_app KG_db
```

### 헬스체크 상태

```bash
# 모든 서비스 헬스체크
docker-compose ps

# 상세 정보
docker inspect KG_app | grep -A 10 Health
docker inspect KG_db | grep -A 10 Health
```

---

## 🔄 업데이트

### 코드 업데이트 후

```bash
# 1. 최신 코드 pull
git pull

# 2. 이미지 재빌드
docker-compose build app

# 3. 재시작
docker-compose up -d app
```

### 의존성 업데이트 후

```bash
# requirements.txt 변경 후
docker-compose build --no-cache app
docker-compose up -d app
```

---

## 💡 팁

### 1. 개발 시 자동 재시작 확인

개발 모드(`docker-compose.yml`)에서는 `app/` 디렉토리 변경 시 자동으로 재시작됩니다.

### 2. 로그 파일 관리

로그가 너무 커지면:
```bash
# 로그 로테이션 설정
docker-compose config | grep logging
```

### 3. 네트워크 문제 해결

```bash
# 네트워크 재생성
docker-compose down
docker network prune
docker-compose up -d
```

---

## 📚 추가 문서

- [환경 변수 설정](ENV_SETUP.md)
- [인증 가이드](AUTH_GUIDE.md)
- [프로젝트 구조](PROJECT_STRUCTURE.md)

---

## ⚙️ 고급 설정

### 커스텀 네트워크

외부 서비스와 연동이 필요한 경우:

```yaml
networks:
  dev_dong_network:
    external: true
```

### 볼륨 백업

```bash
# 볼륨 목록 확인
docker volume ls

# 볼륨 백업
docker run --rm -v dev_dong_docker_mariadb_data:/data -v $(pwd):/backup ubuntu tar czf /backup/db-backup.tar.gz /data
```

---

## 🆘 도움말

문제가 해결되지 않으면:

1. GitHub Issues에 문의
2. 로그 전체를 첨부: `docker-compose logs > logs.txt`
3. 환경 정보 제공: `docker-compose version`, `docker version`

