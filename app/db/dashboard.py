from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from app.core.config import settings
from app.core.logger import logger
from app.db.database import select_with_query, select_all, count, select_with_query, select_one, update

from app.schemas.dashboard import (
    DashboardResponse, 
    DashboardStats,
    ProjectStatusCount,
    QuestionTypeCount,
    TokenUsage,
    RecentProject,
    ProjectDetailResponse,
    ProjectDetailStats,
    ProjectResponse,
    DashboardSummary,
    DashboardSummaryResponse,
    ProjectListItem,
    ProjectListResponse,
    FilterOption,
    FilterOptionsResponse,
    SuccessResponse,
)

# ===========================
# 헬퍼 함수
# ===========================

def get_project_ids_for_user(user_id: int) -> list:
    """사용자의 프로젝트 ID 목록을 조회합니다."""
    projects = select_all(
        table="projects",
        where={"user_id": user_id, "is_deleted": False},
        columns="project_id"
    )
    return [p["project_id"] for p in projects]

def get_all_project_ids_admin() -> list:
    """tester를 제외한 모든 프로젝트 ID 목록을 조회합니다."""

    query = """
        SELECT 
            p.project_id
        FROM projects p
        LEFT JOIN users u ON u.user_id = p.user_id
        WHERE p.is_deleted = FALSE AND u.role in ('admin', 'user')
    """
    return select_with_query(query)

def get_all_project_ids_master() -> list:
    """모든 프로젝트 ID 목록을 조회합니다."""
    projects = select_all(
        table="projects",
        where={"is_deleted": False},
        columns="project_id"
    )
    return [p["project_id"] for p in projects]


def get_project_info_admin_dashboard(project_id: int, connection=None) -> Optional[Dict[str, Any]]:
    query = """
        SELECT 
            *
        FROM projects p
        LEFT JOIN users u ON u.user_id = p.user_id
        WHERE p.project_id = %s AND p.is_deleted = FALSE AND u.role in ('admin', 'user')
    """

    return select_with_query(query, (project_id,), connection=connection)



def get_question_counts_by_project_ids(project_ids: list) -> QuestionTypeCount:
    """프로젝트 ID 목록에 해당하는 문항 수를 조회합니다."""
    if not project_ids:
        return QuestionTypeCount()
    
    placeholders = ", ".join(["%s"] * len(project_ids))
    
    mc_query = f"SELECT COUNT(*) as count FROM multiple_choice_questions WHERE project_id IN ({placeholders})"
    mc_result = select_with_query(mc_query, tuple(project_ids))
    mc_count = mc_result[0]["count"] if mc_result else 0
    
    tf_query = f"SELECT COUNT(*) as count FROM true_false_questions WHERE project_id IN ({placeholders})"
    tf_result = select_with_query(tf_query, tuple(project_ids))
    tf_count = tf_result[0]["count"] if tf_result else 0
    
    sa_query = f"SELECT COUNT(*) as count FROM short_answer_questions WHERE project_id IN ({placeholders})"
    sa_result = select_with_query(sa_query, tuple(project_ids))
    sa_count = sa_result[0]["count"] if sa_result else 0
    
    total = mc_count + tf_count + sa_count
    
    return QuestionTypeCount(
        multiple_choice=mc_count,
        true_false=tf_count,
        short_answer=sa_count,
        total=total
    )


def get_total_question_count_by_project_ids(project_ids: list) -> int:
    """프로젝트 ID 목록에 해당하는 총 문항 수를 조회합니다."""
    if not project_ids:
        return 0
    
    placeholders = ", ".join(["%s"] * len(project_ids))
    
    query = f"""
        SELECT 
            (SELECT COUNT(*) FROM multiple_choice_questions WHERE project_id IN ({placeholders})) +
            (SELECT COUNT(*) FROM true_false_questions WHERE project_id IN ({placeholders})) +
            (SELECT COUNT(*) FROM short_answer_questions WHERE project_id IN ({placeholders})) as total
    """
    result = select_with_query(query, tuple(project_ids * 3))
    return result[0]["total"] if result else 0


def get_token_usage_by_project_ids(project_ids: list) -> TokenUsage:
    """프로젝트 ID 목록에 해당하는 토큰 사용량을 조회합니다."""
    if not project_ids:
        return TokenUsage()
    
    placeholders = ", ".join(["%s"] * len(project_ids))
    
    query = f"""
        SELECT 
            COALESCE(SUM(input_tokens), 0) as total_input,
            COALESCE(SUM(output_token), 0) as total_output
        FROM project_source_config 
        WHERE project_id IN ({placeholders})
    """
    result = select_with_query(query, tuple(project_ids))
    
    if result and result[0]:
        total_input = int(result[0]["total_input"] or 0)
        total_output = int(result[0]["total_output"] or 0)
        return TokenUsage(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_input + total_output
        )
    
    return TokenUsage()


def get_avg_feedback_score_by_project_ids(project_ids: list) -> float | None:
    """프로젝트 ID 목록에 해당하는 평균 품질 평가 점수를 조회합니다."""
    if not project_ids:
        return None
    
    placeholders = ", ".join(["%s"] * len(project_ids))
    
    query = f"""
        SELECT AVG(feedback_score) as avg_score FROM (
            SELECT feedback_score FROM multiple_choice_questions 
            WHERE project_id IN ({placeholders}) AND feedback_score IS NOT NULL
            UNION ALL
            SELECT feedback_score FROM true_false_questions 
            WHERE project_id IN ({placeholders}) AND feedback_score IS NOT NULL
            UNION ALL
            SELECT feedback_score FROM short_answer_questions 
            WHERE project_id IN ({placeholders}) AND feedback_score IS NOT NULL
        ) as all_scores
    """
    result = select_with_query(query, tuple(project_ids * 3))
    
    if result and result[0] and result[0]["avg_score"]:
        return round(float(result[0]["avg_score"]), 2)
    
    return None


def get_question_count_for_project(project_id: int) -> int:
    """개별 프로젝트의 총 문항 수를 조회합니다."""
    mc_count = count("multiple_choice_questions", {"project_id": project_id})
    tf_count = count("true_false_questions", {"project_id": project_id})
    sa_count = count("short_answer_questions", {"project_id": project_id})
    return mc_count + tf_count + sa_count


def get_status_label(status: str) -> str:
    """상태 코드를 라벨로 변환합니다."""
    status_map = {
        "WRITING": "작성중",
        "GENERATING": "생성중",
        "COMPLETED": "생성완료"
    }
    return status_map.get(status, "작성중")


def get_question_type_label(question_type: str) -> str:
    """문항 유형 코드를 라벨로 변환합니다."""
    if not question_type:
        return "-"
    
    type_map = {
        "multiple_choice": "5지선다형",
        "5지선다": "5지선다형",
        "true_false": "OX형",
        "ox": "OX형",
        "short_answer": "단답형",
        "단답형": "단답형"
    }
    return type_map.get(question_type.lower(), question_type)




