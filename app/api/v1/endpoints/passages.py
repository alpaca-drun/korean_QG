from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.curriculum import (
    PassageResponse, 
    ListResponse,
    PassageCreateRequest,
    PassageUpdateRequest,
    PassageCreateFromSourceRequest
)

router = APIRouter()


# 더미 데이터 (추후 DB 조회로 변경 예정)
DUMMY_PASSAGES = [
    {"id": 1, "achievement_standard_id": 1, "title": "자연수의 덧셈 문제 1", "content": "3 + 5 = ?", "description": "자연수 덧셈 지문 1", "source_passage_id": None},
    {"id": 2, "achievement_standard_id": 1, "title": "자연수의 덧셈 문제 2", "content": "7 + 8 = ?", "description": "자연수 덧셈 지문 2", "source_passage_id": None},
    {"id": 3, "achievement_standard_id": 2, "title": "덧셈의 성질 문제", "content": "덧셈의 교환법칙을 설명하시오.", "description": "덧셈 성질 지문", "source_passage_id": None},
    {"id": 4, "achievement_standard_id": 3, "title": "자연수의 뺄셈 문제", "content": "10 - 4 = ?", "description": "자연수 뺄셈 지문", "source_passage_id": None},
    {"id": 5, "achievement_standard_id": 4, "title": "평면도형 문제", "content": "삼각형의 성질을 설명하시오.", "description": "평면도형 지문", "source_passage_id": None},
]

# 리스트 조회 시 content 미리보기 최대 길이
CONTENT_PREVIEW_LENGTH = 50


def truncate_passage_content(passage: dict, max_length: int = CONTENT_PREVIEW_LENGTH) -> dict:
    """
    지문의 content를 지정된 길이로 자릅니다.
    
    Args:
        passage: 지문 딕셔너리
        max_length: 최대 길이 (기본값: 50자)
        
    Returns:
        content가 잘린 지문 딕셔너리 (원본은 수정하지 않음)
    """
    truncated = passage.copy()
    content = truncated["content"]
    
    if len(content) > max_length:
        truncated["content"] = content[:max_length] + "..."
    
    return truncated


@router.get(
    "/list",
    response_model=ListResponse,
    summary="지문 리스트 조회",
    description="특정 성취기준에 해당하는 지문 리스트를 조회합니다.",
)
async def get_passages(
    achievement_standard_id: int = Query(..., description="성취기준 ID", example=1),text_type:int = Query(..., description="텍스트 타입", example=1)
):
    """
    성취기준 ID를 기반으로 지문 리스트를 반환합니다.
    
    - **achievement_standard_id**: 성취기준 ID (필수)
    - **id**: 지문 고유 ID
    - **title**: 지문 제목
    - **content**: 지문 내용 미리보기 (50자로 제한, 전체 내용은 상세/전문 조회 사용)
    - **description**: 지문 설명
    
    **참고**: 리스트 조회에서는 content가 50자로 제한됩니다.
    전체 내용이 필요한 경우 `/passages/{passage_id}` 또는 `/passages/full_content/{passage_id}`를 사용하세요.
    
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
    
    # 리스트 조회에서는 content를 50자로 제한
    truncated_passages = [truncate_passage_content(p) for p in filtered_passages]
    
    return ListResponse(items=truncated_passages, total=len(truncated_passages))


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


@router.get(
    "/search_keyword/{keyword}",
    response_model=ListResponse,
    summary="키워드를 통한 지문 검색",
    description="특정 키워드를 포함하는 지문을 검색합니다.",
    tags=["지문"]
)
async def search_passages_by_keyword(keyword: str):
    """
    키워드를 포함하는 모든 지문을 반환합니다.
    
    - **keyword**: 검색할 키워드
    
    지문의 제목(title), 내용(content), 설명(description)에서 키워드를 검색합니다.
    
    **참고**: 리스트 조회에서는 content가 50자로 제한됩니다.
    전체 내용이 필요한 경우 `/passages/{passage_id}` 또는 `/passages/full_content/{passage_id}`를 사용하세요.
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB 조회로 변경
    # 제목, 내용, 설명 중 하나라도 키워드를 포함하는 지문 검색
    matched_passages = [
        passage for passage in DUMMY_PASSAGES
        if keyword.lower() in passage["title"].lower() 
        or keyword.lower() in passage["content"].lower()
        or keyword.lower() in passage["description"].lower()
    ]
    
    if not matched_passages:
        raise HTTPException(
            status_code=404,
            detail=f"키워드 '{keyword}'를 포함하는 지문을 찾을 수 없습니다."
        )
    
    # 리스트 조회에서는 content를 50자로 제한
    truncated_passages = [truncate_passage_content(p) for p in matched_passages]
    
    return ListResponse(items=truncated_passages, total=len(truncated_passages))


