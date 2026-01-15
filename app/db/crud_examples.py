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
# 조회 예시
# ===========================

def get_user_by_id_example(user_id: int):
    """사용자 조회"""
    user = select_one("users", {"user_id": user_id})
    return user


def get_projects_by_user_example(user_id: int):
    """사용자의 프로젝트 목록 조회"""
    projects = select_all(
        "projects",
        where={"user_id": user_id, "is_deleted": False},
        order_by="created_at DESC"
    )
    return projects


def get_project_with_scope_example(project_id: int):
    """프로젝트와 범위 정보를 JOIN으로 조회"""
    query = """
        SELECT 
            p.project_id,
            p.project_name,
            p.status,
            ps.grade,
            ps.semester,
            ps.subject
        FROM projects p
        LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
        WHERE p.project_id = %s AND p.is_deleted = FALSE
    """
    results = select_with_query(query, (project_id,))
    return results[0] if results else None


def count_user_projects_example(user_id: int):
    """사용자의 프로젝트 개수"""
    total = count("projects", {"user_id": user_id, "is_deleted": False})
    return total


def search_projects_example(user_id: int, keyword: str):
    """프로젝트 검색"""
    projects = search(
        table="projects",
        search_columns=["project_name"],
        keyword=keyword,
        where={"user_id": user_id, "is_deleted": False},
        order_by="created_at DESC"
    )
    return projects


# ===========================
# 추가 예시
# ===========================

def create_project_example(user_id: int, project_name: str):
    """프로젝트 생성"""
    project_id = insert_one("projects", {
        "user_id": user_id,
        "project_name": project_name,
        "status": "WRITING"
    })
    return project_id


def create_multiple_questions_example(questions_data: list):
    """여러 문항 일괄 생성"""
    count = insert_many("multiple_choice_questions", questions_data)
    return count


# ===========================
# 수정 예시
# ===========================

def update_project_status_example(project_id: int, status: str):
    """프로젝트 상태 업데이트"""
    count = update(
        table="projects",
        data={"status": status},
        where={"project_id": project_id}
    )
    return count


def update_question_feedback_example(question_id: int, feedback_score: float):
    """문항 피드백 점수 업데이트"""
    count = update(
        table="multiple_choice_questions",
        data={"feedback_score": feedback_score},
        where={"question_id": question_id}
    )
    return count


# ===========================
# 삭제 예시
# ===========================

def delete_project_soft_example(project_id: int):
    """프로젝트 논리 삭제 (soft delete)"""
    count = soft_delete("projects", {"project_id": project_id})
    return count


def delete_batch_log_hard_example(batch_id: int):
    """배치 로그 물리 삭제 (hard delete)"""
    count = delete("batch_logs", {"batch_id": batch_id})
    return count


# ===========================
# 복잡한 예시
# ===========================

def get_questions_with_project_info_example(user_id: int):
    """사용자의 모든 문항과 프로젝트 정보 조회"""
    query = """
        SELECT 
            q.question_id,
            q.question,
            q.answer,
            q.feedback_score,
            p.project_name,
            p.status
        FROM multiple_choice_questions q
        INNER JOIN projects p ON q.project_id = p.project_id
        WHERE p.user_id = %s AND p.is_deleted = FALSE
        ORDER BY q.created_at DESC
        LIMIT 100
    """
    results = select_with_query(query, (user_id,))
    return results


def get_project_statistics_example(project_id: int):
    """프로젝트 통계 조회"""
    query = """
        SELECT 
            COUNT(*) as total_questions,
            AVG(feedback_score) as avg_score,
            SUM(CASE WHEN is_used = TRUE THEN 1 ELSE 0 END) as used_questions
        FROM multiple_choice_questions
        WHERE project_id = %s
    """
    results = select_with_query(query, (project_id,))
    return results[0] if results else None

