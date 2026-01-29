from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from app.core.config import settings
from app.core.logger import logger

# 커넥션 풀 전역 변수
_pool = None

def get_pool():
    """데이터베이스 커넥션 풀 생성 및 반환"""
    global _pool
    if _pool is None:
        if not all([settings.db_host, settings.db_user, settings.db_password, settings.db_database]):
            raise ValueError("데이터베이스 설정이 완료되지 않았습니다.")
        
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=10,    # 최대 연결 수
            mincached=2,         # 최소 유휴 연결 수
            maxcached=5,         # 최대 유휴 연결 수
            maxshared=3,         # 최대 공유 연결 수
            blocking=True,       # 풀이 다 찼을 때 대기 여부
            maxusage=None,       # 연결 재사용 횟수 제한 없음
            setsession=[],       # 세션 초기화 명령 (필요 시 추가)
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=10,   # 연결 타임아웃 10초
            read_timeout=30,      # 읽기 타임아웃 30초
            write_timeout=30,     # 쓰기 타임아웃 30초
            init_command="SET time_zone = '+09:00'"
        )
    return _pool

@contextmanager
def get_db_connection():
    """
    커넥션 풀에서 연결을 가져오는 context manager
    """
    pool = get_pool()
    connection = pool.connection()
    try:
        yield connection
        connection.commit()
    except Exception as e:
        connection.rollback()
        logger.exception("DB 작업 중 오류 발생")
        raise e
    finally:
        connection.close()  # 실제로는 풀로 반환됨


# ===========================
# 조회 (SELECT) 함수들
# ===========================

def select_one(
    table: str,
    where: Optional[Dict[str, Any]] = None,
    columns: str = "*",
    connection=None
) -> Optional[Dict[str, Any]]:
    """
    단일 레코드 조회
    """
    def _execute(conn):
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

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            return _execute(conn)


def select_all(
    table: str,
    where: Optional[Dict[str, Any]] = None,
    columns: str = "*",
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    connection=None
) -> List[Dict[str, Any]]:
    """
    여러 레코드 조회
    """
    def _execute(conn):
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

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            return _execute(conn)


def select_with_query(
    query: str,
    params: Optional[Union[tuple, list]] = None,
    connection=None
) -> List[Dict[str, Any]]:
    """
    커스텀 쿼리로 조회 (복잡한 JOIN, 서브쿼리 등)
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            return _execute(conn)


def count(
    table: str,
    where: Optional[Dict[str, Any]] = None,
    connection=None
) -> int:
    """
    레코드 개수 조회
    """
    def _execute(conn):
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

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            return _execute(conn)


# ===========================
# 추가 (INSERT) 함수들
# ===========================

def insert_one(
    table: str,
    data: Dict[str, Any],
    connection=None
) -> int:
    """
    단일 레코드 삽입
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            cursor.execute(sql, list(data.values()))
            return cursor.lastrowid

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            res = _execute(conn)
            conn.commit()
            return res


def insert_many(
    table: str,
    data_list: List[Dict[str, Any]],
    connection=None
) -> int:
    """
    여러 레코드 일괄 삽입
    """
    if not data_list:
        return 0
    
    def _execute(conn):
        with conn.cursor() as cursor:
            columns = ", ".join(data_list[0].keys())
            placeholders = ", ".join(["%s"] * len(data_list[0]))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            params = [list(data.values()) for data in data_list]
            cursor.executemany(sql, params)
            return cursor.rowcount

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            res = _execute(conn)
            conn.commit()
            return res


# ===========================
# 수정 (UPDATE) 함수들
# ===========================

def update(
    table: str,
    data: Dict[str, Any],
    where: Dict[str, Any],
    connection=None
) -> int:
    """
    레코드 업데이트
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
            where_clause = " AND ".join([f"{key} = %s" for key in where.keys()])
            
            sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            params = list(data.values()) + list(where.values())
            
            cursor.execute(sql, params)
            return cursor.rowcount

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            res = _execute(conn)
            conn.commit()
            return res


# ===========================
# 삭제 (DELETE) 함수들
# ===========================

def delete(
    table: str,
    where: Dict[str, Any],
    connection=None
) -> int:
    """
    레코드 삭제 (물리 삭제)
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            where_clause = " AND ".join([f"{key} = %s" for key in where.keys()])
            sql = f"DELETE FROM {table} WHERE {where_clause}"
            
            cursor.execute(sql, list(where.values()))
            return cursor.rowcount

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            res = _execute(conn)
            conn.commit()
            return res


def soft_delete(
    table: str,
    where: Dict[str, Any],
    deleted_column: str = "is_deleted",
    connection=None
) -> int:
    """
    레코드 논리 삭제 (soft delete)
    """
    return update(table, {deleted_column: True}, where, connection=connection)


# ===========================
# 트랜잭션 함수
# ===========================

def execute_transaction(operations: List[callable]) -> bool:
    """
    여러 DB 작업을 트랜잭션으로 실행
    
    주의: operations 리스트에 전달되는 함수들은 connection 인자를 받아야 함
    """
    try:
        with get_db_connection() as conn:
            for operation in operations:
                operation(connection=conn)
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
    limit: Optional[int] = None,
    connection=None
) -> List[Dict[str, Any]]:
    """
    LIKE 검색
    """
    def _execute(conn):
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

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            return _execute(conn)

def update_with_query(query: str, params: Union[tuple, list], connection=None):
    """커스텀 쿼리로 업데이트 (DML: UPDATE, INSERT, DELETE)"""
    def _execute(conn):
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    if connection:
        return _execute(connection)
    else:
        with get_db_connection() as conn:
            res = _execute(conn)
            return res
