from typing import Optional, List
from pydantic import BaseModel


class LargeUnitResponse(BaseModel):
    """대단원 응답 스키마"""
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "수와 연산",
                "description": "수와 연산에 대한 대단원"
            }
        }


class SmallUnitResponse(BaseModel):
    """소단원 응답 스키마"""
    id: int
    large_unit_id: int
    name: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "large_unit_id": 1,
                "name": "자연수의 덧셈",
                "description": "자연수의 덧셈에 대한 소단원"
            }
        }


class AchievementStandardResponse(BaseModel):
    """성취기준 응답 스키마"""
    id: int
    small_unit_id: int
    code: str
    content: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "small_unit_id": 1,
                "code": "1-1-1",
                "content": "자연수의 덧셈을 이해하고 계산할 수 있다.",
                "description": "자연수 덧셈 성취기준"
            }
        }


class PassageResponse(BaseModel):
    """지문 응답 스키마"""
    id: int
    achievement_standard_id: int
    title: str
    content: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {    
                "id": 1,
                "achievement_standard_id": 1,
                "title": "자연수의 덧셈 문제",
                "content": "3 + 5 = ?",

            }
        }       


class PassageCreateRequest(BaseModel):
    """지문 생성 요청 스키마"""
    achievement_standard_id: int
    large_unit_id: int
    small_unit_id: int
    title: str
    content: str
    description: Optional[str] = None
    source_passage_id: Optional[int] = None  # 원본 지문 ID (선택사항)

    class Config:
        json_schema_extra = {
            "example": {
                "achievement_standard_id": 1,
                "large_unit_id": 1,
                "small_unit_id": 1,
                "title": "자연수의 곱셈 문제",
                "content": "3 × 5 = ?",
                "description": "자연수 곱셈 지문",
            }
        }


class PassageCreateFromSourceRequest(BaseModel):
    """원본 지문 기반 새 지문 생성 요청 스키마"""
    achievement_standard_id: int
    title: str
    content: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "achievement_standard_id": 1,
                "title": "수정된 자연수의 덧셈 문제",
                "content": "5 + 7 = ?",
                "description": "원본 지문을 수정한 새로운 지문"
            }
        }


class PassageUpdateRequest(BaseModel):
    """지문 수정 요청 스키마"""
    achievement_standard_id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "수정된 제목",
                "content": "수정된 내용",
                "description": "수정된 설명"
            }
        }


class ListResponse(BaseModel):
    """리스트 응답 스키마"""
    items: List[dict]
    total: int



class SelectSaveResultRequest(BaseModel):
    """결과 저장 요청 스키마"""
    result_ids: List[int]

    class Config:
        json_schema_extra = {
            "example": {
                "result_ids": [1, 2, 3]
            }
        }


class SelectSaveResultResponse(BaseModel):
    """결과 저장 응답 스키마"""
    success: bool
    message: str
    saved_count: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "3개의 결과가 성공적으로 저장되었습니다.",
                "saved_count": 3
            }
        }