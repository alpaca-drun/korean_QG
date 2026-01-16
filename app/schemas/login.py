from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""
    user_id: str = Field(..., description="사용자 ID (이메일 등)")
    password: str = Field(..., description="비밀번호")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "test",
                "password": "password123"
            }
        }


class TokenData(BaseModel):
    """토큰 데이터 스키마"""
    access_token: str = Field(..., description="JWT 액세스 토큰")
    refresh_token: str = Field(..., description="JWT 리프레시 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="액세스 토큰 만료 시간 (초)")


class LoginSuccessResponse(BaseModel):
    """로그인 성공 응답 스키마"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: TokenData = Field(..., description="토큰 정보")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "로그인에 성공했습니다.",
                "data": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }


class LoginErrorResponse(BaseModel):
    """로그인 실패 응답 스키마"""
    success: bool = Field(default=False, description="성공 여부")
    message: str = Field(..., description="에러 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "아이디 또는 비밀번호가 올바르지 않습니다."
            }
        }


class RefreshTokenRequest(BaseModel):
    """토큰 갱신 요청 스키마"""
    refresh_token: str = Field(..., description="리프레시 토큰")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class LogoutRequest(BaseModel):
    """로그아웃 요청 스키마"""
    refresh_token: Optional[str] = Field(None, description="리프레시 토큰 (선택사항)")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class LogoutResponse(BaseModel):
    """로그아웃 응답 스키마"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(..., description="응답 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "로그아웃에 성공했습니다."
            }
        }
