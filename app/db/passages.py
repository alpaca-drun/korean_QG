from typing import List, Dict, Any, Optional, Tuple
import json
from app.db.database import select_one, select_all, count, select_with_query, insert_one, update_with_query
from app.core.logger import logger


def get_scope_ids_by_achievement(achievement_standard_id: int, connection=None) -> List[int]:
    """
    achievement_standard_id로 scope_id 리스트를 조회합니다.
    project_scopes 테이블의 achievement_ids JSON 필드에서 찾습니다.
    """
    try:
        sql = """
            SELECT scope_id 
            FROM project_scopes
            WHERE JSON_CONTAINS(achievement_ids, %s)
        """
        # achievement_ids가 JSON 배열([1,5,12])이므로, 찾을 값은 스칼라(예: 1)로 전달해야 매칭됩니다.
        results = select_with_query(sql, (json.dumps(achievement_standard_id),), connection=connection)
        return [row['scope_id'] for row in results] if results else []
    except Exception as e:
        logger.warning("scope_id 조회 오류: %s", e, exc_info=True)
        return []


def get_project_scope_id(project_id: int, user_id: int, connection=None) -> Optional[int]:
    """프로젝트 ID로 scope_id 조회"""
    result = select_one(
        table="projects",
        where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
        columns="scope_id",
        connection=connection
    )
    return result.get("scope_id") if result else None


def get_passage_info(passage_id: int, is_custom: bool, user_id: int = None, connection=None) -> Optional[Dict[str, Any]]:
    """지문 정보 조회 (원본 또는 커스텀)"""
    if is_custom:
        # passage_custom 테이블은 is_deleted 대신 is_use 필드를 사용함 (또는 필터링 없음)
        return select_one(
            table="passage_custom",
            where={"custom_passage_id": passage_id, "user_id": user_id, "is_use": True},
            connection=connection
        )
    else:
        return select_one(
            table="passages",
            where={"passage_id": passage_id},
            connection=connection
        )


def create_custom_passage(data: Dict[str, Any], connection=None) -> int:
    """커스텀 지문 생성"""
    return insert_one("passage_custom", data, connection=connection)


def get_original_passages_paginated(scope_id: int, connection=None) -> Tuple[List[Dict[str, Any]], int]:
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
        order_by="passage_id DESC",
        connection=connection
    )
    
    return items, len(items)

def get_custom_passages_paginated(scope_id: int, user_id: int, connection=None) -> Tuple[List[Dict[str, Any]], int]:
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
    items = select_with_query(query, (scope_id, user_id), connection=connection)

    return items, len(items)




def update_passage_use(project_id: int, is_modified: int, passage_id: int = None, connection=None):
    """
    프로젝트 소스 구성에서 지문 사용 상태(is_modified, passage_id) 업데이트
    INSERT ON DUPLICATE KEY UPDATE 패턴으로 Race Condition 방지
    - project_id가 UNIQUE KEY이므로 동시 요청 시에도 안전하게 처리
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            # is_modified 값에 따라 passage_id 또는 custom_passage_id 컬럼 결정
            if passage_id is not None and is_modified == 1:
                # custom_passage_id 설정
                query = """
                    INSERT INTO project_source_config (project_id, is_modified, custom_passage_id, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE 
                        is_modified = VALUES(is_modified),
                        custom_passage_id = VALUES(custom_passage_id),
                        updated_at = NOW()
                """
                params = (project_id, is_modified, passage_id)
            elif passage_id is not None and is_modified == 0:
                # passage_id 설정
                query = """
                    INSERT INTO project_source_config (project_id, is_modified, passage_id, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE 
                        is_modified = VALUES(is_modified),
                        passage_id = VALUES(passage_id),
                        updated_at = NOW()
                """
                params = (project_id, is_modified, passage_id)
            else:
                # is_modified만 설정
                query = """
                    INSERT INTO project_source_config (project_id, is_modified, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE 
                        is_modified = VALUES(is_modified),
                        updated_at = NOW()
                """
                params = (project_id, is_modified)
            
            cursor.execute(query, params)
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    try:
        if connection:
            return _execute(connection)
        else:
            from app.db.database import get_db_connection
            with get_db_connection() as conn:
                return _execute(conn)
    except Exception as e:
        logger.error("Error updating passage use: %s", e)
        return False


def update_project_config_status(project_id: int, is_modified: int, custom_passage_id: int, connection=None):
    """
    프로젝트 설정 상태 업데이트 (KST 기준)
    INSERT ON DUPLICATE KEY UPDATE 패턴으로 Race Condition 방지
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            query = """
                INSERT INTO project_source_config (project_id, is_modified, custom_passage_id, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                    is_modified = VALUES(is_modified),
                    custom_passage_id = VALUES(custom_passage_id),
                    updated_at = NOW()
            """
            cursor.execute(query, (project_id, is_modified, custom_passage_id))
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    try:
        if connection:
            return _execute(connection)
        else:
            from app.db.database import get_db_connection
            with get_db_connection() as conn:
                return _execute(conn)
    except Exception as e:
        logger.error("Error updating project config status: %s", e)
        return False


def search_passages_keyword(keyword: str, user_id: int, source_type: Optional[int] = None, connection=None) -> List[Dict[str, Any]]:
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
        return select_with_query(query, (search_pattern, search_pattern), connection=connection)
        
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






def insert_without_passage(project_id: int, connection=None):
    """
    지문없이 생성 시 프로젝트 소스 구성에 저장
    """
    try:
            data = {
                "project_id": project_id,
                "is_modified": 2
            }
            return insert_one("project_source_config", data, connection=connection)

    except Exception as e:
        logger.error("Error inserting without passage: %s", e)
        return False