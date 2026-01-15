from fastapi import APIRouter, HTTPException, Query
from app.schemas.curriculum import AchievementStandardResponse, ListResponse

router = APIRouter()


# 더미 데이터 (추후 DB 조회로 변경 예정)
DUMMY_ACHIEVEMENT_STANDARDS = [
    {"id": 1, "small_unit_id": 1, "code": "1-1-1", "content": "자연수의 덧셈을 이해하고 계산할 수 있다.", "description": "자연수 덧셈 성취기준"},
    {"id": 2, "small_unit_id": 1, "code": "1-1-2", "content": "덧셈의 성질을 이해하고 활용할 수 있다.", "description": "덧셈 성질 성취기준"},
    {"id": 3, "small_unit_id": 2, "code": "1-2-1", "content": "자연수의 뺄셈을 이해하고 계산할 수 있다.", "description": "자연수 뺄셈 성취기준"},
    {"id": 4, "small_unit_id": 3, "code": "2-1-1", "content": "평면도형의 성질을 이해하고 설명할 수 있다.", "description": "평면도형 성취기준"},
]


@router.get(
    "",
    response_model=ListResponse,
    summary="성취기준 리스트 조회",
    description="특정 소단원에 속한 성취기준 리스트를 조회합니다.",
)
async def get_achievement_standards(
    small_unit_id: int = Query(..., description="소단원 ID", example=1)
):
    """
    소단원 ID를 기반으로 성취기준 리스트를 반환합니다.
    
    - **small_unit_id**: 소단원 ID (필수)
    - **id**: 성취기준 고유 ID
    - **code**: 성취기준 코드
    - **content**: 성취기준 내용
    - **description**: 성취기준 설명
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB 조회로 변경
    filtered_standards = [
        standard for standard in DUMMY_ACHIEVEMENT_STANDARDS 
        if standard["small_unit_id"] == small_unit_id
    ]
    
    if not filtered_standards:
        raise HTTPException(
            status_code=404,
            detail=f"소단원 ID {small_unit_id}에 해당하는 성취기준을 찾을 수 없습니다."
        )
    
    return ListResponse(items=filtered_standards, total=len(filtered_standards))


@router.get(
    "/{achievement_standard_id}",
    response_model=AchievementStandardResponse,
    summary="성취기준 상세 조회",
    description="특정 성취기준의 상세 정보를 조회합니다.",
)
async def get_achievement_standard(achievement_standard_id: int):
    """
    성취기준 ID로 특정 성취기준의 상세 정보를 반환합니다.
    
    - **achievement_standard_id**: 성취기준 ID
    """
    # TODO: DB 조회로 변경
    for standard in DUMMY_ACHIEVEMENT_STANDARDS:
        if standard["id"] == achievement_standard_id:
            return AchievementStandardResponse(**standard)
    
    raise HTTPException(
        status_code=404,
        detail=f"성취기준 ID {achievement_standard_id}를 찾을 수 없습니다."
    )

