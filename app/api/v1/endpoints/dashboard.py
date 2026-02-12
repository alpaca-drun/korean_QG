from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas.curriculum import ListResponse
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
from app.utils.dependencies import get_current_user
from app.core.logger import logger
from app.db.database import select_all, search, count, select_with_query, select_one, update
import math

from app.db.dashboard import *

router = APIRouter()

# ===========================
# 대시보드 요약 통계 API (상단 카드용)
# ===========================

@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="대시보드 요약 통계 조회",
    description="대시보드 상단 카드에 표시할 요약 통계를 조회합니다.",
    tags=["대시보드"]
)
async def get_dashboard_summary(user_data: tuple[int, str] = Depends(get_current_user)):
    """
    대시보드 상단 요약 통계를 반환합니다.
    
    반환 데이터:
    - 전체 프로젝트 수
    - 작성중 프로젝트 수
    - 생성완료 프로젝트 수
    - 총 생성 문항 수
    """
    user_id, role = user_data
    
    try:

        if role == "admin":
            project_ids = get_all_project_ids_admin()
            total_projects = len(project_ids)
            # admin은 admin, user 역할의 프로젝트만 집계
            writing_query = """
                SELECT COUNT(*) as count FROM projects p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.is_deleted = FALSE AND p.status = 'WRITING' AND u.role IN ('admin', 'user')
            """
            completed_query = """
                SELECT COUNT(*) as count FROM projects p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.is_deleted = FALSE AND p.status = 'COMPLETED' AND u.role IN ('admin', 'user')
            """
            writing_result = select_with_query(writing_query)
            writing_count = writing_result[0]["count"] if writing_result else 0
            completed_result = select_with_query(completed_query)
            completed_count = completed_result[0]["count"] if completed_result else 0
            total_questions = get_total_question_count_by_project_ids(project_ids)
        elif role == "master":
            project_ids = get_all_project_ids_master()
            total_projects = len(project_ids)
            # master는 전체 프로젝트 집계
            writing_count = count("projects", {"is_deleted": False, "status": "WRITING"})
            completed_count = count("projects", {"is_deleted": False, "status": "COMPLETED"})
            total_questions = get_total_question_count_by_project_ids(project_ids)
        else:
            project_ids = get_project_ids_for_user(user_id)
            # user, tester는 자기 프로젝트만 집계
            total_projects = len(project_ids)
            writing_count = count("projects", {"is_deleted": False, "status": "WRITING", "user_id": user_id})
            completed_count = count("projects", {"is_deleted": False, "status": "COMPLETED", "user_id": user_id})
            total_questions = get_total_question_count_by_project_ids(project_ids)
            
        summary = DashboardSummary(
            total_projects=total_projects,
            writing_count=writing_count,
            completed_count=completed_count,
            total_questions=total_questions
        )
        
        return DashboardSummaryResponse(
            success=True,
            message="대시보드 요약 조회 성공",
            data=summary
        )
        
    except Exception as e:
        logger.exception("대시보드 요약 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"대시보드 요약 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ===========================
# 프로젝트 목록 API (테이블용)
# ===========================

@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="프로젝트 목록 조회",
    description="대시보드 테이블에 표시할 프로젝트 목록을 조회합니다.",
    tags=["대시보드"]
)
async def get_project_list(
    user_data: tuple[int, str] = Depends(get_current_user),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    status: Optional[str] = Query(None, description="상태 필터 (WRITING, GENERATING, COMPLETED, FAILED)"),
    subject: Optional[str] = Query(None, description="과목 필터"),
    keyword: Optional[str] = Query(None, description="프로젝트명 검색 키워드")
):
    """
    대시보드 테이블에 표시할 프로젝트 목록을 반환합니다.
    
    반환 데이터:
    - 프로젝트명
    - 교과 정보 (학년/학기/출판사)
    - 문항 유형
    - 문항 수
    - 상태
    - 최종 수정일
    """
    user_id, role = user_data

    
    try:
        if role == "admin":
            # 기본 쿼리 구성 (projects와 project_scopes, project_source_config JOIN)
            base_query = """
                SELECT 
                    u.name AS user_name,
                    p.project_id,
                    p.project_name,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    ps.grade,
                    ps.semester,
                    ps.publisher_author,
                    ps.subject,
                    psc.question_type
                FROM projects p
                LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
                LEFT JOIN (
                    SELECT project_id, question_type 
                    FROM project_source_config 
                    WHERE config_id IN (
                        SELECT MAX(config_id) FROM project_source_config GROUP BY project_id
                    )
                ) psc ON p.project_id = psc.project_id
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.is_deleted = FALSE AND u.role in ('admin', 'user')   
            """
            params=[]
        elif role == "master":
            base_query = """
                SELECT 
                    u.name AS user_name,
                    p.project_id,
                    p.project_name,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    ps.grade,
                    ps.semester,
                    ps.publisher_author,
                    ps.subject,
                    psc.question_type
                FROM projects p
                LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
                LEFT JOIN (
                    SELECT project_id, question_type 
                    FROM project_source_config 
                    WHERE config_id IN (
                        SELECT MAX(config_id) FROM project_source_config GROUP BY project_id
                    )
                ) psc ON p.project_id = psc.project_id
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.is_deleted = FALSE
            """
            params=[]
        else:
            # 기본 쿼리 구성 (projects와 project_scopes, project_source_config JOIN)
            base_query = """
                SELECT 
                    p.project_id,
                    p.project_name,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    ps.grade,
                    ps.semester,
                    ps.publisher_author,
                    ps.subject,
                    psc.question_type
                FROM projects p
                LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
                LEFT JOIN (
                    SELECT project_id, question_type 
                    FROM project_source_config 
                    WHERE config_id IN (
                        SELECT MAX(config_id) FROM project_source_config GROUP BY project_id
                    )
                ) psc ON p.project_id = psc.project_id
                WHERE p.user_id = %s AND p.is_deleted = FALSE
            """
            params = [user_id]

        # 상태 필터
        if status and status in ["WRITING", "GENERATING", "COMPLETED", "FAILED"]:
            base_query += " AND p.status = %s"
            params.append(status)
        
        # 과목 필터
        if subject:
            base_query += " AND ps.subject = %s"
            params.append(subject)
        
        # 키워드 검색
        if keyword:
            base_query += " AND p.project_name LIKE %s"
            params.append(f"%{keyword}%")
        
        # 전체 개수 조회를 위한 카운트 쿼리
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as sub"
        count_result = select_with_query(count_query, tuple(params))
        total = count_result[0]["total"] if count_result else 0
        
        # 페이지네이션 및 정렬 적용
        base_query += " ORDER BY p.updated_at DESC LIMIT %s OFFSET %s"
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
        # 프로젝트 목록 조회
        projects = select_with_query(base_query, tuple(params))
        
        # 응답 데이터 구성
        items = []
        for p in projects:
            # 교과 정보 문자열 생성
            curriculum_parts = []
            if p.get("grade"):
                curriculum_parts.append(f"중{p['grade']}")
            if p.get("semester"):
                curriculum_parts.append(f"{p['semester']}학기")
            if p.get("publisher_author"):
                curriculum_parts.append(p["publisher_author"])
            curriculum_info = " / ".join(curriculum_parts) if curriculum_parts else "-"
            
            # 문항 수 조회
            question_cnt = get_question_count_for_project(p["project_id"])
            
            items.append(ProjectListItem(
                user_name=p.get("user_name"),
                project_id=p["project_id"],
                project_name=p["project_name"],
                grade=p.get("grade"),
                semester=p.get("semester"),
                publisher_author=p.get("publisher_author"),
                subject=p.get("subject"),
                curriculum_info=curriculum_info,
                question_type=get_question_type_label(p.get("question_type")),
                question_count=question_cnt,
                status=p["status"] or "WRITING",
                status_label=get_status_label(p["status"] or "WRITING"),
                updated_at=p.get("updated_at"),
                created_at=p.get("created_at")
            ))
        
        # 총 페이지 수 계산
        total_pages = math.ceil(total / limit) if total > 0 else 1
        
        return ProjectListResponse(
            success=True,
            message="프로젝트 목록 조회 성공",
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.exception("프로젝트 목록 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"프로젝트 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ===========================
# 필터 옵션 API
# ===========================

@router.get(
    "/filters",
    response_model=FilterOptionsResponse,
    summary="필터 옵션 조회",
    description="대시보드 필터에 사용할 옵션 목록을 조회합니다.",
    tags=["대시보드"]
)
async def get_filter_options(user_data: tuple[int, str] = Depends(get_current_user)):
    """
    대시보드 필터에 사용할 옵션 목록을 반환합니다.
    
    반환 데이터:
    - 과목 목록
    - 상태 목록
    """
    user_id, role = user_data
    
    try:
        if role == "admin":
            # 사용자의 프로젝트에서 사용된 과목 목록 조회
            subject_query = """
                SELECT DISTINCT ps.subject
                FROM projects p
                JOIN project_scopes ps ON p.scope_id = ps.scope_id
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.is_deleted = FALSE AND ps.subject IS NOT NULL AND u.role in ('admin', 'user')
                ORDER BY ps.subject
            """
            subjects_result = select_with_query(subject_query, tuple([]))       
        elif role == "master":
            subject_query = """
                SELECT DISTINCT ps.subject
                FROM projects p
                JOIN project_scopes ps ON p.scope_id = ps.scope_id
                WHERE p.is_deleted = FALSE AND ps.subject IS NOT NULL
                ORDER BY ps.subject
            """
            subjects_result = select_with_query(subject_query, tuple([]))
        else:
            # 사용자의 프로젝트에서 사용된 과목 목록 조회
            subject_query = """
                SELECT DISTINCT ps.subject
                FROM projects p
                JOIN project_scopes ps ON p.scope_id = ps.scope_id
                WHERE p.user_id = %s AND p.is_deleted = FALSE AND ps.subject IS NOT NULL
                ORDER BY ps.subject
            """
            subjects_result = select_with_query(subject_query, (user_id,))
            
        subjects = [FilterOption(value="all", label="전체 과목")]
        for s in subjects_result:
            if s["subject"]:
                subjects.append(FilterOption(value=s["subject"], label=s["subject"]))
        
        statuses = [
            FilterOption(value="all", label="전체 상태"),
            FilterOption(value="WRITING", label="작성중"),
            FilterOption(value="GENERATING", label="생성중"),
            FilterOption(value="COMPLETED", label="생성완료"),
            FilterOption(value="FAILED", label="생성실패"),
        ]
        
        return FilterOptionsResponse(
            success=True,
            subjects=subjects,
            statuses=statuses
        )
        
    except Exception as e:
        logger.exception("필터 옵션 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"필터 옵션 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ===========================
# 키워드 검색 API
# ===========================

@router.get(
    "/search",
    response_model=ProjectListResponse,
    summary="프로젝트명 검색",
    description="프로젝트명으로 검색합니다.",
    tags=["대시보드"]
)
async def search_projects(
    user_data: tuple[int, str] = Depends(get_current_user),
    keyword: str = Query(..., description="검색 키워드"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수")
):
    """프로젝트명으로 검색합니다."""
    return await get_project_list(
        user_data=user_data,
        page=page,
        limit=limit,
        keyword=keyword
    )


# ===========================
# 기존 API (하위 호환성 유지)
# ===========================

@router.get(
    "/project",
    response_model=ProjectResponse,
    summary="프로젝트 조회",
    description="특정 프로젝트의 정보를 조회합니다.",
    tags=["대시보드"]
)
async def get_project_detail(
    project_id: int,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    user_id, role = user_data
    
    if role == "admin":
        project = get_project_info_admin_dashboard(project_id)

    elif role == "master":
        project = select_one(
            table="projects",
            where={"project_id": project_id, "is_deleted": False}
        )
    else:
        project = select_one(
            table="projects",
            where={"project_id": project_id, "user_id": user_id, "is_deleted": False}
        )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="프로젝트를 찾을 수 없거나 접근 권한이 없습니다."
        )


    config = select_one("project_source_config", {"project_id": project_id})
    
    is_modified = config.get("is_modified", None) if config else None
    resp_kwargs = dict(
        success=True,
        project_id=project["project_id"],
        status=project["status"]
    )

    # 각 상태에 따라 메시지/필드 정리
    if is_modified == 0:
        resp_kwargs.update(
            message="원본 지문을 사용하여 생성 중입니다.",
            is_custom=0,
            passage_id=config.get("passage_id"),
        )
    elif is_modified == 1:
        resp_kwargs.update(
            message="커스텀 지문을 사용하여 생성 중입니다.",
            is_custom=1,
            passage_id=config.get("custom_passage_id"),
        )
    elif is_modified == 2:
        resp_kwargs.update(
            message="지문 없이 생성 중입니다.",
            is_custom=2,
            passage_id=None,
        )
    elif is_modified == 4:
        resp_kwargs.update(
            message="지문 수정중 중단했거나 지문을 선택하지 않았습니다.",
            is_custom=999,
            passage_id=None,
        )
    else:
        resp_kwargs.update(
            message="프로젝트 설정까지만 진행되었습니다.",
            is_custom=999,
            passage_id=None,
        )
    return ProjectResponse(**resp_kwargs)



@router.delete(
    "/delete",
    response_model=SuccessResponse,
    summary="프로젝트 삭제",
    description="특정 프로젝트를 삭제합니다.",
    tags=["대시보드"]
)
async def project_delete(
    project_id: int,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    user_id, role = user_data

    ## 프로젝트 아이디로 업데이트 is_deleted 를 True 로 변경
    update(
        table="projects",
        where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
        data={"is_deleted": True}
    )
    return SuccessResponse(
        success=True,
        message="프로젝트가 성공적으로 삭제되었습니다."
    )