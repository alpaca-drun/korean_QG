from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from app.core.config import settings
from app.core.logger import logger


@contextmanager
def get_db_connection():
    """
    데이터베이스 연결을 위한 context manager
    
    사용 예시:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM projects")
                result = cursor.fetchall()
    """
    connection = None
    try:
        if not all([settings.db_host, settings.db_user, settings.db_password, settings.db_database]):
            raise ValueError("데이터베이스 설정이 완료되지 않았습니다.")
        
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False,
            init_command="SET time_zone = '+09:00'"  # KST 명시적 설정
        )
        yield connection
        connection.commit()
    except Exception as e:
        if connection:
            connection.rollback()
        logger.exception("DB 연결/컨텍스트 중 오류")
        raise e
    finally:
        if connection:
            connection.close()


# ===========================
# 조회 (SELECT) 함수들
# ===========================

def select_one(
    table: str,
    where: Optional[Dict[str, Any]] = None,
    columns: str = "*"
) -> Optional[Dict[str, Any]]:
    """
    단일 레코드 조회
    
    Args:
        table: 테이블 이름
        where: WHERE 조건 (딕셔너리)
        columns: 조회할 컬럼 (기본값: "*")
    
    Returns:
        레코드 (딕셔너리) 또는 None
    
    예시:
        user = select_one("users", {"user_id": 1})
        project = select_one("projects", {"project_id": 1, "is_deleted": False})
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = f"SELECT {columns} FROM {table}"
            params = []
            
            if where:
                conditions = " AND ".join([f"{key} = %s" for key in where.keys()])
                sql += f" WHERE {conditions}"
                params = list(where.values())
            
            sql += " LIMIT 1"
            cursor.execute(sql, params)
            return cursor.fetchone()


def select_all(
    table: str,
    where: Optional[Dict[str, Any]] = None,
    columns: str = "*",
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    여러 레코드 조회
    
    Args:
        table: 테이블 이름
        where: WHERE 조건 (딕셔너리)
        columns: 조회할 컬럼 (기본값: "*")
        order_by: 정렬 (예: "created_at DESC")
        limit: 제한 개수
        offset: 시작 위치
    
    Returns:
        레코드 리스트
    
    예시:
        projects = select_all("projects", {"user_id": 1, "is_deleted": False}, order_by="created_at DESC")
        questions = select_all("multiple_choice_questions", {"project_id": 1}, limit=10)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = f"SELECT {columns} FROM {table}"
            params = []
            
            if where:
                conditions = " AND ".join([f"{key} = %s" for key in where.keys()])
                sql += f" WHERE {conditions}"
                params = list(where.values())
            
            if order_by:
                sql += f" ORDER BY {order_by}"
            
            if limit:
                sql += f" LIMIT {limit}"
            
            if offset:
                sql += f" OFFSET {offset}"
            
            cursor.execute(sql, params)
            return cursor.fetchall()


def select_with_query(
    query: str,
    params: Optional[Union[tuple, list]] = None
) -> List[Dict[str, Any]]:
    """
    커스텀 쿼리로 조회 (복잡한 JOIN, 서브쿼리 등)
    
    Args:
        query: SQL 쿼리문
        params: 쿼리 파라미터
    
    Returns:
        레코드 리스트
    
    예시:
        query = '''
            SELECT p.*, ps.grade, ps.subject 
            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            WHERE p.user_id = %s
        '''
        results = select_with_query(query, (1,))
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


def count(
    table: str,
    where: Optional[Dict[str, Any]] = None
) -> int:
    """
    레코드 개수 조회
    
    Args:
        table: 테이블 이름
        where: WHERE 조건 (딕셔너리)
    
    Returns:
        레코드 개수
    
    예시:
        total = count("projects", {"user_id": 1, "is_deleted": False})
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = f"SELECT COUNT(*) as count FROM {table}"
            params = []
            
            if where:
                conditions = " AND ".join([f"{key} = %s" for key in where.keys()])
                sql += f" WHERE {conditions}"
                params = list(where.values())
            
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return result["count"] if result else 0


# ===========================
# 추가 (INSERT) 함수들
# ===========================

def insert_one(
    table: str,
    data: Dict[str, Any]
) -> int:
    """
    단일 레코드 삽입
    
    Args:
        table: 테이블 이름
        data: 삽입할 데이터 (딕셔너리)
    
    Returns:
        삽입된 레코드의 ID (auto_increment)
    
    예시:
        project_id = insert_one("projects", {
            "user_id": 1,
            "project_name": "새 프로젝트",
            "status": "WRITING"
        })
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            cursor.execute(sql, list(data.values()))
            return cursor.lastrowid


