from typing import List, Dict, Any, Optional, Tuple
from app.db.database import select_one, select_all, count, select_with_query


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
