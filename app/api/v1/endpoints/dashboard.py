from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.curriculum import ListResponse
from app.utils.dependencies import get_current_user 


router = APIRouter()


# 더미 데이터 (추후 DB 조회로 변경 예정)
DUMMY_PROJECTS = [
    {"id": 1,"user_id": 1, "name": "프로젝트 1", "description": "프로젝트 1에 대한 설명"},
    {"id": 11,"user_id": 1, "name": "프로젝트 11", "description": "프로젝트 11에 대한 설명"},
    {"id": 2, "user_id": 2, "name": "프로젝트 2", "description": "프로젝트 2에 대한 설명"},
    {"id": 22, "user_id": 2, "name": "프로젝트 22", "description": "프로젝트 22에 대한 설명"},
    {"id": 3, "user_id": 3, "name": "프로젝트 3", "description": "프로젝트 3에 대한 설명"},
    {"id": 33, "user_id": 3, "name": "프로젝트 33", "description": "프로젝트 33에 대한 설명"},
]


@router.get(
    "/projects",
    response_model=ListResponse,
    summary="프로젝트 리스트 조회",
    description="모든 프로젝트 리스트를 조회합니다.",
    tags=["대시보드"]
) 
async def get_projects(current_user_id: str = Depends(get_current_user)):
    user_id = int(current_user_id)

    filtered_projects = [
        project for project in DUMMY_PROJECTS
        if project["user_id"] == user_id
    ]

    if not filtered_projects:
        raise HTTPException(
            status_code=404,
            detail="프로젝트를 찾을 수 없습니다."
        )

    return ListResponse(items=filtered_projects, total=len(filtered_projects))

@router.get(
    "/keyword",
    response_model=ListResponse,
    summary="키워드를 통한 프로젝트 검색",
    description="키워드를 통한 프로젝트를 검색합니다.",
    tags=["대시보드"]
)
async def get_projects_by_keyword(
    current_user_id: str = Depends(get_current_user),
    keyword: str = Query(..., description="키워드", example="프로젝트 1")
):
    """
    키워드를 통한 프로젝트를 검색합니다.
    """
    # TODO: DB 조회로 변경
    
    user_id = int(current_user_id)
    
    filtered_projects = [
        project for project in DUMMY_PROJECTS
        if project["user_id"] == user_id
        and (keyword in project["name"] or keyword.lower() in project["name"].lower() or keyword in project["description"] or keyword.lower() in project["description"].lower())
    ]

    if not filtered_projects:
        raise HTTPException(
            status_code=404,
            detail="프로젝트를 찾을 수 없습니다."
        )

    return ListResponse(items=filtered_projects, total=len(filtered_projects))
