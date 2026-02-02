from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProjectMetaResponse(BaseModel):
    """프로젝트 메타정보 응답 스키마"""
    success: bool = True
    message: str = "프로젝트 메타정보 조회 성공"
    project_id: int
    grade: Optional[str] = None
    semester: Optional[str] = None
    subject: Optional[str] = None
    publisher_author: Optional[str] = None
    large_unit_name: Optional[str] = None
    small_unit_name: Optional[str] = None
    question_type: Optional[str] = None
    target_count: Optional[int] = None
    additional_prompt: Optional[str] = None
    stem_directive: Optional[str] = None
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "프로젝트 메타정보 조회 성공",
                "project_id": 1,
                "project_name": "프로젝트 이름",
                "grade": "중학교",
                "semester": "1학기",
                "subject": "국어",
                "publisher_author": "출판사/저자",
                "large_unit_name": "1. 문학의 즐거움",
                "small_unit_name": "(1) 시 감상하기",
                "question_type": "5지선다",
                "target_count": 10,
                "additional_prompt": "추가 프롬프트",
                "stem_directive": "주제 지시문"
            }
        }


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
    custom_title: Optional[str] = None
    content: str
    description: Optional[str] = None
    is_use: Optional[int] = 1
    success: bool = True
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {    
                "id": 1,
                "achievement_standard_id": 1,
                "title": "자연수의 덧셈 문제",
                "content": "3 + 5 = ?",
                "is_use": 1,

            }
        }       


class PassageCreateRequest(BaseModel):
    """지문 생성 요청 스키마"""
    # ✅ 필수 필드
    title: str  # 지문 제목 (필수)
    content: str  # 지문 내용 (필수)
    auth: Optional[str] = None  # 작성자 (선택)

    # ✅ scope_id 또는 achievement_standard_id 중 하나는 필수 (둘 다 없으면 기본값 사용)
    scope_id: Optional[int] = None
    achievement_standard_id: Optional[int] = None

    # ✅ 선택 필드
    custom_title: Optional[str] = None  # 커스텀 제목
    source_passage_id: Optional[int] = None  # 원본 지문 ID
    is_use: Optional[int] = 1  # 사용 여부 (기본값: 1)
    description: Optional[str] = None  # 설명 (호환용, 실제로는 사용 안 함)

    # ✅ 기존 요청 호환용(현재 API에서 실제로는 저장에 사용하지 않음)
    user_id: Optional[int] = None  # 사용자 ID (자동으로 current_user_id 사용)
    large_unit_id: Optional[int] = None
    small_unit_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "자연수의 곱셈 문제",
                "content": "3 × 5 = ?",
                "auth": "작성자",
                "scope_id": 10,
                "custom_title": "내가 만든 지문",
                "is_use": 1
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


class ProjectPassageItem(BaseModel):
    """프로젝트에서 사용된 지문 항목 스키마"""
    passage_id: Optional[int] = None
    title: str
    content: str
    auth: Optional[str] = None
    is_custom: int  # 0: 원본, 1: 커스텀

    class Config:
        json_schema_extra = {
            "example": {
                "passage_id": 1,
                "title": "지문 제목",
                "content": "지문 내용",
                "auth": "저자명",
                "is_custom": 0
            }
        }


class ProjectPassageResponse(BaseModel):
    """프로젝트에서 사용된 지문 목록 응답 스키마"""
    success: Optional[bool] = None
    message: Optional[str] = None
    items: List[ProjectPassageItem]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "프로젝트에서 사용된 지문 목록 조회 성공",
                "items": [
                    {
                        "passage_id": 1,
                        "title": "지문 제목",
                        "content": "지문 내용",
                        "auth": "저자명",
                        "is_custom": 0
                    }
                ],
                "total": 1
            }
        }



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


class QuestionMetaUpdateRequest(BaseModel):
    """문항 메타데이터(피드백/선택여부/난이도) 업데이트 요청"""
    project_id: int
    question_id: int

    feedback_score: Optional[float] = None
    is_checked: Optional[int] = None  # 1/0 (선택 여부)
    modified_difficulty: Optional[str] = None


