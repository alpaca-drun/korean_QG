## 로그인 등 인증에 사용되는 함수들

from app.db.database import (
    select_one, select_all, select_with_query, count, search,
    insert_one, insert_many,
    update,
    delete, soft_delete
)




def get_all_users_with_usage():
    """사용자 목록과 토큰 사용량 조회"""
    query = """
        SELECT 
            u.user_id, 
            u.email, 
            u.name, 
            u.role, 
            u.is_active, 
            u.created_at,
            u.subject,
            u.memo,
            COALESCE(SUM(psc.input_tokens), 0) as input_tokens,
            COALESCE(SUM(psc.output_tokens), 0) as output_tokens
        FROM users u
        LEFT JOIN projects p ON u.user_id = p.user_id
        LEFT JOIN project_source_config psc ON p.project_id = psc.project_id
        GROUP BY u.user_id
        ORDER BY u.created_at DESC
    """
    users = select_with_query(query)
    return users


def update_user_role(user_id: int, role: str):
    """사용자 권한 업데이트"""
    result = update(
        table="users",
        data={"role": role},
        where={"user_id": user_id}
    )
    return result > 0


def update_user_active_status(user_id: int, is_active: bool):
    """사용자 권한 업데이트"""
    result = update(
        table="users",
        data={"is_active": is_active},
        where={"user_id": user_id}
    )
    return result > 0


def update_user_memo(user_id: int, memo: str):
    """사용자 메모 업데이트"""
    result = update(
        table="users",
        data={"memo": memo},
        where={"user_id": user_id}
    )
    return result > 0