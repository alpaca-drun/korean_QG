from typing import List
from pydantic import BaseModel, Field
from typing import Optional

class PassageListResponse(BaseModel):
    """지문 리스트 응답 스키마 (원본과 커스텀 분리)"""
    success: bool = True
    message: str = "지문 리스트 조회 성공"
    original: List[dict]  # 원본 지문 (passages 테이블)
    custom: List[dict]    # 커스텀 지문 (passage_custom 테이블)
    total_original: int   # 원본 지문 총 개수
    total_custom: int     # 커스텀 지문 총 개수

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "지문 리스트 조회 성공",
                "original": [
                    {
                        "id": 1,
                        "title": "원본 지문",
                        "auth": "저자명",
                        "content": "원본 내용...",
                        "scope_id": 10,
                        "is_custom": 0,
                        
                    }
                ],
                "custom": [
                    {
                        "id": 2,
                        "title": "커스텀 지문",
                        "auth": "작성자",
                        "content": "커스텀 내용...",
                        "scope_id": 10,
                        "is_custom": 1
                    }
                ],
                "total_original": 15,
                "total_custom": 3
            }
        }


class PassageUpdateRequest(BaseModel):
    """지문 수정 요청 스키마"""
    passage_id: int = Field(..., description="지문 ID")
    is_custom: int = Field(..., description="커스텀 지문 여부")
    project_id: int = Field(..., description="프로젝트 ID")


    title: Optional[str] = Field(None, description="지문 제목")
    auth: Optional[str] = Field(None, description="작성자")
    custom_title: str = Field(..., description="커스텀 제목")

    content: str = Field(..., description="지문 내용")

    class Config:
        json_schema_extra = {
            "example": {
                "passage_id": 1,
                "is_custom": 0,
                "content": "수정된 지문 내용",
                "project_id": 1,
                "custom_title": "내가 수정한 타이틀",

            }
        }



class PassageUpdateResponse(BaseModel):
    """지문 응답 스키마"""
    success: bool = True
    message: str = "지문 수정 성공"
    passage_id: int = Field(..., description="새로 저장된 지문 ID")
    is_custom: int = Field(..., description="커스텀 지문 여부")

    class Config:
        json_schema_extra = {
            "example": {    
                "success": True,
                "message": "지문 수정 성공",
                "passage_id": 1,
                "is_custom": 1
            }
        }    

class PassageUseRequest(BaseModel):
    project_id: int = Field(..., description="프로젝트 ID")
    passage_id: int = Field(..., description="지문 ID")
    is_custom: int = Field(..., description="커스텀 지문 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 1,
                "passage_id": 1,
                "is_custom": 1
            }
        }


class PassageGenerateWithoutPassageRequest(BaseModel):
    """지문없이 생성 요청 스키마"""
    project_id: int = Field(..., description="프로젝트 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 1,

            }
        }