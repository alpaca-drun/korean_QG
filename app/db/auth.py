## 로그인 등 인증에 사용되는 함수들

from app.db.database import (
    select_one, select_all, select_with_query, count, search,
    insert_one, insert_many,
    update,
    delete, soft_delete
)

def get_user_by_id(user_id: int):
    """사용자 ID로 조회"""
    user = select_one("users", {"user_id": user_id})
    return user


def get_user_by_login_id(login_id: str):
    """로그인 아이디로 사용자 조회 (로그인 용으로 사용)"""
    user = select_one(
        "users",
        where={"login_id": login_id},
        columns="user_id, login_id, password_hash, name, role, is_active"
    )
    return user


def get_users():
    """사용자 목록 조회 (비밀번호 제외)"""
    users = select_all(
        "users",
        columns="user_id, email, name, role, is_active, created_at"
    )
    return users


def update_user_password(user_id: int, password_hash: str) -> bool:
    """사용자 비밀번호 변경"""
    result = update(
        "users",
        {"password_hash": password_hash},
        {"user_id": user_id}
    )
    return result > 0
