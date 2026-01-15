from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.utils.auth import verify_token

# HTTP Bearer 토큰 스키마
security = HTTPBearer(
    scheme_name="Bearer",
    description="Bearer 토큰을 입력하세요. 예: Bearer <your-token>"
)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    현재 인증된 사용자를 가져옵니다.
    
    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰
        
    Returns:
        사용자 ID
        
    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    token = credentials.credentials
    user_id = verify_token(token, token_type="access")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[str]:
    """
    현재 인증된 사용자를 가져옵니다 (선택사항).
    토큰이 없거나 유효하지 않아도 예외를 발생시키지 않습니다.
    
    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰 (선택사항)
        
    Returns:
        사용자 ID 또는 None
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    user_id = verify_token(token, token_type="access")
    
    return user_id