class QuestionMetaUpdateResponse(BaseModel):
    """문항 메타데이터 업데이트 응답"""
    success: bool
    message: str
    updated_count: int = 0
    failed_count: int = 0
    results: Optional[List[Dict[str, Any]]] = None  # 각 문항별 업데이트 결과


class QuestionMetaBatchUpdateRequest(BaseModel):
    """문항 메타데이터 일괄 업데이트 요청"""
    items: List[QuestionMetaUpdateRequest] = Field(..., description="업데이트할 문항 리스트", min_items=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "project_id": 1,
                        "question_id": 2,
                        "feedback_score": 4.5,
                        "is_checked": 1,
                        "modified_difficulty": "상"
                    },
                    {
                        "project_id": 1,
                        "question_id": 4,
                        "feedback_score": 3.0,
                        "is_checked": 1,
                        "modified_difficulty": "중"
                    }
                ]
            }
        }



# Passages 관련 스키마 (DB 스키마 기반)
class PassageDBResponse(BaseModel):
    """원본 지문 응답 스키마 (DB 기반)"""
    passage_id: int
    title: Optional[str] = None
    context: str
    auth: Optional[str] = None
    scope_id: Optional[int] = None

class ScopeCreateRequest(BaseModel):
    """범위 생성 요청 스키마"""
    grade: int
    semester: int
    publisher_author: str
    large_unit_id: int
    large_unit_name: str
    small_unit_id: int
    small_unit_name: str


    class Config:
        json_schema_extra = {
            "example": {
                "grade": 1,
                "semester": 1,
                "publisher_author": "미래엔",
                "large_unit_id": 1,
                "large_unit_name": "1. 문학의 즐거움",
                "small_unit_id": 1,
                "small_unit_name": "(1) 시 감상하기"
            }
        }


class PassageDBCreateRequest(BaseModel):
    """원본 지문 생성 요청 스키마"""
    title: Optional[str] = None
    context: str
    auth: Optional[str] = None
    scope_id: Optional[int] = None




class ScopeCreateResponse(BaseModel):
    """범위 생성 응답 스키마"""
    project_id: int
    scope_id: int


    class Config:
        json_schema_extra = {
            "example": {
                "projetct_id": "1",
                "scope_id": 1
            }
        }


class PassageDBUpdateRequest(BaseModel):
    """원본 지문 수정 요청 스키마"""
    title: Optional[str] = None
    context: Optional[str] = None
    auth: Optional[str] = None
    scope_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "수정된 제목",
                "context": "수정된 내용",
                "auth": "수정된 저자명"
            }
        }


class PassageCustomResponse(BaseModel):
    """커스텀 지문 응답 스키마"""
    custom_passage_id: int
    user_id: int
    scope_id: Optional[int] = None
    custom_title: Optional[str] = None
    title: Optional[str] = None
    auth: Optional[str] = None
    context: str
    passage_id: Optional[int] = None
    created_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "custom_passage_id": 1,
                "user_id": 1,
                "scope_id": 1,
                "custom_title": "커스텀 제목",
                "title": "제목",
                "auth": "저자명",
                "context": "지문 내용",
                "passage_id": None,
                "created_at": "2024-01-01 00:00:00"
            }
        }


class PassageCustomCreateRequest(BaseModel):
    """커스텀 지문 생성 요청 스키마"""
    user_id: int
    scope_id: Optional[int] = None
    custom_title: Optional[str] = None
    title: Optional[str] = None
    auth: Optional[str] = None
    context: str
    passage_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "scope_id": 1,
                "custom_title": "커스텀 제목",
                "title": "제목",
                "auth": "저자명",
                "context": "지문 내용",
                "passage_id": None
            }
        }


class PassageCustomUpdateRequest(BaseModel):
    """커스텀 지문 수정 요청 스키마"""
    scope_id: Optional[int] = None
    custom_title: Optional[str] = None
    title: Optional[str] = None
    auth: Optional[str] = None
    context: Optional[str] = None
    passage_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "custom_title": "수정된 커스텀 제목",
                "title": "수정된 제목",
                "context": "수정된 내용",
                "scope_id": 123
            }
        }
