"""
DB CRUD 함수 사용 예시
"""
from app.db.database import (
    select_one, select_all, select_with_query, count, search,
    insert_one, insert_many, update, delete, soft_delete,
    get_db_connection, update_with_query
)
from typing import Optional, Dict, Any
from threading import Lock
import json
from app.core.logger import logger
# ===========================
# dong
# ===========================

def update_project_status(project_id: int, status: str, connection=None):
    """프로젝트 상태 업데이트 (KST 기준)"""
    query = """
        UPDATE projects SET status = %s, updated_at = NOW() WHERE project_id = %s
    """
    return update_with_query(query, (status, project_id), connection=connection)

def update_project_generation_config(
    project_id: int,
    question_type=None,
    target_count=None,
    stem_directive=None,
    additional_prompt=None,
    use_ai_model=1,
    connection=None
):
    """
    프로젝트 생성 설정 데이터 업데이트
    """
    set_clauses = []
    params = []

    if target_count is not None:
        set_clauses.append("target_count = %s")
        params.append(target_count)
    
    if question_type is not None:
        set_clauses.append("question_type = %s")
        params.append(question_type)
    
    if stem_directive is not None:
        set_clauses.append("stem_directive = %s")
        params.append(stem_directive)
    
    if additional_prompt is not None:
        set_clauses.append("additional_prompt = %s")
        params.append(additional_prompt)
    
    if use_ai_model is not None:
        set_clauses.append("use_ai_model = %s")
        params.append(use_ai_model)

    if not set_clauses:
        return True

    # updated_at은 항상 업데이트
    set_clauses.append("updated_at = NOW()")

    set_clause_str = ", ".join(set_clauses)

    query = f"""
        UPDATE project_source_config 
        SET {set_clause_str}
        WHERE project_id = %s
        ORDER BY config_id DESC
        LIMIT 1
    """
    params.append(project_id)
    
    return update_with_query(query, tuple(params), connection=connection)


def get_generation_config(project_id: int):
    """문항생성에 필요한 정보 조회"""

    query = """
        SELECT 
            psc.config_id,
            pr.project_name,
            COALESCE(NULLIF(cp.context, ''), NULLIF(p.context, ''), '-') AS passage,
            COALESCE(NULLIF(cp.title, ''), NULLIF(p.title, ''), '-') AS title,
            COALESCE(NULLIF(cp.auth, ''), NULLIF(p.auth, ''), '-') AS auth,
            ps.school_level,
            ps.grade,
            ps.semester,
            ps.subject,
            ps.learning_objective,
            ps.learning_activity,
            ps.learning_element,
            ps.large_unit_name,
            ps.small_unit_name,
            ps.study_area,
            ps.achievement_ids,
            (
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'code', a.code,
                        'description', a.description,
                        'evaluation_criteria', a.evaluation_criteria
                    )
                )
                FROM achievement a
                CROSS JOIN JSON_TABLE(
                    JSON_UNQUOTE(COALESCE(ps.achievement_ids, '[]')),
                    '$[*]' COLUMNS (code_value VARCHAR(50) PATH '$')
                ) AS jt
                WHERE a.code = jt.code_value COLLATE utf8mb4_unicode_ci
            ) AS achievements
        FROM project_source_config psc
        INNER JOIN projects pr ON psc.project_id = pr.project_id
        LEFT JOIN project_scopes ps ON pr.scope_id = ps.scope_id
        LEFT JOIN passages p ON psc.passage_id = p.passage_id
        LEFT JOIN passage_custom cp ON psc.custom_passage_id = cp.custom_passage_id
        WHERE psc.project_id = %s
        ORDER BY psc.config_id DESC
    """
    results = select_with_query(query, (project_id,))
    return results[0] if results else None

# ===========================
# 프로젝트 관련 조회
# ===========================

def get_project_detail(project_id: int):
    """프로젝트 상세 정보 조회 (범위, 설정 정보 포함)"""
    query = """
        SELECT 
            p.project_id,
            p.project_name,
            p.status,
            p.created_at,
            p.updated_at,
            ps.grade,
            ps.semester,
            ps.subject,
            ps.study_area,
            ps.publisher_author,
            ps.learning_objective,
            ps.learning_activity,
            ps.learning_element,
            psc.question_type,
            psc.target_count,
            psc.is_modified,
            psc.use_ai_model,
            psc.stem_directive
        FROM projects p
        LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
        LEFT JOIN project_source_config psc ON psc.config_id = (
            SELECT MAX(config_id)
            FROM project_source_config
            WHERE project_id = p.project_id
        )
        WHERE p.project_id = %s AND p.is_deleted = FALSE
    """
    results = select_with_query(query, (project_id,))
    return results[0] if results else None


