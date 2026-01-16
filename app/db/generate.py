"""
DB CRUD 함수 사용 예시
"""
from app.db.database import (
    select_one, select_all, select_with_query, count, search,
    insert_one, insert_many,
    update,
    delete, soft_delete
)


# ===========================
# dong
# ===========================

def get_generation_config(project_id: int):
    """문항생성에 필요한 정보 조회"""

    query = """
        SELECT 
            psc.config_id,
            COALESCE(cp.context, p.context) AS passage,
            COALESCE(cp.title, p.title) AS title,
            COALESCE(cp.auth, p.auth) AS auth,
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
                    '$[*]' COLUMNS (ach_id_value INT PATH '$')
                ) AS jt
                WHERE a.ach_id = jt.ach_id_value
            ) AS achievements
        FROM project_source_config psc
        INNER JOIN projects pr ON psc.project_id = pr.project_id
        LEFT JOIN project_scopes ps ON pr.scope_id = ps.scope_id
        LEFT JOIN passages p ON psc.passage_id = p.passage_id
        LEFT JOIN passage_custom cp ON psc.custom_passage_id = cp.custom_passage_id
        WHERE psc.project_id = %s
    """
    results = select_with_query(query, (project_id,))
    return results[0] if results else None
import json
print("tett")
print(json.dumps(get_generation_config(1), ensure_ascii=False, indent=4))

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
        LEFT JOIN project_source_config psc ON p.project_id = psc.project_id
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


# ===========================
# 문항 관련 조회
# ===========================

def get_project_all_questions(project_id: int):
    """프로젝트의 모든 문항 조회 (객관식, OX, 단답형 통합)"""
    # 객관식 문항
    mc_query = """
        SELECT 
            'multiple_choice' as question_type,
            question_id as id,
            question,
            answer,
            answer_explain,
            feedback_score,
            is_used,
            created_at
        FROM multiple_choice_questions
        WHERE project_id = %s
    """
    
    # OX 문항
    tf_query = """
        SELECT 
            'true_false' as question_type,
            ox_question_id as id,
            question,
            answer,
            answer_explain,
            feedback_score,
            is_used,
            created_at
        FROM true_false_questions
        WHERE project_id = %s
    """
    
    # 단답형 문항
    sa_query = """
        SELECT 
            'short_answer' as question_type,
            short_question_id as id,
            question,
            answer,
            answer_explain,
            feedback_score,
            is_used,
            created_at
        FROM short_answer_questions
        WHERE project_id = %s
    """
    
    # UNION으로 통합
    union_query = f"""
        {mc_query}
        UNION ALL
        {tf_query}
        UNION ALL
        {sa_query}
        ORDER BY created_at DESC
    """
    
    results = select_with_query(union_query, (project_id, project_id, project_id))
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
            bl.input_token,
            bl.output_token,
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
        
        ORDER BY feedback_score DESC
    """
    results = select_with_query(query, (project_id, min_score, project_id, min_score, project_id, min_score))
    return results


# ===========================
# 지문 관련 조회
# ===========================

def get_passage_info(passage_id: int = None, scope_id: int = None):
    """원본 지문 정보 조회"""
    if passage_id:
        query = """
            SELECT 
                p.passage_id,
                p.title,
                p.context,
                p.auth,
                ps.grade,
                ps.semester,
                ps.subject,
                ps.study_area
            FROM passages p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            WHERE p.passage_id = %s
        """
        results = select_with_query(query, (passage_id,))
        return results[0] if results else None
    elif scope_id:
        query = """
            SELECT 
                passage_id,
                title,
                context,
                auth
            FROM passages
            WHERE scope_id = %s
        """
        results = select_with_query(query, (scope_id,))
        return results
    return None


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
            a.ach_id,
            a.code,
            a.description,
            a.evaluation_criteria
        FROM achievement a
        INNER JOIN project_scopes ps ON JSON_CONTAINS(ps.achievement_ids, CAST(a.ach_id AS JSON), '$')
        WHERE ps.scope_id = %s
    """
    results = select_with_query(query, (scope_id,))
    return results


# ===========================
# 통계 및 로그 조회
# ===========================

def get_project_statistics(project_id: int):
    """프로젝트의 문항 생성 통계"""
    query = """
        SELECT 
            (SELECT COUNT(*) FROM multiple_choice_questions WHERE project_id = %s) as mc_count,
            (SELECT COUNT(*) FROM true_false_questions WHERE project_id = %s) as tf_count,
            (SELECT COUNT(*) FROM short_answer_questions WHERE project_id = %s) as sa_count,
            (SELECT COUNT(*) FROM multiple_choice_questions WHERE project_id = %s AND is_used = TRUE) as mc_used_count,
            (SELECT COUNT(*) FROM true_false_questions WHERE project_id = %s AND is_used = TRUE) as tf_used_count,
            (SELECT COUNT(*) FROM short_answer_questions WHERE project_id = %s AND is_used = TRUE) as sa_used_count,
            (SELECT AVG(feedback_score) FROM multiple_choice_questions WHERE project_id = %s) as avg_mc_score,
            (SELECT AVG(feedback_score) FROM true_false_questions WHERE project_id = %s) as avg_tf_score,
            (SELECT AVG(feedback_score) FROM short_answer_questions WHERE project_id = %s) as avg_sa_score
    """
    results = select_with_query(query, (project_id,) * 9)
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
            bl.input_token,
            bl.output_token,
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
        )
        ORDER BY bl.batch_id DESC
    """
    results = select_with_query(query, (project_id, project_id, project_id))
    return results


def get_generation_logs_by_project(project_id: int):
    """프로젝트의 생성 로그 조회"""
    query = """
        SELECT 
            generation_log_id,
            question_type,
            input_token,
            output_token,
            model_name,
            ls.created_at as selection_created_at
        FROM generation_logs gl
        LEFT JOIN log_selection ls ON gl.selection_id = ls.selection_id
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
# 다운로드 로그 조회
# ===========================

def get_download_history(project_id: int):
    """프로젝트의 다운로드 이력 조회"""
    query = """
        SELECT 
            ld.download_id,
            ld.download_at,
            ls.JSON as selected_questions
        FROM log_download ld
        INNER JOIN log_selection ls ON ld.selection_id = ls.selection_id
        WHERE ls.project_id = %s
        ORDER BY ld.download_at DESC
    """
    results = select_with_query(query, (project_id,))
    return results

