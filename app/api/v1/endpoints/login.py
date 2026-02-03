from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.login import (
    LoginRequest,
    LoginSuccessResponse,
    LoginErrorResponse,
    TokenData,
    RefreshTokenRequest,
    LogoutRequest,
    LogoutResponse,
    PasswordChangeRequest,
    PasswordChangeResponse
)
from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.utils.dependencies import get_current_user
from app.core.config import settings
from app.core.logger import logger
from app.db.auth import get_user_by_login_id, get_user_by_id, update_user_password

router = APIRouter()


# ===========================
# 더미 데이터 (테스트용 - 실제로는 DB 사용)
# ===========================
# 아래는 테스트용 더미 데이터입니다.
# 실제 환경에서는 DB의 users 테이블을 사용합니다.
#
# 테스트용 비밀번호 해시 생성 방법:
# from app.utils.auth import get_password_hash
# print(get_password_hash("your_password"))
#
# DUMMY_USERS = {
#     "test@test.com": {
#         "user_id": "test@test.com",
#         "name": "테스트 사용자",
#         "password_hash": "$2b$12$jg6oUI5hFidFqhGYCo3yKOF/eYbz15E9pLmNdG0GJLLY29AvADJNq",  # password123
#     },
#     "admin@test.com": {
#         "user_id": "admin@test.com",
#         "name": "관리자",
#         "password_hash": "$2b$12$QzaSPHlpv9aYYYJLjWfwL.UuwsHk4HNtXmoA6zBGmQGHCwzHTw6oe",  # admin123
#     }
# }


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
    
    - **user_id**: 사용자 ID (이메일)
    - **password**: 비밀번호 (평문)
    
    프로세스:
    1. 프론트엔드에서 평문 비밀번호 수신 (HTTPS로 암호화됨)
    2. DB에서 사용자 조회 (이메일 기준)
    3. 입력된 평문 비밀번호와 DB의 해시된 비밀번호 비교
    4. 인증 성공 시 JWT 토큰 발급
    
    성공 시 액세스 토큰과 리프레시 토큰을 반환합니다.
    """
    try:
        # 1. DB에서 사용자 조회 (이메일 기준)
        user = get_user_by_login_id(request.user_id)
        
        # 2. 사용자가 존재하지 않거나 비활성 상태인 경우
        if not user:
            logger.warning("로그인 실패 - 사용자 없음: %s", request.user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다."
            )
        
        # 사용자 비활성 상태 체크 (is_active 컬럼이 있는 경우)
        if user.get("is_active") is False:
            logger.warning("로그인 실패 - 비활성 계정: %s", request.user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다. 관리자에게 문의하세요."
            )
        
        # 3. 평문 비밀번호와 DB의 해시된 비밀번호 비교
        if not verify_password(request.password, user["password_hash"]):
            logger.warning("로그인 실패 - 비밀번호 불일치: %s", request.user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다."
            )
        
        # 4. JWT 토큰 생성 (user_id 또는 email을 토큰 subject로 사용)
        user_identifier = str(user["user_id"])  # 또는 user["email"]
        access_token = create_access_token(data={"sub": user_identifier, "role": user["role"]})
        refresh_token = create_refresh_token(data={"sub": user_identifier, "role": user["role"]})
        
        # 토큰 데이터 구성
        token_data = TokenData(
            access_token=access_token,
            refresh_token=refresh_token,  # 로그인 시에도 리프레시 토큰 반환
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60  # 초 단위로 변환
        )
        
        logger.info("로그인 성공: user_id=%s", user_identifier)
        return LoginSuccessResponse(
            success=True,
            message="로그인에 성공했습니다.",
            data=token_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("로그인 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
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
    
    # DB에서 사용자 존재 여부 확인
    user = get_user_by_id(int(user_id))  # user_id를 숫자로 저장한 경우
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 사용자 비활성 상태 체크
    if user.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비활성화된 계정입니다."
        )
    
    # 새로운 토큰 생성 (Refresh Token Rotation 전략)
    # 보안을 위해 액세스 토큰과 리프레시 토큰을 모두 새로 발급합니다.
    # 이전 리프레시 토큰은 더 이상 사용할 수 없습니다.
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


@router.post(
    "/change-password",
    response_model=PasswordChangeResponse,
    summary="비밀번호 변경",
    description="로그인한 사용자의 비밀번호를 변경합니다.",
    tags=["인증"]
)
async def change_password(
    request: PasswordChangeRequest,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    현재 로그인한 사용자의 비밀번호를 변경합니다.
    
    - **current_password**: 현재 비밀번호
    - **new_password**: 새 비밀번호
    """
    user_id, _ = user_data
    
    # 1. 사용자 정보 조회
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 2. 현재 비밀번호 확인
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다."
        )
    
    # 3. 새 비밀번호 유효성 검사 (필요한 경우 추가)
    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 현재 비밀번호와 다르게 설정해야 합니다."
        )
        
    # 4. 비밀번호 업데이트
    new_password_hash = get_password_hash(request.new_password)
    success = update_user_password(user_id, new_password_hash)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경에 실패했습니다."
        )
        
    logger.info(f"비밀번호 변경 성공: user_id={user_id}")
    
    return PasswordChangeResponse(
        success=True,
        message="비밀번호가 성공적으로 변경되었습니다."
    )
