from fastapi import APIRouter, HTTPException, Query
from app.schemas.curriculum import AchievementStandardResponse, ListResponse
from app.db.database import select_all, select_one

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse,
    summary="성취기준 리스트 조회",
    description="성취기준 리스트를 조회합니다.",
)
async def get_achievement_standards():
    """
    전체 성취기준 리스트를 반환합니다.
    
    - **code**: 성취기준 코드 (PK)
    - **description**: 성취기준 내용
    - **evaluation_criteria**: 평가기준
    """
    results = select_all(table="achievement", order_by="code ASC")
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail="성취기준을 찾을 수 없습니다."
        )
    
    return ListResponse(items=results, total=len(results))


@router.get(
    "/{achievement_code}",
    response_model=AchievementStandardResponse,
    summary="성취기준 상세 조회",
    description="특정 성취기준의 상세 정보를 조회합니다.",
)
async def get_achievement_standard(achievement_code: str):
    """
    성취기준 코드로 특정 성취기준의 상세 정보를 반환합니다.
    
    - **achievement_code**: 성취기준 코드 (예: 9국01-01)
    """
    result = select_one(table="achievement", where={"code": achievement_code})
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"성취기준 코드 '{achievement_code}'를 찾을 수 없습니다."
        )
    
    return AchievementStandardResponse(**result)

