"""
storage.py - 레거시 호환성을 위한 래퍼 모듈

NOTE: 이 모듈은 database.py의 커넥션 풀을 사용하도록 리팩토링되었습니다.
새 코드에서는 app.db.database의 함수들을 직접 사용하세요.
"""
from typing import Optional, Dict, Any
from threading import Lock
import json
from app.db.database import get_db_connection
from app.core.logger import logger


# 레거시 호환성을 위해 get_db_connection을 re-export
# 새 코드에서는 from app.db.database import get_db_connection 사용 권장
__all__ = ['get_db_connection', 'save_question_to_db', 'save_questions_batch_to_db']


def save_question_to_db(
    question_data: Dict[str, Any],
    lock: Optional[Lock] = None,
    info_id: Optional[str] = None,
) -> Optional[int]:
    """
    문항을 데이터베이스에 저장 (커넥션 풀 사용)
    
    Args:
        question_data: 문항 데이터 딕셔너리
        lock: 스레드 안전을 위한 Lock (선택사항)
        info_id: 정보 ID (선택사항)
        
    Returns:
        저장된 question_id 또는 None
    """
    try:
        with get_db_connection() as connection:
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
                passage_info = json.dumps(question_data.get("passage_info", {}), ensure_ascii=False)
                choices = json.dumps(question_data.get("choices", []), ensure_ascii=False)
                
                if lock:
                    with lock:
                        cursor.execute(
                            sql,
                            (question_text_str, correct_answer, explanation, passage_info, choices, info_id)
                        )
                        question_id = cursor.lastrowid
                else:
                    cursor.execute(
                        sql,
                        (question_text_str, correct_answer, explanation, passage_info, choices, info_id)
                    )
                    question_id = cursor.lastrowid
                
                return question_id
            
    except Exception as e:
        logger.error("문항 DB 저장 실패: %s", e)
        return None


def save_questions_batch_to_db(
    questions_data: list[Dict[str, Any]],
    lock: Optional[Lock] = None,
    info_id: Optional[str] = None,
) -> list[Optional[int]]:
    """
    여러 문항을 배치로 데이터베이스에 저장 (단일 트랜잭션)
    
    Args:
        questions_data: 문항 데이터 리스트
        lock: 스레드 안전을 위한 Lock (선택사항)
        info_id: 정보 ID (선택사항)
        
    Returns:
        저장된 question_id 리스트
    """
    question_ids = []
    
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO questions (
                        question_text, correct_answer, explanation,
                        passage_info, choices, info_id, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                
                for question_data in questions_data:
                    try:
                        question_text = question_data.get("question_text", {})
                        if isinstance(question_text, dict):
                            question_text_str = question_text.get("text", "")
                        else:
                            question_text_str = str(question_text)
                        
                        correct_answer = question_data.get("correct_answer", "")
                        explanation = question_data.get("explanation", "")
                        
                        passage_info = json.dumps(question_data.get("passage_info", {}), ensure_ascii=False)
                        choices = json.dumps(question_data.get("choices", []), ensure_ascii=False)
                        
                        if lock:
                            with lock:
                                cursor.execute(
                                    sql,
                                    (question_text_str, correct_answer, explanation, passage_info, choices, info_id)
                                )
                                question_ids.append(cursor.lastrowid)
                        else:
                            cursor.execute(
                                sql,
                                (question_text_str, correct_answer, explanation, passage_info, choices, info_id)
                            )
                            question_ids.append(cursor.lastrowid)
                    except Exception as e:
                        logger.error("개별 문항 저장 실패: %s", e)
                        question_ids.append(None)
                
                # 트랜잭션 성공 시 자동 commit (context manager에서 처리)
                
    except Exception as e:
        logger.error("배치 문항 DB 저장 실패: %s", e)
        # 실패 시 빈 리스트 대신 None으로 채워진 리스트 반환
        return [None] * len(questions_data)
    
    return question_ids

