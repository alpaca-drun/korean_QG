from typing import Optional, Dict, Any
from threading import Lock
import pymysql
from app.core.config import settings
from app.core.logger import logger


def get_db_connection():
    """데이터베이스 연결 생성"""
    if not all([settings.db_host, settings.db_user, settings.db_password, settings.db_database]):
        return None
    
    try:
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        logger.error("데이터베이스 연결 실패: %s", e)
        return None


def save_question_to_db(
    question_data: Dict[str, Any],
    lock: Optional[Lock] = None,
    info_id: Optional[str] = None,
) -> Optional[int]:
    """
    문항을 데이터베이스에 저장
    
    Args:
        question_data: 문항 데이터 딕셔너리
        lock: 스레드 안전을 위한 Lock (선택사항)
        info_id: 정보 ID (선택사항)
        
    Returns:
        저장된 question_id 또는 None
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            # 문항 테이블에 저장 (테이블 구조에 맞게 수정 필요)
            sql = """
                INSERT INTO questions (
                    question_text, correct_answer, explanation,
                    passage_info, choices, info_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            
            question_text = question_data.get("question_text", {})
            if isinstance(question_text, dict):
                question_text_str = question_text.get("text", "")
            else:
                question_text_str = str(question_text)
            
            correct_answer = question_data.get("correct_answer", "")
            explanation = question_data.get("explanation", "")
            
            # passage_info를 JSON 문자열로 변환
            import json
            passage_info = json.dumps(question_data.get("passage_info", {}), ensure_ascii=False)
            choices = json.dumps(question_data.get("choices", []), ensure_ascii=False)
            
            if lock:
                with lock:
                    cursor.execute(
                        sql,
                        (question_text_str, correct_answer, explanation, passage_info, choices, info_id)
                    )
                    connection.commit()
                    question_id = cursor.lastrowid
            else:
                cursor.execute(
                    sql,
                    (question_text_str, correct_answer, explanation, passage_info, choices, info_id)
                )
                connection.commit()
                question_id = cursor.lastrowid
            
            return question_id
            
    except Exception as e:
        logger.error("문항 DB 저장 실패: %s", e)
        if connection:
            connection.rollback()
        return None
    finally:
        if connection:
            connection.close()


def save_questions_batch_to_db(
    questions_data: list[Dict[str, Any]],
    lock: Optional[Lock] = None,
    info_id: Optional[str] = None,
) -> list[Optional[int]]:
    """
    여러 문항을 배치로 데이터베이스에 저장
    
    Args:
        questions_data: 문항 데이터 리스트
        lock: 스레드 안전을 위한 Lock (선택사항)
        info_id: 정보 ID (선택사항)
        
    Returns:
        저장된 question_id 리스트
    """
    question_ids = []
    
    for question_data in questions_data:
        question_id = save_question_to_db(question_data, lock, info_id)
        question_ids.append(question_id)
    
    return question_ids