def insert_many(
    table: str,
    data_list: List[Dict[str, Any]]
) -> int:
    """
    여러 레코드 일괄 삽입
    
    Args:
        table: 테이블 이름
        data_list: 삽입할 데이터 리스트
    
    Returns:
        삽입된 레코드 개수
    
    예시:
        questions = [
            {"project_id": 1, "question": "문제1", "answer": "답1"},
            {"project_id": 1, "question": "문제2", "answer": "답2"}
        ]
        count = insert_many("multiple_choice_questions", questions)
    """
    if not data_list:
        return 0
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            columns = ", ".join(data_list[0].keys())
            placeholders = ", ".join(["%s"] * len(data_list[0]))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            params = [list(data.values()) for data in data_list]
            cursor.executemany(sql, params)
            return cursor.rowcount


# ===========================
# 수정 (UPDATE) 함수들
# ===========================

def update(
    table: str,
    data: Dict[str, Any],
    where: Dict[str, Any]
) -> int:
    """
    레코드 업데이트
    
    Args:
        table: 테이블 이름
        data: 업데이트할 데이터 (딕셔너리)
        where: WHERE 조건 (딕셔너리)
    
    Returns:
        업데이트된 레코드 개수
    
    예시:
        count = update(
            "projects",
            {"status": "COMPLETED", "project_name": "완료된 프로젝트"},
            {"project_id": 1}
        )
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
            where_clause = " AND ".join([f"{key} = %s" for key in where.keys()])
            
            sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            params = list(data.values()) + list(where.values())
            
            cursor.execute(sql, params)
            return cursor.rowcount


# ===========================
# 삭제 (DELETE) 함수들
# ===========================

def delete(
    table: str,
    where: Dict[str, Any]
) -> int:
    """
    레코드 삭제 (물리 삭제)
    
    Args:
        table: 테이블 이름
        where: WHERE 조건 (딕셔너리)
    
    Returns:
        삭제된 레코드 개수
    
    예시:
        count = delete("projects", {"project_id": 1})
    
    주의: 물리적으로 삭제됩니다. soft delete가 필요한 경우 update() 사용
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            where_clause = " AND ".join([f"{key} = %s" for key in where.keys()])
            sql = f"DELETE FROM {table} WHERE {where_clause}"
            
            cursor.execute(sql, list(where.values()))
            return cursor.rowcount


def soft_delete(
    table: str,
    where: Dict[str, Any],
    deleted_column: str = "is_deleted"
) -> int:
    """
    레코드 논리 삭제 (soft delete)
    
    Args:
        table: 테이블 이름
        where: WHERE 조건 (딕셔너리)
        deleted_column: 삭제 플래그 컬럼명 (기본값: "is_deleted")
    
    Returns:
        업데이트된 레코드 개수
    
    예시:
        count = soft_delete("projects", {"project_id": 1})
    """
    return update(table, {deleted_column: True}, where)


# ===========================
# 트랜잭션 함수
# ===========================

def execute_transaction(operations: List[callable]) -> bool:
    """
    여러 DB 작업을 트랜잭션으로 실행
    
    Args:
        operations: 실행할 함수 리스트
    
    Returns:
        성공 여부
    
    예시:
        def create_project_with_config():
            project_id = insert_one("projects", {...})
            insert_one("project_source_config", {"project_id": project_id, ...})
        
        success = execute_transaction([create_project_with_config])
    """
    try:
        with get_db_connection() as conn:
            for operation in operations:
                operation()
        return True
    except Exception as e:
        logger.error("트랜잭션 실패: %s", e)
        return False


# ===========================
# 검색 함수 (LIKE)
# ===========================

def search(
    table: str,
    search_columns: List[str],
    keyword: str,
    where: Optional[Dict[str, Any]] = None,
    columns: str = "*",
    order_by: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    LIKE 검색
    
    Args:
        table: 테이블 이름
        search_columns: 검색할 컬럼 리스트
        keyword: 검색 키워드
        where: 추가 WHERE 조건
        columns: 조회할 컬럼
        order_by: 정렬
        limit: 제한 개수
    
    Returns:
        레코드 리스트
    
    예시:
        projects = search(
            "projects",
            ["project_name"],
            "프로젝트",
            where={"user_id": 1, "is_deleted": False},
            order_by="created_at DESC"
        )
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = f"SELECT {columns} FROM {table} WHERE "
            params = []
            
            # LIKE 조건 생성
            like_conditions = " OR ".join([f"{col} LIKE %s" for col in search_columns])
            sql += f"({like_conditions})"
            params.extend([f"%{keyword}%"] * len(search_columns))
            
            # 추가 WHERE 조건
            if where:
                additional_conditions = " AND ".join([f"{key} = %s" for key in where.keys()])
                sql += f" AND {additional_conditions}"
                params.extend(list(where.values()))
            
            if order_by:
                sql += f" ORDER BY {order_by}"
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql, params)
            return cursor.fetchall()

def update_with_query(query: str, params: tuple):
    """커스텀 쿼리로 업데이트"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount