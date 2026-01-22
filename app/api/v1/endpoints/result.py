from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile

from app.download.dev import fill_table_from_list, get_question_data_from_db
from app.db.database import select_one, update
from app.db.generate import get_project_all_questions
from app.schemas.curriculum import (
    ListResponse, 
    SelectSaveResultRequest,
    SelectSaveResultResponse,
    QuestionMetaUpdateRequest,
    QuestionMetaUpdateResponse
)
from app.utils.dependencies import get_current_user
router = APIRouter()


@router.get(
    "/list",
    response_model=ListResponse,
    summary="결과 리스트 조회",
    description="project_id를 기준으로 프로젝트의 문항(객관식/OX/단답형)을 통합 조회합니다.",
    tags=["결과 관리"]
)
async def get_result(
    project_id: int = Query(..., description="프로젝트 ID", example=1),
    question_type: str = Query("all", description="문항 타입 필터 (multiple_choice/true_false/short_answer/all)"),
    current_user_id: str = Depends(get_current_user)
):
    """
    project_id를 기반으로 문항 리스트를 반환합니다.
    """
    user_id = int(current_user_id)
    project = select_one(
        "projects",
        where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
        columns="project_id",
    )
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")

    items = get_project_all_questions(project_id)
    if question_type and question_type != "all":
        items = [q for q in items if q.get("question_type") == question_type]

    return ListResponse(items=items or [], total=len(items or []))





@router.post(
    "/save",
    response_model=QuestionMetaUpdateResponse,
    summary="문항 메타데이터 저장(=업데이트)",
    description="save와 update는 동일 기능입니다. feedback_score/is_used/modified_difficulty/modified_passage를 업데이트합니다.",
    tags=["결과 관리"]
)
async def save_selected_results(request: QuestionMetaUpdateRequest, current_user_id: str = Depends(get_current_user)):
    # save는 update의 별칭
    return await update_selected_results(request, current_user_id)


# @router.put(
#     "/update",
#     response_model=QuestionMetaUpdateResponse,
#     summary="문항 메타데이터 수정",
#     description="feedback_score/is_used/modified_difficulty/modified_passage를 업데이트합니다.",
#     tags=["결과 관리"]
# )
async def update_selected_results(request: QuestionMetaUpdateRequest, current_user_id: str = Depends(get_current_user)):
    user_id = int(current_user_id)

    # 프로젝트 소유권 확인
    project = select_one(
        "projects",
        where={"project_id": request.project_id, "user_id": user_id, "is_deleted": False},
        columns="project_id",
    )
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")

    # 업데이트 데이터 구성 (전달된 값만)
    data = {}
    if request.feedback_score is not None:
        data["feedback_score"] = request.feedback_score
    if request.is_used is not None:
        data["is_used"] = int(request.is_used)
    if request.modified_difficulty is not None:
        data["modified_difficulty"] = request.modified_difficulty
    if request.modified_passage is not None:
        data["modified_passage"] = request.modified_passage

    if not data:
        return QuestionMetaUpdateResponse(success=False, message="업데이트할 값이 없습니다.", updated_count=0)

    # 테이블/PK 매핑
    table_map = {
        "multiple_choice": ("multiple_choice_questions", "question_id"),
        "true_false": ("true_false_questions", "ox_question_id"),
        "short_answer": ("short_answer_questions", "short_question_id"),
    }
    if request.question_type not in table_map:
        raise HTTPException(status_code=422, detail="question_type은 multiple_choice/true_false/short_answer 중 하나여야 합니다.")

    table, pk = table_map[request.question_type]

    # project_id까지 where에 포함해 타 프로젝트 문항 업데이트 방지
    updated_count = update(
        table=table,
        data=data,
        where={pk: request.question_id, "project_id": request.project_id},
    )

    if updated_count <= 0:
        return QuestionMetaUpdateResponse(success=False, message="업데이트 대상 문항을 찾을 수 없습니다.", updated_count=0)

    return QuestionMetaUpdateResponse(success=True, message="업데이트 완료", updated_count=updated_count)


@router.get(
    "/download",
    summary="프로젝트 문항 DOCX 다운로드",
    description="project_id 기준으로 문항을 조회하여 sample3.docx 양식으로 DOCX 파일을 생성/다운로드합니다.",
    tags=["결과 관리"]
)
async def download_selected_results(
    project_id: int = Query(..., description="프로젝트 ID", example=1),
    category: str = Query("", description="문서 상단 {category} 치환 값", example="말하기듣기"),
    current_user_id: str = Depends(get_current_user)
):
    """
    project_id로 문항을 조회하여 docx 파일로 반환합니다.
    """
    # 템플릿 경로 (app/download/sample3.docx)
    template_path = Path(__file__).resolve().parents[3] / "download" / "sample3.docx"
    if not template_path.exists():
        raise HTTPException(status_code=500, detail=f"템플릿 파일을 찾을 수 없습니다: {template_path}")

    # ✅ 프로젝트 소유권 확인 (현재 로그인 사용자만 접근 가능)
    user_id = int(current_user_id)
    project = select_one("projects", where={"project_id": project_id, "user_id": user_id, "is_deleted": False}, columns="project_id")
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")

    # 데이터 조회
    try:
        # 내부에서도 user_id로 한번 더 검증/필터링
        data_list = get_question_data_from_db(project_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문항 조회 실패: {str(e)}")

    if not data_list:
        raise HTTPException(status_code=404, detail=f"project_id={project_id}에 해당하는 문항이 없습니다.")

    # 임시 파일 생성 후 docx 저장
    out_dir = Path(tempfile.gettempdir())
    out_path = out_dir / f"output-project-{project_id}.docx"

    try:
        fill_table_from_list(str(template_path), str(out_path), data_list, category=category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX 생성 실패: {str(e)}")

    return FileResponse(
        path=str(out_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"output-project-{project_id}.docx",
    )