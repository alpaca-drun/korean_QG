from fastapi import APIRouter, HTTPException
from app.schemas.curriculum import LargeUnitResponse, ListResponse

router = APIRouter()


# 더미 데이터 (추후 DB 조회로 변경 예정)
DUMMY_LARGE_UNITS = [
    {"id": 1, "name": "수와 연산", "description": "수와 연산에 대한 대단원"},
    {"id": 2, "name": "도형", "description": "도형에 대한 대단원"},
    {"id": 3, "name": "측정", "description": "측정에 대한 대단원"},
]


@router.get(
    "",
    response_model=ListResponse,
    summary="대단원 리스트 조회",
    description="모든 대단원 리스트를 조회합니다. 드롭다운 선택용으로 사용됩니다.",
    tags=["메타데이터"]
)
async def get_large_units():
    """
    대단원 리스트를 반환합니다.
    
    - **id**: 대단원 고유 ID
    - **name**: 대단원 이름
    - **description**: 대단원 설명
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB 조회로 변경
    return ListResponse(items=DUMMY_LARGE_UNITS, total=len(DUMMY_LARGE_UNITS))


@router.get(
    "/{large_unit_id}",
    response_model=LargeUnitResponse,
    summary="대단원 상세 조회",
    description="특정 대단원의 상세 정보를 조회합니다.",
    tags=["메타데이터"]
)
async def get_large_unit(large_unit_id: int):
    """
    대단원 ID로 특정 대단원의 상세 정보를 반환합니다.
    
    - **large_unit_id**: 대단원 ID
    """
    # TODO: DB 조회로 변경
    for unit in DUMMY_LARGE_UNITS:
        if unit["id"] == large_unit_id:
            return LargeUnitResponse(**unit)
    
    raise HTTPException(
        status_code=404,
        detail=f"대단원 ID {large_unit_id}를 찾을 수 없습니다."
    )