def get_user_projects(user_id: int, status: str = None):
    """사용자의 프로젝트 목록 조회 (상태별 필터 가능)"""
    if status:
        query = """
            SELECT 
                p.project_id,
                p.project_name,
                p.status,
                p.created_at,
                ps.grade,
                ps.semester,
                ps.subject
            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            WHERE p.user_id = %s AND p.status = %s AND p.is_deleted = FALSE
            ORDER BY p.updated_at DESC
        """
        results = select_with_query(query, (user_id, status))
    else:
        query = """
            SELECT 
                p.project_id,
                p.project_name,
                p.status,
                p.created_at,
                ps.grade,
                ps.semester,
                ps.subject
            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            WHERE p.user_id = %s AND p.is_deleted = FALSE
            ORDER BY p.updated_at DESC
        """
        results = select_with_query(query, (user_id,))
    return results




def save_batch_log(
    batch_log_data: Dict[str, Any],
    project_id: Optional[int] = None,
    connection=None
) -> Optional[int]:
    """
    배치 로그를 데이터베이스에 저장
    
    Args:
        batch_log_data: 배치 로그 데이터 딕셔너리
        project_id: 프로젝트 ID
        connection: 외부에서 전달된 DB 연결
        
    Returns:
        저장된 batch_id 또는 None
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            # 배치 로그 테이블에 저장 (최소 컬럼)
            sql = """
                INSERT INTO batch_logs (
                    input_tokens, output_tokens, 
                    total_duration,total_attempts,success_count
                ) VALUES (%s, %s, %s, %s, %s)
            """
            
            input_tokens = batch_log_data.get("input_tokens", 0)
            output_tokens = batch_log_data.get("output_tokens", 0)
            total_tokens = batch_log_data.get("total_tokens", 0)
            duration_seconds = batch_log_data.get("duration_seconds", 0.0)
            total_attempts = batch_log_data.get("requested_count", 0)
            success_count = batch_log_data.get("generated_count", 0)
            logger.debug("배치 로그 저장 시도: tokens=%s", total_tokens)
            
            cursor.execute(
                sql,
                (input_tokens, output_tokens, duration_seconds,total_attempts, success_count )
            )
            last_row_id = cursor.lastrowid
            if project_id:
                update_sql = """
                    UPDATE project_source_config 
                    SET input_tokens = COALESCE(input_tokens, 0) + %s, 
                        output_tokens = COALESCE(output_tokens, 0) + %s
                    WHERE project_id = %s
                    ORDER BY config_id DESC
                    LIMIT 1
                """
                cursor.execute(update_sql, (input_tokens, output_tokens, project_id))

            
            return last_row_id

    try:
        if connection:
            return _execute(connection)
        else:
            with get_db_connection() as connection:
                result = _execute(connection)
                connection.commit()
                return result
            
    except Exception as e:
        logger.exception("배치 로그 DB 저장 실패: %s", e)
        return None

def save_generation_log(
    project_id: int,
    config_id: Optional[int] = None,
    question_type: Optional[str] = None,
    input_token: int = 0,
    output_token: int = 0,
    model_name: Optional[str] = None,
    connection=None
) -> Optional[int]:
    """
    generation_logs 테이블에 생성 로그 저장

    Returns:
        저장된 generation_log_id 또는 None
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO generation_logs (
                    project_id, config_id, question_type,
                    input_token, output_token, model_name
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                project_id, config_id, question_type,
                input_token, output_token, model_name
            ))
            return cursor.lastrowid

    try:
        if connection:
            return _execute(connection)
        else:
            with get_db_connection() as conn:
                result = _execute(conn)
                conn.commit()
                return result
    except Exception as e:
        logger.exception("generation_logs 저장 실패: %s", e)
        return None


