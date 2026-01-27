from typing import List
from pydantic import BaseModel


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
                        "content": "원본 내용...",
                        "auth": "작성자",
                        "scope_id": 10,
                        "is_custom": 0,
                        
                    }
                ],
                "custom": [
                    {
                        "id": 2,
                        "title": "커스텀 지문",
                        "content": "커스텀 내용...",
                        "auth": "작성자",
                        "scope_id": 10,
                        "is_custom": 1
                    }
                ],
                "total_original": 15,
                "total_custom": 3
            }
        }
