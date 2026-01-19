"""데이터베이스 연결 및 쿼리 실행 유틸리티"""
import os
import pymysql
from contextlib import contextmanager
from typing import List, Dict, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

# 서버(.env) 호환: DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_DATABASE fallback 지원
def _get_fallback_db_env() -> Dict[str, Any]:
    """
    기존 prefix 방식(QG_db_host 등)이 없을 때, 일반 DB_* 환경변수를 fallback으로 사용합니다.
    """
    fb = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DATABASE"),
        "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    }
    # port 정수 변환
    if fb["port"] is not None:
        try:
            fb["port"] = int(str(fb["port"]).strip())
        except ValueError:
            fb["port"] = None
    return fb

# 기본 데이터베이스 설정
DEFAULT_DB_CONFIG = {
    'host': os.getenv("Job_db_host"),
    'port': int(os.getenv("Job_db_port")) if os.getenv("Job_db_port") else 3306,
    'user': os.getenv("Job_db_user"),
    'password': os.getenv("Job_db_password"),
    'database': os.getenv("Job_db_database"),
    'charset': 'utf8mb4'
}


@contextmanager
def get_db_connection(db_config: Optional[Dict[str, Any]] = None, env_prefix: str = "Job_db", database: str = "crawling"):
    """
    데이터베이스 연결을 안전하게 관리하는 context manager
    사용 후 자동으로 연결을 닫습니다.
    
    Args:
        db_config: 데이터베이스 설정 딕셔너리 (선택사항)
        env_prefix: 환경변수 접두사 (기본값: "Job_db")
        database: 데이터베이스 이름
    
    환경변수 예시:
        Job_db_host, Job_db_port, Job_db_user, Job_db_password, Job_db_database
    """
    connection = None
    try:
        # 설정 우선순위: 매개변수 > 환경변수 > 기본값
        config = DEFAULT_DB_CONFIG.copy()
        
        if database:
            database = database
        else:
            database = os.getenv(f"{env_prefix}_database") or os.getenv(f"{env_prefix}_database") or os.getenv(f"{env_prefix}_DATABASE")
        
        # 환경변수에서 설정 가져오기
        env_config = {
            'host': os.getenv(f"{env_prefix}_host") or os.getenv(f"{env_prefix}_host"),
            'port': os.getenv(f"{env_prefix}_port") or os.getenv(f"{env_prefix}_port"),
            'user': os.getenv(f"{env_prefix}_user") or os.getenv(f"{env_prefix}_user"),
            'password': os.getenv(f"{env_prefix}_password") or os.getenv(f"{env_prefix}_password"),
            'database': database,
            'charset': os.getenv(f"{env_prefix}_charset", 'utf8mb4')
        }
        
        # None이 아닌 값들만 업데이트
        for key, value in env_config.items():
            if value is not None:
                if key == 'port':
                    config[key] = int(value)
                else:
                    config[key] = value

        # ✅ fallback: prefix 방식이 비어 있으면 DB_* 환경변수 사용
        fallback = _get_fallback_db_env()
        for key, value in fallback.items():
            if (config.get(key) is None or config.get(key) == "") and value is not None and value != "":
                config[key] = value
        
        # 매개변수로 전달된 설정이 있으면 최종적으로 덮어쓰기
        if db_config:
            config.update(db_config)
        
        # 필수 설정 확인
        if not config.get('host'):
            raise ValueError(
                f"데이터베이스 호스트가 설정되지 않았습니다. "
                f"환경변수 {env_prefix}_host 또는 DB_HOST를 확인하세요."
            )
        if not config.get('user'):
            raise ValueError(
                f"데이터베이스 사용자가 설정되지 않았습니다. "
                f"환경변수 {env_prefix}_user 또는 DB_USER를 확인하세요."
            )
        if not config.get('password'):
            raise ValueError(
                f"데이터베이스 비밀번호가 설정되지 않았습니다. "
                f"환경변수 {env_prefix}_password 또는 DB_PASSWORD를 확인하세요."
            )
        if not config.get('database'):
            raise ValueError(
                f"데이터베이스 이름이 설정되지 않았습니다. "
                f"환경변수 {env_prefix}_database 또는 DB_DATABASE를 확인하세요."
            )
        
        # MariaDB/MySQL 연결 (타임아웃 설정 추가)
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset'],
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,  # 연결 타임아웃 10초
            read_timeout=30,     # 읽기 타임아웃 30초
            write_timeout=30     # 쓰기 타임아웃 30초
        )
        
        yield connection  # context 내에서 사용
    except pymysql.OperationalError as e:
        error_code, error_msg = e.args
        if error_code == 2003:  # Can't connect to MySQL server
            logger.error(
                f"데이터베이스 서버 연결 실패 (타임아웃): {error_msg}\n"
                f"호스트: {config.get('host', 'N/A')}, 포트: {config.get('port', 'N/A')}\n"
                f"확인사항:\n"
                f"  1. 데이터베이스 서버가 실행 중인지 확인\n"
                f"  2. 호스트 주소와 포트가 올바른지 확인\n"
                f"  3. 방화벽 설정 확인\n"
                f"  4. 네트워크 연결 확인"
            )
        else:
            logger.error(f"데이터베이스 연결 오류 ({error_code}): {error_msg}")
        raise
    except pymysql.MySQLError as e:
        logger.error(f"데이터베이스 오류: {e}")
        raise
    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        raise
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise
    finally:
        if connection:
            connection.close()
            logger.debug("데이터베이스 연결이 안전하게 종료되었습니다.")


def execute_query(query: str, env_prefix: str = "QG_db", database: str = "midtest", 
                 params: Optional[Union[tuple, dict]] = None, 
                 fetch: bool = True, db_config: Optional[Dict[str, Any]] = None):
    """
    쿼리를 실행하고 결과를 반환하는 함수
    SELECT → 결과 반환
    INSERT/UPDATE/DELETE → 자동 커밋
    
    Args:
        query: 실행할 SQL 쿼리
        env_prefix: 환경변수 접두사
        database: 데이터베이스 이름
        params: 쿼리 매개변수
        fetch: 결과를 가져올지 여부 (SELECT용)
        db_config: 데이터베이스 설정 딕셔너리
    """
    with get_db_connection(db_config=db_config, env_prefix=env_prefix, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            if fetch:  # SELECT 같은 경우
                return cursor.fetchall()
            else:  # INSERT, UPDATE, DELETE 같은 경우
                connection.commit()
                return cursor.rowcount  # 영향받은 행 수 반환


def execute_batch_query(query, list_of_params, db_config: Optional[Dict[str, Any]] = None, 
                        env_prefix: str = "Job_db", database: str = "crawling"):
    """
    여러 행의 데이터를 한 번에 삽입/수정하기 위해 executemany()를 사용하는 함수
    """
    database = database
    
    # get_db_connection 컨텍스트 매니저 사용
    with get_db_connection(db_config=db_config, env_prefix=env_prefix, database=database) as connection:
        with connection.cursor() as cursor:
            # ⭐️ 핵심: cursor.executemany() 사용
            row_count = cursor.executemany(query, list_of_params)
            
            connection.commit()  # 배치 삽입 후 커밋
            return row_count  # 영향받은 행 수 반환