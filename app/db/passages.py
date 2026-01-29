from typing import List, Dict, Any, Optional, Tuple
from app.db.database import select_one, select_all, count, select_with_query, insert_one, update_with_query


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
        # passage_custom 테이블은 is_deleted 대신 is_use 필드를 사용함 (또는 필터링 없음)
        return select_one(
            table="passage_custom",
            where={"custom_passage_id": passage_id, "user_id": user_id, "is_use": True}
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




def update_passage_use(project_id: int, is_modified: int, passage_id: int = None):
    """
    프로젝트 소스 구성에서 지문 사용 상태(is_modified, passage_id) 업데이트
    passage_id가 주어지면 passage_id까지 수정, 아니면 is_modified만 수정
    기존 데이터가 없으면 insert_one을 수행함
    """
    try:
        # 기존 데이터 존재 여부 확인
        config = select_one("project_source_config", where={"project_id": project_id})
        
        if not config:
            # 존재하지 않으면 INSERT
            data = {
                "project_id": project_id,
                "is_modified": is_modified
            }
            if passage_id is not None:
                if is_modified == 1:
                    data["custom_passage_id"] = passage_id
                else:
                    data["passage_id"] = passage_id
            
            return insert_one("project_source_config", data)
        else:
            # 존재하면 UPDATE
            if passage_id is not None and is_modified == 1:
                query = """
                    UPDATE project_source_config 
                    SET 
                        is_modified = %s,
                        custom_passage_id = %s,
                        updated_at = NOW()
                    WHERE project_id = %s
                """
                params = (is_modified, passage_id, project_id)
            elif passage_id is not None and is_modified == 0:
                query = """
                    UPDATE project_source_config 
                    SET 
                        is_modified = %s,
                        passage_id = %s,
                        updated_at = NOW()
                    WHERE project_id = %s
                """
                params = (is_modified, passage_id, project_id)
            else:
                query = """
                    UPDATE project_source_config 
                    SET 
                        is_modified = %s,
                        updated_at = NOW()
                    WHERE project_id = %s
                """
                params = (is_modified, project_id)
            return update_with_query(query, params)
    except Exception as e:
        print(f"Error updating passage use: {e}")
        return False


def update_project_config_status(project_id: int, is_modified: int, custom_passage_id: int):
    """프로젝트 설정 상태 업데이트 (KST 기준)"""
    try:
        query = """
            UPDATE project_source_config 
            SET 
                is_modified = %s, 
                custom_passage_id = %s,
                updated_at = NOW() 
            WHERE 
            project_id = %s
        """
        return update_with_query(query, (is_modified, custom_passage_id, project_id))
    except Exception as e:
        print(f"Error updating project config status: {e}")
        return False


def search_passages_keyword(keyword: str, user_id: int, source_type: Optional[int] = None) -> List[Dict[str, Any]]:
    """키워드를 통한 지문 검색 (원본 및 커스텀)"""
    search_pattern = f"%{keyword}%"
    
    if source_type == 0:  # 원본 지문만
        query = """
            SELECT passage_id as id, title, auth as auth, 
                   CASE 
                       WHEN CHAR_LENGTH(context) > 50 THEN CONCAT(SUBSTRING(context, 1, 50), '...')
                       ELSE context
                   END as content,
                   NULL as description, scope_id, NULL as achievement_standard_id,
                   0 as is_custom
            FROM passages
            WHERE title LIKE %s OR context LIKE %s
            ORDER BY id DESC
        """
        return select_with_query(query, (search_pattern, search_pattern))
        
    elif source_type == 1:  # 커스텀 지문만
        query = """
            SELECT custom_passage_id as id, 
                   COALESCE(custom_title, title) as title, 
                   auth as auth,
                   CASE 
                       WHEN CHAR_LENGTH(context) > 50 THEN CONCAT(SUBSTRING(context, 1, 50), '...')
                       ELSE context
                   END as content,
                   NULL as description, scope_id, NULL as achievement_standard_id,
                   1 as is_custom
            FROM passage_custom
            WHERE user_id = %s AND IFNULL(is_use, 1) = 1 AND (custom_title LIKE %s OR title LIKE %s OR context LIKE %s)
            ORDER BY id DESC
        """
        return select_with_query(query, (user_id, search_pattern, search_pattern, search_pattern))
        
    else:  # 전체 (원본 + 커스텀)
        query = """
            SELECT 
                passage_id as id, 
                title, 
                auth as auth,
                CASE 
                    WHEN CHAR_LENGTH(context) > 50 THEN CONCAT(SUBSTRING(context, 1, 50), '...')
                    ELSE context
                END as content, 

                scope_id, 

                0 as is_custom,
                NULL as created_at
            FROM passages
            WHERE title LIKE %s OR context LIKE %s
            UNION ALL
            
            SELECT 
                custom_passage_id as id, 
                title as title, 
                auth as auth,
                CASE 
                    WHEN CHAR_LENGTH(context) > 50 THEN CONCAT(SUBSTRING(context, 1, 50), '...')
                    ELSE context
                END as content,

                scope_id, 

                1 as is_custom,
                created_at
            FROM passage_custom
            WHERE user_id = %s AND IFNULL(is_use, 1) = 1 AND (custom_title LIKE %s OR title LIKE %s OR context LIKE %s)
            ORDER BY is_custom ASC, created_at ASC
        """
        return select_with_query(query, (search_pattern, search_pattern, user_id, search_pattern, search_pattern, search_pattern))
