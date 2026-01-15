from fastapi import APIRouter, HTTPException, status
from app.schemas.login import (
    LoginRequest,
    LoginSuccessResponse,
    LoginErrorResponse,
    TokenData,
    RefreshTokenRequest,
    LogoutRequest,
    LogoutResponse
)
from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.core.config import settings

router = APIRouter()


# 더미 사용자 데이터 (추후 DB 조회로 변경 예정)
# 실제 프로덕션에서는 DB에서 사용자 정보를 조회해야 합니다.
# 비밀번호 해시는 미리 생성된 값 사용 (모듈 로드 시 bcrypt 초기화 문제 방지)
DUMMY_USERS = {
    "test@test.com": {
        "user_id": "test@test.com",
        "name": "테스트 사용자",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYxK.6vUZVm",  # password123
    },
    "admin@test.com": {
        "user_id": "admin@test.com",
        "name": "관리자",
        "hashed_password": "$2b$12$yGqxfzZKs0RM3AvDzFKTyuaHFnL3kpXhXDQqpVVqJhXQJ6XqZ8v5e",  # admin123
    }
}


@router.post(
    "/login",
    response_model=LoginSuccessResponse,
    responses={
        200: {"description": "로그인 성공"},
        401: {"model": LoginErrorResponse, "description": "로그인 실패"}
    },
    summary="로그인",
    description="사용자 ID와 비밀번호로 로그인하고 JWT 토큰을 발급받습니다.",
    tags=["인증"]
)
async def login(request: LoginRequest):
    """
    사용자 로그인을 처리하고 JWT 토큰을 발급합니다.
    
    - **user_id**: 사용자 ID (이메일 등)
    - **password**: 비밀번호
    
    성공 시 액세스 토큰과 리프레시 토큰을 반환합니다.
    
    **더미 계정:**
    - test@test.com / password123
    - admin@test.com / admin123
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB에서 사용자 정보 조회로 변경
    user = DUMMY_USERS.get(request.user_id)
    
    # 사용자가 존재하지 않거나 비밀번호가 일치하지 않는 경우
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": user["user_id"]})
    refresh_token = create_refresh_token(data={"sub": user["user_id"]})
    
    # 토큰 데이터 구성
    token_data = TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60  # 초 단위로 변환
    )
    
    return LoginSuccessResponse(
        success=True,
        message="로그인에 성공했습니다.",
        data=token_data
    )


@router.post(
    "/refresh",
    response_model=LoginSuccessResponse,
    responses={
        200: {"description": "토큰 갱신 성공"},
        401: {"model": LoginErrorResponse, "description": "토큰 갱신 실패"}
    },
    summary="토큰 갱신",
    description="리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.",
    tags=["인증"]
)
async def refresh_token(request: RefreshTokenRequest):
    """
    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급합니다.
    
    - **refresh_token**: 리프레시 토큰
    
    성공 시 새로운 액세스 토큰과 리프레시 토큰을 반환합니다.
    """
    # 리프레시 토큰 검증
    user_id = verify_token(request.refresh_token, token_type="refresh")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 리프레시 토큰입니다."
        )
    
    # TODO: DB에서 사용자 존재 여부 확인
    if user_id not in DUMMY_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 새로운 토큰 생성
    new_access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})
    
    # 토큰 데이터 구성
    token_data = TokenData(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )
    
    return LoginSuccessResponse(
        success=True,
        message="토큰이 갱신되었습니다.",
        data=token_data
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="로그아웃",
    description="로그아웃을 처리합니다.",
    tags=["인증"]
)
async def logout(request: LogoutRequest):
    """
    사용자 로그아웃을 처리합니다.
    
    - **refresh_token**: 리프레시 토큰 (선택사항)
    
    실제 프로덕션 환경에서는:
    1. 리프레시 토큰을 블랙리스트에 추가
    2. Redis 등에 토큰 무효화 정보 저장
    3. DB에 로그아웃 기록 저장
    
    현재는 클라이언트에서 토큰을 삭제하는 것으로 처리합니다.
    """
    # TODO: 리프레시 토큰 블랙리스트 처리 (Redis 등 사용)
    # TODO: 로그아웃 로그 기록
    
    return LogoutResponse(
        success=True,
        message="로그아웃에 성공했습니다."
    )