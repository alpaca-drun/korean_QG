from fastapi import APIRouter, HTTPException, Query
from app.schemas.curriculum import ListResponse
from app.db.database import select_with_query

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse,
    summary="소단원 리스트 조회",
    description="학년, 학기, 출판사/저자, 대단원에 해당하는 소단원 리스트를 조회합니다.",
    tags=["메타데이터"]
)
async def get_small_units(
    grade: int = Query(..., description="학년 (1, 2, 3)", example=1),
    semester: int = Query(..., description="학기 (1, 2)", example=1),
    publisher_author: str = Query(..., description="출판사/저자", example="미래엔"),
    large_unit_id: int = Query(..., description="대단원 ID", example=1)
):
    """
    학년, 학기, 출판사/저자, 대단원 ID를 기반으로 소단원 리스트를 반환합니다.
    
    - **grade**: 학년 (필수)
    - **semester**: 학기 (필수)
    - **publisher_author**: 출판사/저자 (필수)
    - **large_unit_id**: 대단원 ID (필수)
    """
    query = """
        SELECT DISTINCT small_unit_id, small_unit_name
        FROM project_scopes
        WHERE grade = %s AND semester = %s AND publisher_author = %s AND large_unit_id = %s
            AND small_unit_id IS NOT NULL AND small_unit_name IS NOT NULL
        ORDER BY small_unit_id
    """
    
    results = select_with_query(query, (grade, semester, publisher_author, large_unit_id))
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"해당 조건에 맞는 소단원을 찾을 수 없습니다."
        )
    
    items = [
        {"id": row["small_unit_id"], "name": row["small_unit_name"]}
        for row in results
    ]
    
    return ListResponse(items=items, total=len(items))


