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
                "description": "자연수 덧셈 지문"
            }
        }


class ListResponse(BaseModel):
    """리스트 응답 스키마"""
    items: List[dict]
    total: int

