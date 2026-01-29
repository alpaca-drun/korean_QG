# JWT 인증 시스템 가이드

## 개요

이 프로젝트는 JWT(JSON Web Token) 기반의 인증 시스템을 사용합니다.

## 주요 기능

- **로그인**: 사용자 ID와 비밀번호로 로그인하고 JWT 토큰 발급
- **토큰 갱신**: 리프레시 토큰으로 새로운 액세스 토큰 발급
- **로그아웃**: 로그아웃 처리 (클라이언트에서 토큰 삭제)
- **인증 보호**: 보호된 엔드포인트에 대한 접근 제어

## API 엔드포인트

### 1. 로그인

**POST** `/api/v1/auth/login`

사용자 ID와 비밀번호로 로그인하고 JWT 토큰을 발급받습니다.

**요청 본문:**
```json
{
  "user_id": "test@test.com",
  "password": "password123"
}
```

**응답 (성공):**
```json
{
  "success": true,
  "message": "로그인에 성공했습니다.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**응답 (실패):**
```json
{
  "detail": "아이디 또는 비밀번호가 올바르지 않습니다."
}
```

### 2. 토큰 갱신

**POST** `/api/v1/auth/refresh`

리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.

**요청 본문:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**응답:**
```json
{
  "success": true,
  "message": "토큰이 갱신되었습니다.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### 3. 로그아웃

**POST** `/api/v1/auth/logout`

로그아웃을 처리합니다.

**요청 본문:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**응답:**
```json
{
  "success": true,
  "message": "로그아웃에 성공했습니다."
}
```

## 인증이 필요한 API 사용하기

인증이 필요한 엔드포인트를 호출할 때는 HTTP Authorization 헤더에 Bearer 토큰을 포함해야 합니다.

**헤더 예시:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 더미 계정

개발/테스트용 더미 계정:

1. **일반 사용자**
   - ID: `test@test.com`
   - 비밀번호: `password123`

2. **관리자**
   - ID: `admin@test.com`
   - 비밀번호: `admin123`

## 환경 변수 설정

`.env` 파일에 다음 설정을 추가할 수 있습니다:

```env
# JWT 인증 설정
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

**주의**: 프로덕션 환경에서는 반드시 `JWT_SECRET_KEY`를 안전한 랜덤 문자열로 변경하세요!

## 보호된 엔드포인트 만들기

다른 엔드포인트에서 인증을 요구하려면 `get_current_user` 의존성을 사용하세요:

```python
from fastapi import APIRouter, Depends
from app.utils.dependencies import get_current_user

router = APIRouter()

@router.get("/protected")
async def protected_endpoint(current_user: str = Depends(get_current_user)):
    """
    인증이 필요한 엔드포인트
    """
    return {"message": f"안녕하세요, {current_user}님!"}
```

선택적 인증 (토큰이 없어도 접근 가능하지만, 있으면 사용자 정보 제공):

```python
from fastapi import APIRouter, Depends
from typing import Optional
from app.utils.dependencies import get_current_user_optional

router = APIRouter()

@router.get("/optional-auth")
async def optional_auth_endpoint(current_user: Optional[str] = Depends(get_current_user_optional)):
    """
    선택적 인증 엔드포인트
    """
    if current_user:
        return {"message": f"안녕하세요, {current_user}님!"}
    else:
        return {"message": "게스트로 접근 중입니다."}
```

## 토큰 만료 시간

- **액세스 토큰**: 30분 (기본값)
- **리프레시 토큰**: 7일 (기본값)

액세스 토큰이 만료되면 리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받으세요.

## 보안 권장사항

1. **프로덕션 환경**:
   - `JWT_SECRET_KEY`를 강력한 랜덤 문자열로 변경
   - HTTPS 사용 필수
   - 리프레시 토큰 블랙리스트 구현 (Redis 등)

2. **클라이언트 측**:
   - 액세스 토큰은 메모리에 저장
   - 리프레시 토큰은 HttpOnly 쿠키에 저장 권장
   - XSS 공격 방지

3. **서버 측**:
   - 비밀번호는 절대 평문으로 저장하지 않음 (bcrypt 해싱 사용)
   - 로그인 시도 횟수 제한 구현 권장
   - 로그 기록 및 모니터링

## TODO (추후 구현 예정)

- [ ] 실제 데이터베이스 연동
- [ ] 리프레시 토큰 블랙리스트 (Redis)
- [ ] 로그인 시도 횟수 제한
- [ ] 이메일 인증
- [ ] 비밀번호 재설정
- [ ] 소셜 로그인 (OAuth2)
- [ ] 역할 기반 접근 제어 (RBAC)


















