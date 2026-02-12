from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===========================
# 상단 통계 카드용 스키마
# ===========================

class DashboardSummary(BaseModel):
    """대시보드 상단 요약 통계"""
    total_projects: int = Field(default=0, description="전체 프로젝트 수")
    writing_count: int = Field(default=0, description="작성중 프로젝트 수")
    completed_count: int = Field(default=0, description="생성완료 프로젝트 수")
    total_questions: int = Field(default=0, description="총 생성 문항 수")


class DashboardSummaryResponse(BaseModel):
    """대시보드 요약 통계 API 응답"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="대시보드 요약 조회 성공", description="메시지")
    data: DashboardSummary = Field(..., description="대시보드 요약 데이터")


# ===========================
# 프로젝트 목록용 스키마
# ===========================

class ProjectListItem(BaseModel):
    """프로젝트 목록 아이템"""
    #프로젝트 소유자명
    user_name: Optional[str] = Field(None, description="프로젝트 소유자명")
    project_id: int = Field(..., description="프로젝트 ID")
    project_name: str = Field(..., description="프로젝트명")
    
    # 교과 정보
    grade: Optional[int] = Field(None, description="학년")
    semester: Optional[int] = Field(None, description="학기")
    publisher_author: Optional[str] = Field(None, description="출판사/저자")
    subject: Optional[str] = Field(None, description="교과목")
    curriculum_info: Optional[str] = Field(None, description="교과 정보 (학년/학기/출판사)")
    
    # 문항 정보
    question_type: Optional[str] = Field(None, description="문항 유형 (5지선다형, 단답형 등)")
    question_count: int = Field(default=0, description="문항 수")
    
    # 상태 및 일시
    status: str = Field(default="WRITING", description="상태 (WRITING, GENERATING, COMPLETED, FAILED)")
    status_label: str = Field(default="알 수 없음", description="상태 라벨")
    updated_at: Optional[datetime] = Field(None, description="최종 수정일")
    created_at: Optional[datetime] = Field(None, description="생성일시")


class ProjectListResponse(BaseModel):
    """프로젝트 목록 API 응답"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="프로젝트 목록 조회 성공", description="메시지")
    items: List[ProjectListItem] = Field(default_factory=list, description="프로젝트 목록")
    total: int = Field(default=0, description="총 프로젝트 수")
    page: int = Field(default=1, description="현재 페이지")
    limit: int = Field(default=10, description="페이지당 항목 수")
    total_pages: int = Field(default=1, description="총 페이지 수")


# ===========================
# 필터 옵션용 스키마
# ===========================

class FilterOption(BaseModel):
    """필터 옵션"""
    value: str = Field(..., description="옵션 값")
    label: str = Field(..., description="옵션 라벨")


class FilterOptionsResponse(BaseModel):
    """필터 옵션 API 응답"""
    success: bool = Field(default=True, description="성공 여부")
    subjects: List[FilterOption] = Field(default_factory=list, description="과목 목록")
    statuses: List[FilterOption] = Field(
        default=[
            FilterOption(value="all", label="전체 상태"),
            FilterOption(value="WRITING", label="작성중"),
            FilterOption(value="GENERATING", label="생성중"),
            FilterOption(value="COMPLETED", label="생성완료"),
            FilterOption(value="FAILED", label="생성실패"),
        ],
        description="상태 목록"
    )


# ===========================
# 기존 스키마 (하위 호환성 유지)
# ===========================

class ProjectStatusCount(BaseModel):
    """프로젝트 상태별 개수"""
    writing: int = Field(default=0, description="작성중 프로젝트 수")
    generating: int = Field(default=0, description="생성중 프로젝트 수")
    completed: int = Field(default=0, description="완료된 프로젝트 수")
    failed: int = Field(default=0, description="실패한 프로젝트 수")

class QuestionTypeCount(BaseModel):
    """문항 유형별 개수"""
    multiple_choice: int = Field(default=0, description="객관식 문항 수")
    true_false: int = Field(default=0, description="OX 문항 수")
    short_answer: int = Field(default=0, description="단답형 문항 수")
    matching: int = Field(default=0, description="선긋기 문항 수")
    total: int = Field(default=0, description="총 문항 수")


class TokenUsage(BaseModel):
    """토큰 사용량"""
    total_input_tokens: int = Field(default=0, description="총 입력 토큰")
    total_output_tokens: int = Field(default=0, description="총 출력 토큰")
    total_tokens: int = Field(default=0, description="총 토큰 사용량")


class RecentProject(BaseModel):
    """최근 프로젝트 정보"""
    project_id: int = Field(..., description="프로젝트 ID")
    project_name: str = Field(..., description="프로젝트명")
    status: str = Field(..., description="상태")
    question_count: int = Field(default=0, description="생성된 문항 수")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")


class DashboardStats(BaseModel):
    """대시보드 통계 응답"""
    total_projects: int = Field(default=0, description="총 프로젝트 수")
    project_status: ProjectStatusCount = Field(
        default_factory=ProjectStatusCount, 
        description="프로젝트 상태별 개수"
    )
    question_count: QuestionTypeCount = Field(
        default_factory=QuestionTypeCount, 
        description="문항 유형별 개수"
    )
    token_usage: TokenUsage = Field(
        default_factory=TokenUsage, 
        description="토큰 사용량"
    )
    recent_projects: List[RecentProject] = Field(
        default_factory=list, 
        description="최근 프로젝트 목록 (최대 5개)"
    )
    avg_feedback_score: Optional[float] = Field(None, description="평균 품질 평가 점수")


class DashboardResponse(BaseModel):
    """대시보드 API 응답"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="대시보드 데이터 조회 성공", description="메시지")
    data: DashboardStats = Field(..., description="대시보드 통계 데이터")


class ProjectDetailStats(BaseModel):
    """개별 프로젝트 상세 통계"""
    project_id: int = Field(..., description="프로젝트 ID")
    project_name: str = Field(..., description="프로젝트명")
    status: str = Field(..., description="상태")
    question_count: QuestionTypeCount = Field(
        default_factory=QuestionTypeCount, 
        description="문항 유형별 개수"
    )
    token_usage: TokenUsage = Field(
        default_factory=TokenUsage, 
        description="토큰 사용량"
    )
    avg_feedback_score: Optional[float] = Field(None, description="평균 품질 평가 점수")
    used_question_count: int = Field(default=0, description="사용된 문항 수")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")


class ProjectDetailResponse(BaseModel):
    """프로젝트 상세 통계 API 응답"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="프로젝트 상세 통계 조회 성공", description="메시지")
    data: ProjectDetailStats = Field(..., description="프로젝트 상세 통계")





class ProjectResponse(BaseModel):
    """프로젝트 정보 API 응답"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="프로젝트 정보 조회 성공", description="메시지")
    project_id: int = Field(..., description="프로젝트 ID")
    status: str = Field(..., description="상태")
    
    config_id: Optional[int] = Field(None, description="설정 ID")
    is_custom: Optional[int] = Field(None, description="지문 변형 여부 (0: 원본, 1: 변형, 2: 지문없음)")
    passage_id: Optional[int] = Field(None, description="사용된 지문 ID")


class SuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="요청이 성공적으로 처리되었습니다.", description="메시지")