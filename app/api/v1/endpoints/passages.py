from fastapi import APIRouter, HTTPException, Query
from app.schemas.curriculum import PassageResponse, ListResponse

router = APIRouter()


# 더미 데이터 (추후 DB 조회로 변경 예정)
DUMMY_PASSAGES = [
    {"id": 1, "achievement_standard_id": 1, "title": "자연수의 덧셈 문제 1", "content": "3 + 5 = ?", "description": "자연수 덧셈 지문 1"},
    {"id": 2, "achievement_standard_id": 1, "title": "자연수의 덧셈 문제 2", "content": "7 + 8 = ?", "description": "자연수 덧셈 지문 2"},
    {"id": 3, "achievement_standard_id": 2, "title": "덧셈의 성질 문제", "content": "덧셈의 교환법칙을 설명하시오.", "description": "덧셈 성질 지문"},
    {"id": 4, "achievement_standard_id": 3, "title": "자연수의 뺄셈 문제", "content": "10 - 4 = ?", "description": "자연수 뺄셈 지문"},
    {"id": 5, "achievement_standard_id": 4, "title": "평면도형 문제", "content": "삼각형의 성질을 설명하시오.", "description": "평면도형 지문"},
]


@router.get(
    "",
    response_model=ListResponse,
    summary="지문 리스트 조회",
    description="특정 성취기준에 해당하는 지문 리스트를 조회합니다.",
    tags=["지문"]
)
async def get_passages(
    achievement_standard_id: int = Query(..., description="성취기준 ID", example=1)
):
    """
    성취기준 ID를 기반으로 지문 리스트를 반환합니다.
    
    - **achievement_standard_id**: 성취기준 ID (필수)
    - **id**: 지문 고유 ID
    - **title**: 지문 제목
    - **content**: 지문 내용
    - **description**: 지문 설명
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB 조회로 변경
    filtered_passages = [
        passage for passage in DUMMY_PASSAGES 
        if passage["achievement_standard_id"] == achievement_standard_id
    ]
    
    if not filtered_passages:
        raise HTTPException(
            status_code=404,
            detail=f"성취기준 ID {achievement_standard_id}에 해당하는 지문을 찾을 수 없습니다."
        )
    
    return ListResponse(items=filtered_passages, total=len(filtered_passages))


@router.get(
    "/{passage_id}",
    response_model=PassageResponse,
    summary="지문 상세 조회",
    description="특정 지문의 상세 정보를 조회합니다.",
    tags=["지문"]
)
async def get_passage(passage_id: int):
    """
    지문 ID로 특정 지문의 상세 정보를 반환합니다.
    
    - **passage_id**: 지문 ID
    """
    # TODO: DB 조회로 변경
    for passage in DUMMY_PASSAGES:
        if passage["id"] == passage_id:
            return PassageResponse(**passage)
    
    raise HTTPException(
        status_code=404,
        detail=f"지문 ID {passage_id}를 찾을 수 없습니다."
    )

