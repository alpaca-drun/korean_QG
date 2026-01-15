# 환경 변수 설정 가이드

프로젝트 루트에 `.env` 파일을 생성하여 아래 환경 변수들을 설정하세요.

## 📋 .env 파일 생성 방법

```bash
# 프로젝트 루트에서 실행
touch .env
```

## 🔧 필수 환경 변수

### 데이터베이스 설정

```env
# MariaDB 연결 정보
DB_HOST=localhost
DB_PORT=8001
DB_USER=curriculum_user
DB_PASSWORD=curriculum_password
DB_DATABASE=curriculum_db

# Docker MariaDB Root 비밀번호
DB_ROOT_PASSWORD=rootpassword
```

> **참고**: `docker-compose.yml`의 기본값과 동일하게 설정하세요.
> - Docker 컨테이너는 호스트의 `8001` 포트를 `3306`로 매핑합니다.
> - 애플리케이션에서는 `DB_PORT=8001`로 설정하세요.

### JWT 인증 설정

```env
# JWT 토큰 설정
JWT_SECRET_KEY=your-secret-key-change-this-in-production-use-long-random-string
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

> **보안 주의**: 프로덕션 환경에서는 반드시 강력한 무작위 문자열로 변경하세요!

```bash
# 안전한 시크릿 키 생성 예시
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### LLM API 설정

```env
# Gemini API 키
GEMINI_API_KEY=your_gemini_api_key

# 또는 여러 개의 키를 콤마로 구분
# GEMINI_API_KEYS=key1,key2,key3

# OpenAI API 키
OPENAI_API_KEY=your_openai_api_key

# 기본 LLM 제공자
DEFAULT_LLM_PROVIDER=gemini
```

## 🎯 선택적 환경 변수

### 애플리케이션 설정

```env
APP_NAME=Curriculum API
APP_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### API 키 로테이션 설정

```env
API_KEY_ROTATION_STRATEGY=round_robin
MAX_PARALLEL_API_KEYS=5
API_CALL_TIMEOUT=60
API_RETRY_TIMEOUT=30
ENABLE_FAST_FAILOVER=True
```

### 배치 작업 설정

```env
MAX_BATCH_SIZE=10
BATCH_TIMEOUT=30
```

### Celery 설정 (비동기 작업)

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
ENABLE_CELERY=False
```

### 파일 저장소 설정

```env
FILE_STORAGE_PATH=storage/files
```

## 📝 완성된 .env 파일 예시

```env
# ===========================
# 데이터베이스 설정
# ===========================
DB_HOST=localhost
DB_PORT=8001
DB_USER=curriculum_user
DB_PASSWORD=curriculum_password
DB_DATABASE=curriculum_db
DB_ROOT_PASSWORD=rootpassword

# ===========================
# JWT 인증 설정
# ===========================
JWT_SECRET_KEY=super-secret-key-please-change-in-production-12345678
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ===========================
# LLM API 설정
# ===========================
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_LLM_PROVIDER=gemini

# ===========================
# 개발 설정
# ===========================
DEBUG=True
```

## 🔍 환경 변수가 제대로 로드되는지 확인

```python
# Python 콘솔에서 확인
from app.core.config import settings

print(f"DB Host: {settings.db_host}")
print(f"DB Port: {settings.db_port}")
print(f"DB Name: {settings.db_database}")
print(f"JWT Secret: {settings.jwt_secret_key[:10]}...")
```

## ⚠️ 주의사항

1. **.env 파일은 절대 Git에 커밋하지 마세요!**

2. **프로덕션 환경에서는 반드시 안전한 값으로 변경하세요!**
   - 특히 `JWT_SECRET_KEY`와 DB 비밀번호는 필수입니다.

3. **Docker Compose 사용 시**
   - `docker-compose.yml`과 `.env`의 환경 변수가 일치해야 합니다.
   - DB_PORT는 호스트 포트(8001)를 사용하세요.

4. **팀원과 공유할 때**
   - `.env` 대신 이 가이드 문서를 공유하세요.
   - 민감한 정보(API 키, 비밀번호)는 별도로 안전하게 전달하세요.

