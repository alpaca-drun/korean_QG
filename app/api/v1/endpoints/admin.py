from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body


from app.utils.dependencies import get_current_user
from app.core.config import settings
from app.core.logger import logger
from app.db.admin import *
from app.schemas.admin import UserListItem, UserUpdateRoleRequest, UserUpdateStatusRequest, UserUpdateMemoRequest


router = APIRouter()


@router.get(
    "/list",
    response_model=List[UserListItem],
    summary="사용자 목록 조회",
    description="모든 사용자의 목록과 토큰 사용량, 예상 비용을 조회합니다."
)
async def get_users_list(
    exchange_rate: Optional[float] = 1450.0,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    관리자 페이지용 사용자 목록 조회
    """
    # TODO: 관리자 권한 체크 로직 추가 필요
    # if current_user.get("role") != "admin":
    #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    user_id, role = user_data
    users = get_all_users_with_usage()
    result = []

    if role != "master":
        raise HTTPException(status_code=403, detail="관리자 권한(Master)이 필요합니다.")

    for u in users:
        input_t = int(u.get("input_tokens") or 0)
        output_t = int(u.get("output_tokens") or 0)
        
        # 비용 계산 (Gemini Pro 기준 근사치: $0.50/1M input, $1.50/1M output)
        # 실제 비용 정책에 따라 수정 필요
        cost_usd = (input_t * 0.5 + output_t * 3) / 1_000_000
        cost_won = int(cost_usd * exchange_rate) # 환율 적용 (기본값 1450원)
        
        
        # Team 매핑 (subject 컬럼 사용)
        subject = u.get("subject") or ""

        
        result.append(UserListItem(
            id=u["user_id"],
            name=u["name"],
            email=u.get("email"),
            subject=subject,
            team_name=u.get("team_name"), 
            role=u.get("role"),
            input_tokens=input_t,
            output_tokens=output_t,
            price_dollers=round(cost_usd, 4),
            price_won=cost_won,
            status=u.get("is_active"),
            memo=u.get("memo")
        ))
        
    return result

@router.patch(
    "/role/{user_id}",
    response_model=dict,
    summary="접근 권한 변경",
    description="사용자 ID를 기준으로 사용자의 접근 권한을 변경합니다."

)
async def patch_user_role(
    user_id: int = Path(..., description="사용자 ID"),
    request: UserUpdateRoleRequest = Body(...),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    """
    current_user_id, current_role = user_data
    if current_role != "master":
        raise HTTPException(status_code=403, detail="관리자 권한(Master)이 필요합니다.")

    user_info = select_one(
        table="users",
        where={"user_id": user_id},
        columns="role"
    )
    if not user_info:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    result = update_user_role(user_id=user_id, role=request.role)
    if result:
        return {"message": "접근 권한이 변경되었습니다."}
    else:
        raise HTTPException(status_code=400, detail="접근 권한 변경에 실패하였습니다.")

@router.patch(
    "/active_status/{user_id}",
    response_model=dict,
    summary="활성화 상태 변경",
    description="사용자 ID를 기준으로 사용자의 활성화 상태를 변경합니다."

)
async def patch_user_active_status(
    user_id: int = Path(..., description="사용자 ID"),
    request: UserUpdateStatusRequest = Body(...),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    """
    current_user_id, current_role = user_data
    if current_role != "master":
        raise HTTPException(status_code=403, detail="관리자 권한(Master)이 필요합니다.")

    user_info = select_one(
        table="users",
        where={"user_id": user_id},
        columns="role"
    )
    if not user_info:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    result = update_user_active_status(user_id=user_id, is_active=request.is_active)
    if result:
        return {"message": "활성화 상태가 변경되었습니다."}
    else:
        raise HTTPException(status_code=400, detail="활성화 상태 변경에 실패하였습니다.")

@router.patch(
    "/memo/{user_id}",
    response_model=dict,
    summary="메모 수정",
    description="사용자 ID를 기준으로 사용자의 메모를 수정합니다."
)
async def patch_user_memo(
    user_id: int = Path(..., description="사용자 ID"),
    request: UserUpdateMemoRequest = Body(...),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    """
    current_user_id, current_role = user_data
    if current_role != "master":
        raise HTTPException(status_code=403, detail="관리자 권한(Master)이 필요합니다.")

    user_info = select_one(
        table="users",
        where={"user_id": user_id},
        columns="role"
    )
    if not user_info:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    result = update_user_memo(user_id=user_id, memo=request.memo)
    if result:
        return {"message": "메모가 수정되었습니다."}
    else:
        raise HTTPException(status_code=400, detail="메모 수정에 실패하였습니다.")



# =============\