@router.get(
    "/full_content",
    response_model=PassageResponse,
    summary="지문 전문",
    description="특정 지문의 전문을 조회합니다.",
    tags=["지문"]
)
async def get_passage_content(
    passage_id: int = Query(..., description="지문 ID", example=1)
):
    """
    지문 ID를 기반으로 지문의 전문을 조회합니다.
    
    - **passage_id**: 지문 ID
    
    추후 DB 조회로 변경 예정입니다.
    """
    # TODO: DB 조회로 변경
    for passage in DUMMY_PASSAGES:
        if passage["id"] == passage_id:
            return PassageResponse(**passage)

    raise HTTPException(
        status_code=404,
        detail=f"지문 ID {passage_id}의 전문을 찾을 수 없습니다."
    )



@router.post(
    "/create",
    response_model=PassageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 지문 생성",
    description="새로운 지문을 생성합니다.",
    tags=["지문"]
)
async def create_passage(request: PassageCreateRequest):
    """
    새로운 지문을 생성합니다.
    
    - **achievement_standard_id**: 성취기준 ID
    - **large_unit_id**:대단원
    - **small_unit_id**:소단원
    - **title**: 지문 제목
    - **content**: 지문 내용
    - **description**: 지문 설명 (선택사항)
    
    생성된 지문의 ID를 포함한 전체 정보를 반환합니다.
    
    추후 DB 저장으로 변경 예정입니다.
    """
    # TODO: DB에 저장
    # 새로운 ID 생성 (기존 최대 ID + 1)
    new_id = max([p["id"] for p in DUMMY_PASSAGES]) + 1 if DUMMY_PASSAGES else 1
    
    # 새로운 지문 생성
    new_passage = {
        "id": new_id,
        "achievement_standard_id": request.achievement_standard_id,
        "large_unit_id": request.large_unit_id,
        "small_unit_id": request.small_unit_id,
        "title": request.title,
        "content": request.content,
        "description": request.description
    }
    
    # 더미 데이터에 추가
    DUMMY_PASSAGES.append(new_passage)
    
    return PassageResponse(**new_passage)

@router.post(
    "/update/{passage_id}",
    response_model=PassageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="원본지문을 기반으로 지문 생성",
    description="원본지문을 기반으로 지문을 생성합니다.",
    tags=["지문"]
)
async def update_passage(passage_id: int, request: PassageCreateFromSourceRequest):
    """
    지문 ID를 기반으로 지문을 수정합니다.
    
    - **achievement_standard_id**: 성취기준 ID
    - **title**: 지문 제목
    - **content**: 지문 내용
    - **description**: 지문 설명 (선택사항)
    - **source_passage_id**: 원본 지문 ID (선택사항, 다른 지문 기반인 경우)
    
    생성된 지문의 ID를 포함한 전체 정보를 반환합니다.
    
    추후 DB 저장으로 변경 예정입니다.
    """
    # TODO: DB에 저장
    # source_passage_id가 제공된 경우 원본 지문 존재 여부 확인
    if request.source_passage_id is not None:
        source_exists = any(p["id"] == request.source_passage_id for p in DUMMY_PASSAGES)
        if not source_exists:
            raise HTTPException(
                status_code=404,
                detail=f"원본 지문 ID {request.source_passage_id}를 찾을 수 없습니다."
            )
    
    # 새로운 ID 생성 (기존 최대 ID + 1)
    new_id = max([p["id"] for p in DUMMY_PASSAGES]) + 1 if DUMMY_PASSAGES else 1
    
    # 새로운 지문 생성
    new_passage = {
        "id": new_id,
        "achievement_standard_id": request.achievement_standard_id,
        "title": request.title,
        "content": request.content,
        "description": request.description,
        "source_passage_id": request.source_passage_id
    }
    
    # 더미 데이터에 추가
    DUMMY_PASSAGES.append(new_passage)
    
    return PassageResponse(**new_passage)


@router.delete(
    "/{passage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="지문 삭제",
    description="사용자 리스트에 추가된 특정 지문을 삭제합니다.",
    tags=["지문"]
)
async def delete_passage(passage_id: int):
    """
    지문 ID를 기반으로 지문을 삭제합니다.
    
    - **passage_id**: 지문 ID (경로 파라미터)
    
    성공 시 204 No Content를 반환합니다.
    
    추후 DB 삭제로 변경 예정입니다.
    """
    # TODO: DB 삭제로 변경
    for i, passage in enumerate(DUMMY_PASSAGES):
        if passage["id"] == passage_id:
            DUMMY_PASSAGES.pop(i)
            return
    
    raise HTTPException(
        status_code=404,
        detail=f"지문 ID {passage_id}를 찾을 수 없습니다."
    )
