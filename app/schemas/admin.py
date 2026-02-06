from typing import Optional
from pydantic import BaseModel, Field

class UserListItem(BaseModel):
    id: int = Field(..., description="사용자 ID")
    name: str = Field(..., description="이름")
    email: Optional[str] = Field(None, description="이메일")
    subject: Optional[str] = Field(None, description="과목")
    team_name: Optional[str] = Field(None, description="팀 이름")
    role: Optional[str] = Field(None, description="역할")
    input_tokens: int = Field(0, description="Input 토큰")
    output_tokens: int = Field(0, description="Output 토큰")
    price_dollers: float = Field(0.0, description="예상 비용 (달러)")
    price_won: int = Field(0, description="예상 비용 (원)")
    status: bool = Field(True, description="활성화 여부 (True | False)")
    memo: Optional[str] = Field(None, description="메모")

class UserUpdateRoleRequest(BaseModel):
    role: str = Field(..., description="접근 권한 (admin | master | user | tester)")

class UserUpdateStatusRequest(BaseModel):
    is_active: bool = Field(..., description="활성화 상태 (True | False)")

class UserUpdateMemoRequest(BaseModel):
    memo: Optional[str] = Field(None, description="메모 내용")
