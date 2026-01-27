from typing import List, Dict, Any, Optional, Tuple
from app.db.database import select_one, select_all, count, select_with_query, insert_one


def get_project_scope_id(project_id: int, user_id: int) -> Optional[int]:
    """프로젝트 ID로 scope_id 조회"""
    result = select_one(
        table="projects",
        where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
        columns="scope_id"
    )
    return result.get("scope_id") if result else None


def get_passage_info(passage_id: int, is_custom: bool, user_id: int = None) -> Optional[Dict[str, Any]]:
    """지문 정보 조회 (원본 또는 커스텀)"""
    if is_custom:
        return select_one(
            table="passage_custom",
            where={"custom_passage_id": passage_id, "user_id": user_id, "is_deleted": False}
        )
    else:
        return select_one(
            table="passages",
            where={"passage_id": passage_id}
        )


def create_custom_passage(data: Dict[str, Any]) -> int:
    """커스텀 지문 생성"""
    return insert_one("passage_custom", data)


def get_original_passages_paginated(scope_id: int) -> Tuple[List[Dict[str, Any]], int]:
    """범위(scope_id)에 해당하는 원본 지문 목록(50자 절삭)과 총 개수 반환"""
    columns = """
        passage_id as id,
        title,
        auth,
        CASE 
            WHEN CHAR_LENGTH(context) > 50 THEN CONCAT(LEFT(context, 50), '...') 
            ELSE context 
        END as content,
        scope_id,
        0 as is_custom
    """
    items = select_all(
        table="passages",
        columns=columns,
        where={"scope_id": scope_id},
        order_by="passage_id DESC"
    )
    
    return items, len(items)

def get_custom_passages_paginated(scope_id: int, user_id: int) -> Tuple[List[Dict[str, Any]], int]:
    """범위(scope_id)와 사용자 ID에 해당하는 커스텀 지문 목록(50자 절삭)과 총 개수 반환"""
    # 1. 목록 조회
    query = """
        SELECT 
            custom_passage_id as id,
            custom_title,
            title,
            auth,
            CASE 
                WHEN CHAR_LENGTH(context) > 50 THEN CONCAT(LEFT(context, 50), '...') 
                ELSE context 
            END as content,
            
            1 as is_custom
        FROM passage_custom
        WHERE scope_id = %s AND user_id = %s AND IFNULL(is_use, 1) = 1
        ORDER BY custom_passage_id DESC
    """
    items = select_with_query(query, (scope_id, user_id))

    return items, len(items)
