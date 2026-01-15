from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.curriculum import ListResponse
from app.utils.dependencies import get_current_user
from app.db.database import select_all, search


router = APIRouter()


@router.get(
    "/projects",
    response_model=ListResponse,
    summary="프로젝트 리스트 조회",
    description="사용자의 프로젝트 리스트를 조회합니다.",
    tags=["대시보드"]
) 
async def get_projects(current_user_id: str = Depends(get_current_user)):
    """
    현재 로그인한 사용자의 프로젝트 목록을 조회합니다.
    """
    user_id = int(current_user_id)
    
    try:
        # DB에서 프로젝트 조회
        projects = select_all(
            table="projects",
            where={"user_id": user_id, "is_deleted": False},
            order_by="created_at DESC"
        )
        
        if not projects:
            raise HTTPException(
                status_code=404,
                detail="프로젝트를 찾을 수 없습니다."
            )
        
        # 응답 형식에 맞게 변환
        items = []
        for p in projects:
            items.append({
                "id": p["project_id"],
                "user_id": p["user_id"],
                "name": p["project_name"],
                "status": p["status"],
                "created_at": p["created_at"].isoformat() if p.get("created_at") else None,
                "updated_at": p["updated_at"].isoformat() if p.get("updated_at") else None,
            })
        
        return ListResponse(items=items, total=len(items))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"프로젝트 조회 중 오류가 발생했습니다: {str(e)}"
        )

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
    user_id = int(current_user_id)
    
    try:
        # DB에서 프로젝트 검색
        projects = search(
            table="projects",
            search_columns=["project_name"],
            keyword=keyword,
            where={"user_id": user_id, "is_deleted": False},
            order_by="created_at DESC"
        )
        
        if not projects:
            raise HTTPException(
                status_code=404,
                detail="프로젝트를 찾을 수 없습니다."
            )
        
        # 응답 형식에 맞게 변환
        items = []
        for p in projects:
            items.append({
                "id": p["project_id"],
                "user_id": p["user_id"],
                "name": p["project_name"],
                "status": p["status"],
                "created_at": p["created_at"].isoformat() if p.get("created_at") else None,
                "updated_at": p["updated_at"].isoformat() if p.get("updated_at") else None,
            })
        
        return ListResponse(items=items, total=len(items))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"프로젝트 검색 중 오류가 발생했습니다: {str(e)}"
        )
