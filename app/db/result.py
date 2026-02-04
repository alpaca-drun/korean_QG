from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from app.core.config import settings
from app.core.logger import logger
from app.db.database import select_with_query

def get_project_info_admin(project_id: int, connection=None) -> Optional[Dict[str, Any]]:
    query = """
        SELECT 
            p.project_id,
            p.project_name,
            ps.subject as category
        FROM projects p
        LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
        LEFT JOIN users u ON u.user_id = p.user_id
        WHERE p.project_id = %s AND p.is_deleted = FALSE AND u.role in ('admin', 'user')
    """

    return select_with_query(query, (project_id,), connection=connection)


def get_passage_info_admin(project_id: int, connection=None) -> Optional[Dict[str, Any]]:
    query = """
        SELECT 
            p.project_id,
            p.project_name,
            ps.subject as category
        FROM projects p
        LEFT JOIN users u ON u.user_id = p.user_id
        WHERE p.project_id = %s AND p.is_deleted = FALSE AND u.role in ('admin', 'user')
    """
    return select_with_query(query, (project_id,), connection=connection)


def get_passages_for_project(project_id: int, connection=None) -> Optional[list[dict]]:
    """
    프로젝트에 사용된 지문 목록을 조회합니다.
    """
    query = """
        SELECT 
            CASE
                WHEN psc.is_modified = 0 THEN psc.passage_id
                WHEN psc.is_modified = 1 THEN psc.custom_passage_id
                ELSE NULL
            END as passage_id,
            CASE
                WHEN psc.is_modified = 0 THEN p.title
                WHEN psc.is_modified = 1 THEN pc.title
                ELSE NULL
            END as title,
            CASE
                WHEN psc.is_modified = 0 THEN p.context
                WHEN psc.is_modified = 1 THEN pc.context
                ELSE NULL
            END as content,
            CASE
                WHEN psc.is_modified = 0 THEN p.auth
                WHEN psc.is_modified = 1 THEN pc.auth
                ELSE NULL
            END as auth,
            CASE 
                WHEN psc.is_modified = 0 THEN 0
                WHEN psc.is_modified = 1 THEN 1
                ELSE NULL
            END as is_custom
        FROM project_source_config psc
        LEFT JOIN passages p ON psc.passage_id = p.passage_id
        LEFT JOIN passage_custom pc ON psc.custom_passage_id = pc.custom_passage_id
        WHERE psc.project_id = %s
        AND (psc.passage_id IS NOT NULL OR psc.custom_passage_id IS NOT NULL)
        ORDER BY psc.config_id DESC
        LIMIT 1
    """
    results = select_with_query(query, (project_id,), connection=connection)
    return results if results else None
