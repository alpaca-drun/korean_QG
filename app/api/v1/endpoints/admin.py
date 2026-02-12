from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body


from app.utils.dependencies import get_current_user
from app.core.config import settings
from app.core.logger import logger
from app.db.admin import *
from app.schemas.admin import UserListItem,UserListResponse, UserUpdateRoleRequest, UserUpdateStatusRequest, UserUpdateMemoRequest
import requests


router = APIRouter()


@router.get(
    "/list",
    response_model=UserListResponse,
    summary="사용자 목록 조회",
    description="모든 사용자의 목록과 토큰 사용량, 예상 비용을 조회합니다. 날짜 필터링 가능 (YYYY-MM-DD)"
)
async def get_users_list(
    exchange_rate: Optional[float] = Query(None, description="환율"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    관리자 페이지용 사용자 목록 조회
    """
    # TODO: 관리자 권한 체크 로직 추가 필요
    # if current_user.get("role") != "admin":
    #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    user_id, role = user_data
    
    # 날짜 포맷 검증 (간단하게)
    if start_date and len(start_date) != 10:
        start_date = None
    if end_date and len(end_date) != 10:
        end_date = None
        
    # 종료 날짜가 있으면 23:59:59까지로 설정하기 위해 하루 더하거나 시간을 붙여야 하는데,
    # DB 쿼리에서 BETWEEN은 inclusive이므로 문자열 비교 시 시간까지 고려해야 함.
    # 여기서는 입력받은 YYYY-MM-DD를 그대로 넘기되, DB 쿼리에서 처리하거나
    # 단순 문자열 비교를 위해 end_date에 " 23:59:59"를 붙여주는 것이 좋음.
    if end_date:
        end_date = f"{end_date} 23:59:59"
    if start_date:
        start_date = f"{start_date} 00:00:00"

    users = get_all_users_with_usage(start_date, end_date)
    result = []

    if role != "master":
        raise HTTPException(status_code=403, detail="관리자 권한(Master)이 필요합니다.")

    if not exchange_rate:
        target_date = datetime.now()
        # 최대 10일 전까지만 조회 (무한 루프 방지)
        for _ in range(10):
            search_date = target_date.strftime("%Y%m%d")
            try:
                response = requests.get(f"https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON?authkey=cSoiQgL0NfNwRz9uuEpFDykoEA73y9rV&searchdate={search_date}&data=AP01", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    # 데이터가 비어있지 않고 리스트인 경우
                    if isinstance(data, list) and data:
                        for item in data:
                            if item.get("cur_unit") == "USD":
                                exchange_rate = float(item.get("deal_bas_r").replace(",", ""))
                                break
                        
                        # 환율을 찾았으면 루프 종료
                        if exchange_rate:
                            break
            except Exception as e:
                logger.error(f"환율 정보 조회 중 오류 발생 ({search_date}): {e}")
            
            # 실패했거나 데이터가 없으면 하루 전으로 이동
            target_date -= timedelta(days=1)
            
        # 10일간 조회해도 실패하면 기본값 사용
        if not exchange_rate:
            logger.warning("환율 API 응답에서 USD 정보를 찾을 수 없습니다. 기본값을 사용합니다.")
            exchange_rate = 1450.0

    print(f"exchange_rate: {exchange_rate}")
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
            memo=u.get("memo"),
            updated_at=u.get("updated_at").strftime("%Y-%m-%d %H:%M:%S") if u.get("updated_at") else None
        ))

    return UserListResponse(items=result, exchange_rate=exchange_rate)

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