### 문항 데이터 저장
def save_question_to_db(
    question_data: Dict[str, Any],
    question_type: Optional[str] = None,
    project_id: Optional[int] = None,
    config_id: Optional[int] = None,
    connection=None
) -> Optional[int]:
    """
    문항을 데이터베이스에 저장
    
    Args:
        question_data: 문항 데이터 딕셔너리
        project_id: 프로젝트 ID
        config_id: 설정 ID
        connection: 외부에서 전달된 DB 연결 (트랜잭션 유지용)
    Returns:
        저장된 question_id 또는 None
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            


            # # 문항 테이블에 저장
            # sql = """
            #     INSERT INTO multiple_choice_questions (
            #         config_id, project_id, batch_id, question, box_content, modified_passage,
            #         option1, option2, option3, option4, option5, 
            #         answer, answer_explain, is_used, llm_difficulty, created_at
            #     ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            # """
            batch_id = question_data.get("batch_index", None)
            question_text = question_data.get("question_text", {})

            # print("🟣🟣🟣🟣🟣🟣")
            # print(question_text)
            
            # 'null' 문자열이나 빈 값을 None(NULL)으로 처리하는 헬퍼 함수
            def clean_val(v):
                if v is None or str(v).lower() == 'null' or v == '':
                    return None
                return v

            # Question 스키마의 필드명에 맞춤: "text"
            question = clean_val(question_text.get("text"))
            modified_passage = clean_val(question_text.get("modified_passage"))
            box_content = clean_val(question_text.get("box_content"))
            
            options = question_data.get("choices", [])
            option1 = clean_val(options[0]["text"]) if len(options) > 0 and "text" in options[0] else None
            option2 = clean_val(options[1]["text"]) if len(options) > 1 and "text" in options[1] else None
            option3 = clean_val(options[2]["text"]) if len(options) > 2 and "text" in options[2] else None
            option4 = clean_val(options[3]["text"]) if len(options) > 3 and "text" in options[3] else None
            option5 = clean_val(options[4]["text"]) if len(options) > 4 and "text" in options[4] else None
            
            # Question 스키마의 필드명에 맞춤: "correct_answer", "explanation"
            answer = clean_val(question_data.get("correct_answer"))
            answer_explain = clean_val(question_data.get("explanation"))
            is_used = question_data.get("is_used", 1)  # 기본값 1 (사용)
            
            # llm_difficulty 변환: 1 -> "쉬움", 2 -> "보통", 3 -> "어려움"
            llm_difficulty_raw = question_data.get("llm_difficulty", None)
            llm_difficulty_map = {1: "쉬움", 2: "보통", 3: "어려움"}
            llm_difficulty = llm_difficulty_map.get(llm_difficulty_raw, None) if llm_difficulty_raw else None
            llm_difficulty = clean_val(llm_difficulty)

            if question_type == "5지선다":
                sql = """
                    INSERT INTO multiple_choice_questions (
                        config_id, project_id, batch_id, question, box_content, modified_passage,
                        option1, option2, option3, option4, option5, 
                        answer, answer_explain, is_used, llm_difficulty, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(
                sql,
                (config_id, project_id, batch_id, question, box_content, modified_passage, option1, option2, option3, option4, option5, answer, answer_explain, is_used, llm_difficulty)
            )
            elif question_type == "단답형":
                sql = """
                    INSERT INTO short_answer_questions (
                        config_id, project_id, batch_id, question, box_content, modified_passage,
                        answer, answer_explain, is_used, llm_difficulty, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(
                sql,
                (config_id, project_id, batch_id, question, box_content, modified_passage, answer, answer_explain, is_used, llm_difficulty)
                )
            elif question_type == "진위형":
                # 진위형은 보기박스(box_content)가 불필요 — <보기>는 passage에 포함
                box_content = None
                sql = """
                    INSERT INTO true_false_questions (
                        config_id, project_id, batch_id, question, box_content, modified_passage,
                        answer, answer_explain, is_used, llm_difficulty, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(
                    sql,
                    (config_id, project_id, batch_id, question, box_content, modified_passage,
                     answer, answer_explain, is_used, llm_difficulty)
                )
            elif question_type == "선긋기":
                import random
                
                # 1. 원본 데이터 (정답 짝)
                left_items = [opt.get("text") for opt in options] if options else []
                
                # JSON 파싱 시도 (실패 시 하위 호환성을 위해 기존 split 방식 사용)
                try:
                    right_items = json.loads(answer) if answer else []
                    if not isinstance(right_items, list):
                        right_items = str(answer).split(" | ")
                except (json.JSONDecodeError, TypeError):
                    right_items = str(answer).split(" | ") if answer else []
                
                # 2. 인덱스 섞기 (0, 1, 2, 3...) -> (2, 0, 3, 1...)
                # 이 인덱스는 "오른쪽 항목"을 어떤 순서로 보여줄지를 결정함
                # 예: sort_order가 [2, 0, 1]이면 
                # 화면에는 right_items[2], right_items[0], right_items[1] 순서로 표시
                n = min(len(left_items), len(right_items))
                indices = list(range(n))
                random.shuffle(indices)
                
                # JSON 변환
                left_json = json.dumps(left_items, ensure_ascii=False)
                right_json = json.dumps(right_items, ensure_ascii=False)
                sort_order_json = json.dumps(indices, ensure_ascii=False)

                sql = """
                    INSERT INTO matching_questions (
                        config_id, project_id, batch_id, question, box_content, modified_passage,
                        left_items, right_items, sort_order,
                        answer_explain, is_used, llm_difficulty, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(
                    sql,
                    (config_id, project_id, batch_id, question, box_content, modified_passage, 
                     left_json, right_json, sort_order_json,
                     answer_explain, is_used, llm_difficulty)
                )



            return cursor.lastrowid

    try:
        if connection:
            return _execute(connection)
        else:
            with get_db_connection() as connection:
                result = _execute(connection)
                connection.commit()
                return result
            
    except Exception as e:
        logger.exception("문항 DB 저장 실패: %s", e)
        return None





_BATCH_INSERT_SQL = {
    "5지선다": """
        INSERT INTO multiple_choice_questions (
            config_id, project_id, batch_id, question, box_content, modified_passage,
            option1, option2, option3, option4, option5,
            answer, answer_explain, is_used, llm_difficulty, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """,
    "단답형": """
        INSERT INTO short_answer_questions (
            config_id, project_id, batch_id, question, box_content, modified_passage,
            answer, answer_explain, is_used, llm_difficulty, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """,
    "진위형": """
        INSERT INTO true_false_questions (
            config_id, project_id, batch_id, question, box_content, modified_passage,
            answer, answer_explain, is_used, llm_difficulty, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """,
    "선긋기": """
        INSERT INTO matching_questions (
            config_id, project_id, batch_id, question, box_content, modified_passage,
            left_items, right_items, sort_order,
            answer_explain, is_used, llm_difficulty, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """,
}


def _prepare_question_values(
    question_data: Dict[str, Any],
    question_type: str,
    config_id: Optional[int],
    project_id: Optional[int],
) -> tuple:
    """단일 문항 데이터에서 DB INSERT용 파라미터 튜플을 생성"""
    import random as _random

    def _clean(v):
        if v is None or str(v).lower() == 'null' or v == '':
            return None
        return v

    batch_id = question_data.get("batch_index")
    qt = question_data.get("question_text", {})
    question = _clean(qt.get("text"))
    modified_passage = _clean(qt.get("modified_passage"))
    box_content = _clean(qt.get("box_content"))

    options = question_data.get("choices", [])
    answer = _clean(question_data.get("correct_answer"))
    answer_explain = _clean(question_data.get("explanation"))
    is_used = question_data.get("is_used", 1)

    raw_diff = question_data.get("llm_difficulty")
    diff_map = {1: "쉬움", 2: "보통", 3: "어려움"}
    llm_difficulty = _clean(diff_map.get(raw_diff)) if raw_diff else None

    def _opt(idx):
        return _clean(options[idx]["text"]) if len(options) > idx and "text" in options[idx] else None

    if question_type == "5지선다":
        return (config_id, project_id, batch_id, question, box_content, modified_passage,
                _opt(0), _opt(1), _opt(2), _opt(3), _opt(4),
                answer, answer_explain, is_used, llm_difficulty)

    if question_type == "단답형":
        return (config_id, project_id, batch_id, question, box_content, modified_passage,
                answer, answer_explain, is_used, llm_difficulty)

    if question_type == "진위형":
        return (config_id, project_id, batch_id, question, None, modified_passage,
                answer, answer_explain, is_used, llm_difficulty)

    if question_type == "선긋기":
        left_items = [opt.get("text") for opt in options] if options else []
        try:
            right_items = json.loads(answer) if answer else []
            if not isinstance(right_items, list):
                right_items = str(answer).split(" | ")
        except (json.JSONDecodeError, TypeError):
            right_items = str(answer).split(" | ") if answer else []

        n = min(len(left_items), len(right_items))
        indices = list(range(n))
        _random.shuffle(indices)

        return (config_id, project_id, batch_id, question, box_content, modified_passage,
                json.dumps(left_items, ensure_ascii=False),
                json.dumps(right_items, ensure_ascii=False),
                json.dumps(indices, ensure_ascii=False),
                answer_explain, is_used, llm_difficulty)

    return ()


def save_questions_batch_to_db(
    questions_data: list[Dict[str, Any]],
    question_type: Optional[str] = None,
    project_id: Optional[int] = None,
    config_id: Optional[int] = None,
    connection=None
) -> list[Optional[int]]:
    """
    여러 문항을 배치로 데이터베이스에 저장 (executemany로 단일 라운드트립)
    """
    if not questions_data or question_type not in _BATCH_INSERT_SQL:
        return []

    def _execute(conn):
        sql = _BATCH_INSERT_SQL[question_type]
        params_list = [
            _prepare_question_values(qd, question_type, config_id, project_id)
            for qd in questions_data
        ]
        with conn.cursor() as cursor:
            cursor.executemany(sql, params_list)
            first_id = cursor.lastrowid
            return list(range(first_id, first_id + len(params_list)))

    try:
        if connection:
            return _execute(connection)
        else:
            with get_db_connection() as connection:
                result = _execute(connection)
                connection.commit()
                return result
    except Exception as e:
        logger.exception("배치 문항 DB 저장 실패: %s", e)
        return []




# ===========================
# 문항 관련 조회
# ===========================

def get_project_all_questions(project_id: int):
    """프로젝트의 모든 문항 조회 (객관식, OX, 단답형 통합)"""
    # 객관식 문항 (추가 필드 포함)
    mc_query = """
        SELECT 
            'multiple_choice' as question_type,
            mcq.question_id as id,
            NULLIF(mcq.question, 'null') as question,
            NULLIF(mcq.answer, 'null') as answer,
            NULLIF(mcq.answer_explain, 'null') as answer_explain,
            mcq.feedback_score,
            mcq.is_used,
            mcq.is_checked,
            mcq.created_at,
            NULLIF(mcq.box_content, 'null') as box_content,
            NULLIF(mcq.option1, 'null') as option1,
            NULLIF(mcq.option2, 'null') as option2,
            NULLIF(mcq.option3, 'null') as option3,
            NULLIF(mcq.option4, 'null') as option4,
            NULLIF(mcq.option5, 'null') as option5,
            NULLIF(mcq.llm_difficulty, 'null') as llm_difficulty,
            NULLIF(mcq.modified_difficulty, 'null') as modified_difficulty,
            NULLIF(mcq.modified_passage, 'null') as modified_passage,
            NULL as left_items, NULL as right_items, NULL as sort_order
        FROM multiple_choice_questions mcq
        WHERE mcq.project_id = %s AND IFNULL(mcq.is_used, 1) = 1
    """
    
    # OX 문항
    tf_query = """
        SELECT 
            'true_false' as question_type,
            tfq.ox_question_id as id,
            NULLIF(tfq.question, 'null') as question,
            NULLIF(tfq.answer, 'null') as answer,
            NULLIF(tfq.answer_explain, 'null') as answer_explain,
            tfq.feedback_score,
            tfq.is_used,
            tfq.is_checked,
            tfq.created_at,
            NULLIF(tfq.box_content, 'null') as box_content,
            NULL as option1,
            NULL as option2,
            NULL as option3,
            NULL as option4,
            NULL as option5,
            NULLIF(tfq.llm_difficulty, 'null') as llm_difficulty,
            NULLIF(tfq.modified_difficulty, 'null') as modified_difficulty,
            NULLIF(tfq.modified_passage, 'null') as modified_passage,
            NULL as left_items, NULL as right_items, NULL as sort_order
        FROM true_false_questions tfq
        WHERE tfq.project_id = %s AND IFNULL(tfq.is_used, 1) = 1
    """
    
    # 단답형 문항
    sa_query = """
        SELECT 
            'short_answer' as question_type,
            saq.short_question_id as id,
            NULLIF(saq.question, 'null') as question,
            NULLIF(saq.answer, 'null') as answer,
            NULLIF(saq.answer_explain, 'null') as answer_explain,
            saq.feedback_score,
            saq.is_used,
            saq.is_checked,
            saq.created_at,
            NULLIF(saq.box_content, 'null') as box_content,
            NULL as option1,
            NULL as option2,
            NULL as option3,
            NULL as option4,
            NULL as option5,
            NULLIF(saq.llm_difficulty, 'null') as llm_difficulty,
            NULLIF(saq.modified_difficulty, 'null') as modified_difficulty,
            NULLIF(saq.modified_passage, 'null') as modified_passage,
            NULL as left_items, NULL as right_items, NULL as sort_order
        FROM short_answer_questions saq
        WHERE saq.project_id = %s AND IFNULL(saq.is_used, 1) = 1
    """

    # 선긋기 문항
    mq_query = """
        SELECT 
            'matching' as question_type,
            mq.matching_question_id as id,
            NULLIF(mq.question, 'null') as question,
            NULL as answer,
            NULLIF(mq.answer_explain, 'null') as answer_explain,
            mq.feedback_score,
            mq.is_used,
            mq.is_checked,
            mq.created_at,
            NULLIF(mq.box_content, 'null') as box_content,
            NULL as option1, NULL as option2, NULL as option3, NULL as option4, NULL as option5,
            NULLIF(mq.llm_difficulty, 'null') as llm_difficulty,
            NULLIF(mq.modified_difficulty, 'null') as modified_difficulty,
            NULLIF(mq.modified_passage, 'null') as modified_passage,
            mq.left_items,
            mq.right_items,
            mq.sort_order
        FROM matching_questions mq
        WHERE mq.project_id = %s AND IFNULL(mq.is_used, 1) = 1
    """
    
    # UNION으로 통합
    union_query = f"""
        {mc_query}
        UNION ALL
        {tf_query}
        UNION ALL
        {sa_query}
        UNION ALL
        {mq_query}
        ORDER BY created_at ASC, id ASC
    """
    
    results = select_with_query(union_query, (project_id, project_id, project_id, project_id))
    return results


def get_multiple_choice_with_batch_info(project_id: int):
    """객관식 문항과 배치 로그 정보 조회"""
    query = """
        SELECT 
            mcq.question_id,
            mcq.question,
            mcq.option1,
            mcq.option2,
            mcq.option3,
            mcq.option4,
            mcq.option5,
            mcq.answer,
            mcq.answer_explain,
            mcq.feedback_score,
            mcq.llm_difficulty,
            mcq.is_used,
            bl.model_name,
            bl.temperature,
            bl.input_tokens AS input_token,
            bl.output_tokens AS output_token,
            bl.total_attempts,
            bl.success_count
        FROM multiple_choice_questions mcq
        LEFT JOIN batch_logs bl ON mcq.batch_id = bl.batch_id
        WHERE mcq.project_id = %s
        ORDER BY mcq.created_at DESC
    """
    results = select_with_query(query, (project_id,))
    return results


def get_questions_by_feedback_score(project_id: int, min_score: float = 7.0):
    """피드백 점수가 높은 문항만 조회"""
    query = """
        SELECT 
            'multiple_choice' as question_type,
            question_id as id,
            question,
            answer,
            feedback_score,
            is_used
        FROM multiple_choice_questions
        WHERE project_id = %s AND feedback_score >= %s
        
        UNION ALL
        
        SELECT 
            'true_false' as question_type,
            ox_question_id as id,
            question,
            answer,
            feedback_score,
            is_used
        FROM true_false_questions
        WHERE project_id = %s AND feedback_score >= %s
        
        UNION ALL
        
        SELECT 
            'short_answer' as question_type,
            short_question_id as id,
            question,
            answer,
            feedback_score,
            is_used
        FROM short_answer_questions
        WHERE project_id = %s AND feedback_score >= %s

        UNION ALL
        
        SELECT 
            'matching' as question_type,
            matching_question_id as id,
            question,
            NULL as answer,
            feedback_score,
            is_used
        FROM matching_questions
        WHERE project_id = %s AND feedback_score >= %s
        
        ORDER BY feedback_score DESC
    """
    results = select_with_query(query, (project_id, min_score, project_id, min_score, project_id, min_score, project_id, min_score))
    return results


# ===========================
# 지문 관련 조회
# ===========================

def get_custom_passage_info(user_id: int):
    """사용자가 업로드한 커스텀 지문 목록 조회"""
    query = """
        SELECT 
            cp.custom_passage_id,
            cp.custom_title,
            cp.title,
            cp.auth,
            cp.context,
            ps.grade,
            ps.semester,
            ps.subject
        FROM custom_passage cp
        LEFT JOIN project_scopes ps ON cp.scope_id = ps.scope_id
        WHERE cp.user_id = %s
        ORDER BY cp.custom_passage_id DESC
    """
    results = select_with_query(query, (user_id,))
    return results


def get_project_source_info(project_id: int):
    """프로젝트에서 사용한 지문 정보 조회 (원본/커스텀)"""
    query = """
        SELECT 
            psc.config_id,
            psc.is_modified,
            psc.question_type,
            psc.target_count,
            CASE 
                WHEN psc.passage_id IS NOT NULL THEN 'original'
                WHEN psc.custom_passage_id IS NOT NULL THEN 'custom'
                ELSE 'unknown'
            END as source_type,
            COALESCE(p.title, cp.custom_title) as title,
            COALESCE(p.context, cp.context) as context,
            COALESCE(p.auth, cp.auth) as auth
        FROM project_source_config psc
        LEFT JOIN passages p ON psc.passage_id = p.passage_id
        LEFT JOIN custom_passage cp ON psc.custom_passage_id = cp.custom_passage_id
        WHERE psc.project_id = %s
        ORDER BY psc.config_id DESC
        LIMIT 1
    """
    results = select_with_query(query, (project_id,))
    return results[0] if results else None


# ===========================
# 성취기준 관련 조회
# ===========================

def get_achievement_by_scope(scope_id: int):
    """프로젝트 범위의 성취기준 정보 조회"""
    query = """
        SELECT 
            a.code,
            a.description,
            a.evaluation_criteria
        FROM achievement a
        INNER JOIN project_scopes ps ON JSON_CONTAINS(ps.achievement_ids, JSON_QUOTE(a.code) COLLATE utf8mb4_unicode_ci, '$')
        WHERE ps.scope_id = %s
    """
    results = select_with_query(query, (scope_id,))
    return results


# ===========================
# 통계 및 로그 조회
# ===========================

def get_project_statistics(project_id: int):
    """프로젝트의 문항 생성 통계 (UNION ALL로 테이블당 1회 스캔)"""
    query = """
        SELECT
            SUM(CASE WHEN qt = 'mc' THEN 1 ELSE 0 END) as mc_count,
            SUM(CASE WHEN qt = 'tf' THEN 1 ELSE 0 END) as tf_count,
            SUM(CASE WHEN qt = 'sa' THEN 1 ELSE 0 END) as sa_count,
            SUM(CASE WHEN qt = 'mq' THEN 1 ELSE 0 END) as mq_count,
            SUM(CASE WHEN qt = 'mc' AND is_used = TRUE THEN 1 ELSE 0 END) as mc_used_count,
            SUM(CASE WHEN qt = 'tf' AND is_used = TRUE THEN 1 ELSE 0 END) as tf_used_count,
            SUM(CASE WHEN qt = 'sa' AND is_used = TRUE THEN 1 ELSE 0 END) as sa_used_count,
            SUM(CASE WHEN qt = 'mq' AND is_used = TRUE THEN 1 ELSE 0 END) as mq_used_count,
            AVG(CASE WHEN qt = 'mc' THEN feedback_score END) as avg_mc_score,
            AVG(CASE WHEN qt = 'tf' THEN feedback_score END) as avg_tf_score,
            AVG(CASE WHEN qt = 'sa' THEN feedback_score END) as avg_sa_score,
            AVG(CASE WHEN qt = 'mq' THEN feedback_score END) as avg_mq_score
        FROM (
            SELECT 'mc' as qt, is_used, feedback_score FROM multiple_choice_questions WHERE project_id = %s
            UNION ALL
            SELECT 'tf', is_used, feedback_score FROM true_false_questions WHERE project_id = %s
            UNION ALL
            SELECT 'sa', is_used, feedback_score FROM short_answer_questions WHERE project_id = %s
            UNION ALL
            SELECT 'mq', is_used, feedback_score FROM matching_questions WHERE project_id = %s
        ) all_questions
    """
    results = select_with_query(query, (project_id,) * 4)
    return results[0] if results else None


def get_batch_logs_by_project(project_id: int):
    """프로젝트의 배치 로그 조회"""
    query = """
        SELECT DISTINCT
            bl.batch_id,
            bl.model_name,
            bl.temperature,
            bl.top_p,
            bl.top_k,
            bl.input_tokens AS input_token,
            bl.output_tokens AS output_token,
            bl.total_duration,
            bl.total_attempts,
            bl.success_count,
            bl.error_message
        FROM batch_logs bl
        WHERE bl.batch_id IN (
            SELECT DISTINCT batch_id FROM multiple_choice_questions WHERE project_id = %s
            UNION
            SELECT DISTINCT batch_id FROM true_false_questions WHERE project_id = %s
            UNION
            SELECT DISTINCT batch_id FROM short_answer_questions WHERE project_id = %s
            UNION
            SELECT DISTINCT batch_id FROM matching_questions WHERE project_id = %s
        )
        ORDER BY bl.batch_id DESC
    """
    results = select_with_query(query, (project_id, project_id, project_id, project_id))
    return results


def get_generation_logs_by_project(project_id: int):
    """프로젝트의 생성 로그 조회"""
    query = """
        SELECT 
            gl.generation_log_id,
            gl.question_type,
            gl.input_token,
            gl.output_token,
            gl.model_name,
            gl.config_id
        FROM generation_logs gl
        WHERE gl.project_id = %s
        ORDER BY gl.generation_log_id DESC
    """
    results = select_with_query(query, (project_id,))
    return results


# ===========================
# 사용자 관련 조회
# ===========================

def get_user_info(user_id: int):
    """사용자 정보 및 선호도 조회"""
    query = """
        SELECT 
            u.user_id,
            u.login_id,
            u.name,
            u.role,
            u.subject,
            u.memo,
            u.is_active,
            u.created_at,
            up.blocklist_json
        FROM users u
        LEFT JOIN user_preferences up ON u.user_id = up.user_id
        WHERE u.user_id = %s
    """
    results = select_with_query(query, (user_id,))
    return results[0] if results else None


def get_user_token_usage(user_id: int):
    """사용자의 토큰 사용량 통계"""
    query = """
        SELECT 
            u.user_id,
            u.name,
            SUM(gl.input_token) as total_input_tokens,
            SUM(gl.output_token) as total_output_tokens,
            COUNT(DISTINCT gl.project_id) as total_projects,
            COUNT(gl.generation_log_id) as total_generations
        FROM users u
        INNER JOIN projects p ON u.user_id = p.user_id
        INNER JOIN generation_logs gl ON p.project_id = gl.project_id
        WHERE u.user_id = %s AND p.is_deleted = FALSE
        GROUP BY u.user_id, u.name
    """
    results = select_with_query(query, (user_id,))
    return results[0] if results else None


# ===========================
# 다운로드/선택 로그 저장 및 조회
# ===========================

def save_selection_log(
    project_id: int,
    selected_list: str,
    connection=None
) -> Optional[int]:
    """
    log_selection 테이블에 선택 로그 저장

    Args:
        project_id: 프로젝트 ID
        selected_list: 선택된 문항 ID JSON 문자열 (예: "[1,2,3]")

    Returns:
        저장된 selection_id 또는 None
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO log_selection (project_id, selected_list)
                VALUES (%s, %s)
            """
            cursor.execute(sql, (project_id, selected_list))
            return cursor.lastrowid

    try:
        if connection:
            return _execute(connection)
        else:
            with get_db_connection() as conn:
                result = _execute(conn)
                conn.commit()
                return result
    except Exception as e:
        logger.exception("log_selection 저장 실패: %s", e)
        return None


def save_download_log(
    selection_id: int,
    connection=None
) -> Optional[int]:
    """
    log_download 테이블에 다운로드 로그 저장

    Args:
        selection_id: log_selection의 selection_id (FK)

    Returns:
        저장된 download_id 또는 None
    """
    def _execute(conn):
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO log_download (selection_id)
                VALUES (%s)
            """
            cursor.execute(sql, (selection_id,))
            return cursor.lastrowid

    try:
        if connection:
            return _execute(connection)
        else:
            with get_db_connection() as conn:
                result = _execute(conn)
                conn.commit()
                return result
    except Exception as e:
        logger.exception("log_download 저장 실패: %s", e)
        return None


def get_download_history(project_id: int):
    """프로젝트의 다운로드 이력 조회"""
    query = """
        SELECT 
            ld.download_id,
            ld.download_at,
            ls.selected_list as selected_questions
        FROM log_download ld
        INNER JOIN log_selection ls ON ld.selection_id = ls.selection_id
        WHERE ls.project_id = %s
        ORDER BY ld.download_at DESC
    """
    results = select_with_query(query, (project_id,))
    return results
