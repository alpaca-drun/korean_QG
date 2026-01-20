from fastapi import APIRouter, HTTPException, Query
from app.schemas.curriculum import ListResponse
from app.db.database import select_with_query

router = APIRouter()


@router.get(
    "/publishers",
    response_model=ListResponse,
    summary="출판사/저자 리스트 조회",
    description="학년과 학기에 해당하는 출판사/저자 리스트를 조회합니다.",
    tags=["메타데이터"]
)
async def get_publishers(
    grade: int = Query(..., description="학년 (1, 2, 3)", example=1),
    semester: int = Query(..., description="학기 (1, 2)", example=1)
):
    """
    학년과 학기를 기반으로 출판사/저자 리스트를 반환합니다.
    
    - **grade**: 학년 (필수)
    - **semester**: 학기 (필수)
    """
    query = """
        SELECT DISTINCT publisher_author
        FROM project_scopes
        WHERE grade = %s AND semester = %s AND publisher_author IS NOT NULL
        ORDER BY publisher_author
    """
    
    results = select_with_query(query, (grade, semester))
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"학년 {grade}, 학기 {semester}에 해당하는 출판사/저자를 찾을 수 없습니다."
        )
    
    items = [
        {"id": idx + 1, "name": row["publisher_author"]}
        for idx, row in enumerate(results)
    ]
    
    return ListResponse(items=items, total=len(items))


@router.get(
    "",
    response_model=ListResponse,
    summary="대단원 리스트 조회",
    description="학년, 학기, 출판사/저자에 해당하는 대단원 리스트를 조회합니다.",
    tags=["메타데이터"]
)
async def get_large_units(
    grade: int = Query(..., description="학년 (1, 2, 3)", example=1),
    semester: int = Query(..., description="학기 (1, 2)", example=1),
    publisher_author: str = Query(..., description="출판사/저자", example="미래엔")
):
    """
    학년, 학기, 출판사/저자를 기반으로 대단원 리스트를 반환합니다.
    
    - **grade**: 학년 (필수)
    - **semester**: 학기 (필수)
    - **publisher_author**: 출판사/저자 (필수)
    """
    query = """
        SELECT DISTINCT large_unit_id, large_unit_name
        FROM project_scopes
        WHERE grade = %s AND semester = %s AND publisher_author = %s
            AND large_unit_id IS NOT NULL AND large_unit_name IS NOT NULL
        ORDER BY large_unit_id
    """
    
    results = select_with_query(query, (grade, semester, publisher_author))
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"해당 조건에 맞는 대단원을 찾을 수 없습니다."
        )
    
    items = [
        {"id": row["large_unit_id"], "name": row["large_unit_name"]}
        for row in results
    ]
    
    return ListResponse(items=items, total=len(items))

