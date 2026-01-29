from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.logger import logger
from fastapi import Header, HTTPException, status

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    평문 비밀번호와 해시된 비밀번호를 비교합니다.
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
        
    Returns:
        비밀번호 일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    비밀번호를 해시합니다.
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        해시된 비밀번호
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.
    
    Args:
        data: 토큰에 포함할 데이터 (예: {"sub": "user_id"})
        expires_delta: 토큰 만료 시간 (기본값: 설정의 access_token_expire_minutes)
        
    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 리프레시 토큰을 생성합니다.
    
    Args:
        data: 토큰에 포함할 데이터 (예: {"sub": "user_id"})
        expires_delta: 토큰 만료 시간 (기본값: 설정의 refresh_token_expire_days)
        
    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰을 디코드하고 검증합니다.
    
    Args:
        token: JWT 토큰 문자열
        
    Returns:
        디코드된 페이로드 또는 None (유효하지 않은 경우)
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    JWT 토큰을 검증하고 사용자 ID를 반환합니다.
    
    Args:
        token: JWT 토큰 문자열
        token_type: 토큰 타입 ("access" 또는 "refresh")
        
    Returns:
        사용자 ID 또는 None (유효하지 않은 경우)
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # 토큰 타입 확인
    if payload.get("type") != token_type:
        return None
    
    # 사용자 ID 추출
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    return user_id




def create_temp_token_for_user_1() -> str:
    """
    임시 함수: user_id가 1인 액세스 토큰을 생성합니다.
    """
    return create_refresh_token(data={"sub": "1"})

# 테스트용 토큰 생성 (모듈 로드 시 실행 - 필요시 logger로 확인)
token = create_temp_token_for_user_1()
logger.debug("Token: %s", token)