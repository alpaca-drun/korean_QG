from fastapi import APIRouter, HTTPException, Query, Depends
from app.schemas.curriculum import ScopeCreateResponse
from app.db.database import select_one, insert_one
from app.utils.dependencies import get_current_user
from app.core.logger import logger
router = APIRouter()


@router.get(
    "",
    response_model=ScopeCreateResponse,
    summary="사용자 선택 범위 조회",
    description="사용자가 선택한 학년, 학기, 출판사/저자, 대단원, 소단원에 해당하는 scope_id를 반환합니다.",
    tags=["메타데이터"]
)
async def get_scope(
    project_name: str = Query(..., description="프로젝트 이름", example="새 프로젝트"),
    grade: int = Query(..., description="학년 (1, 2, 3)", example=1),
    semester: int = Query(..., description="학기 (1, 2)", example=1),
    publisher_author: str = Query(..., description="출판사/저자", example="천재교육/노미숙"),
    large_unit_id: int = Query(..., description="대단원 ID", example=1),
    small_unit_id: int = Query(..., description="소단원 ID", example=1),
    current_user_id: str = Depends(get_current_user)
):
    """
    사용자가 선택한 조건에 맞는 scope_id를 조회합니다.
    
    - **grade**: 학년 (필수)
    - **semester**: 학기 (필수)
    - **publisher_author**: 출판사/저자 (필수)
    - **large_unit_id**: 대단원 ID (필수)
    - **small_unit_id**: 소단원 ID (필수)
    
    Returns:
        scope_id: 해당 조건의 범위 ID
    """
    try:
        result = select_one("project_scopes", {
            "grade": grade,
            "semester": semester,
            "publisher_author": publisher_author,
            "large_unit_id": large_unit_id,
            "small_unit_id": small_unit_id
        })
        

        project_id = insert_one("projects", {
            "user_id": current_user_id,
            "project_name": project_name,
            "scope_id": result["scope_id"],
            "status": "WRITING"
        })
        result["project_id"] = project_id

        if not result:
            raise HTTPException(
                status_code=404,
                detail="해당 조건에 맞는 범위를 찾을 수 없습니다."
            )
        
        return ScopeCreateResponse(project_id=result["project_id"], scope_id=result["scope_id"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("범위 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"범위 조회 중 오류가 발생했습니다: {str(e)}"
        )
