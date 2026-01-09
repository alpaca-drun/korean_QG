from fastapi import APIRouter, HTTPException, Query
from app.schemas.curriculum import SmallUnitResponse, ListResponse

router = APIRouter()


# 더미 데이터 (추후 DB 조회로 변경 예정)
DUMMY_SMALL_UNITS = [
    {"id": 1, "large_unit_id": 1, "name": "자연수의 덧셈", "description": "자연수의 덧셈에 대한 소단원"},
    {"id": 2, "large_unit_id": 1, "name": "자연수의 뺄셈", "description": "자연수의 뺄셈에 대한 소단원"},
    {"id": 3, "large_unit_id": 2, "name": "평면도형", "description": "평면도형에 대한 소단원"},
    {"id": 4, "large_unit_id": 2, "name": "입체도형", "description": "입체도형에 대한 소단원"},
]


@router.get(
    "",
    response_model=ListResponse,
    summary="소단원 리스트 조회",
    description="특정 대단원에 속한 소단원 리스트를 조회합니다.",
    tags=["소단원"]
)
async def get_small_units(
    large_unit_id: int = Query(..., description="대단원 ID", example=1)
):
    """
    대단원 ID를 기반으로 소단원 리스트를 반환합니다.
    
    - **large_unit_id**: 대단원 ID (필수)
    - **id**: 소단원 고유 ID
    - **name**: 소단원 이름
    - **description**: 소단원 설명
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB 조회로 변경
    filtered_units = [
        unit for unit in DUMMY_SMALL_UNITS 
        if unit["large_unit_id"] == large_unit_id
    ]
    
    if not filtered_units:
        raise HTTPException(
            status_code=404,
            detail=f"대단원 ID {large_unit_id}에 해당하는 소단원을 찾을 수 없습니다."
        )
    
    return ListResponse(items=filtered_units, total=len(filtered_units))


@router.get(
    "/{small_unit_id}",
    response_model=SmallUnitResponse,
    summary="소단원 상세 조회",
    description="특정 소단원의 상세 정보를 조회합니다.",
    tags=["소단원"]
)
async def get_small_unit(small_unit_id: int):
    """
    소단원 ID로 특정 소단원의 상세 정보를 반환합니다.
    
    - **small_unit_id**: 소단원 ID
    """
    # TODO: DB 조회로 변경
    for unit in DUMMY_SMALL_UNITS:
        if unit["id"] == small_unit_id:
            return SmallUnitResponse(**unit)
    
    raise HTTPException(
        status_code=404,
        detail=f"소단원 ID {small_unit_id}를 찾을 수 없습니다."
    )


