from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile

from app.download.dev import fill_table_from_list, get_question_data_from_db
from app.db.database import select_one, update, select_with_query
from app.db.generate import get_project_all_questions
from app.schemas.curriculum import (
    ListResponse, 
    SelectSaveResultRequest,
    SelectSaveResultResponse,
    QuestionMetaUpdateRequest,
    QuestionMetaUpdateResponse,
    QuestionMetaBatchUpdateRequest,
    ProjectMetaResponse
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
    question_type: Optional[str] = Query(None, description="문항 타입 필터 (multiple_choice/true_false/short_answer). 제공하지 않으면 모든 타입을 반환합니다."),
    current_user_id: str = Depends(get_current_user)
):
    """
    project_id를 기반으로 문항 리스트를 반환합니다.
    question_type을 제공하지 않으면 모든 타입의 문항을 반환합니다.
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
    # question_type이 제공된 경우에만 필터링
    if question_type:
        items = [q for q in items if q.get("question_type") == question_type]

    return ListResponse(items=items or [], total=len(items or []))





@router.post(
    "/save",
    response_model=QuestionMetaUpdateResponse,
    summary="문항 메타데이터 일괄 저장(=업데이트)",
    description="여러 문항의 메타데이터를 한 번에 업데이트합니다. feedback_score/is_checked/modified_difficulty를 업데이트합니다. question_type은 자동으로 판단됩니다.",
    tags=["결과 관리"]
)
async def save_selected_results(request: QuestionMetaBatchUpdateRequest, current_user_id: str = Depends(get_current_user)):
    """
    여러 문항의 메타데이터를 한 번에 업데이트합니다.
    question_type은 자동으로 판단됩니다.
    
    **요청 형식:**
    ```json
    {
      "items": [
        {
          "project_id": 1,
          "question_id": 123,
          "feedback_score": 8.5,
          "is_checked": 1,
          "modified_difficulty": "상"
        },
        {
          "project_id": 1,
          "question_id": 456,
          "feedback_score": 7.0,
          "is_checked": 1
        }
      ]
    }
    ```
    """
    user_id = int(current_user_id)
    
    if not request.items:
        return QuestionMetaUpdateResponse(
            success=False,
            message="업데이트할 문항이 없습니다.",
            updated_count=0,
            failed_count=0,
            results=[]
        )
    
    # 프로젝트 소유권 확인 (모든 문항이 같은 project_id를 가져야 함)
    project_ids = set(item.project_id for item in request.items)
    if len(project_ids) > 1:
        return QuestionMetaUpdateResponse(
            success=False,
            message="모든 문항은 같은 project_id를 가져야 합니다.",
            updated_count=0,
            failed_count=len(request.items),
            results=[]
        )
    
    project_id = list(project_ids)[0]
    project = select_one(
        "projects",
        where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
        columns="project_id",
    )
    if not project:
        return QuestionMetaUpdateResponse(
            success=False,
            message="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)",
            updated_count=0,
            failed_count=len(request.items),
            results=[]
        )
    
    # 테이블/PK 매핑 (question_id로 테이블 자동 판단)
    table_configs = [
        ("multiple_choice_questions", "question_id", "multiple_choice"),
        ("true_false_questions", "ox_question_id", "true_false"),
        ("short_answer_questions", "short_question_id", "short_answer"),
    ]
    
    # 각 문항 업데이트
    results = []
    updated_count = 0
    failed_count = 0
    
    for item in request.items:
        try:
            # project_id와 question_id로 어떤 테이블에 있는지 찾기
            found_table = None
            found_pk = None
            found_question_type = None
            
            for table, pk, question_type in table_configs:
                # 각 테이블에서 question_id로 조회
                check_query = f"SELECT {pk} FROM {table} WHERE {pk} = %s AND project_id = %s LIMIT 1"
                check_result = select_with_query(check_query, (item.question_id, item.project_id))
                if check_result:
                    found_table = table
                    found_pk = pk
                    found_question_type = question_type
                    break
            
            if not found_table:
                results.append({
                    "question_id": item.question_id,
                    "success": False,
                    "message": "해당 question_id를 가진 문항을 찾을 수 없습니다."
                })
                failed_count += 1
                continue
            
            # 업데이트 데이터 구성 (전달된 값만)
            data = {}
            if item.feedback_score is not None:
                data["feedback_score"] = item.feedback_score
            if item.is_checked is not None:
                data["is_checked"] = int(item.is_checked)
            if item.modified_difficulty is not None:
                data["modified_difficulty"] = item.modified_difficulty
            
            if not data:
                results.append({
                    "question_id": item.question_id,
                    "success": False,
                    "message": "업데이트할 값이 없습니다."
                })
                failed_count += 1
                continue
            
            # project_id까지 where에 포함해 타 프로젝트 문항 업데이트 방지
            updated = update(
                table=found_table,
                data=data,
                where={found_pk: item.question_id, "project_id": item.project_id},
            )
            
            if updated <= 0:
                results.append({
                    "question_id": item.question_id,
                    "question_type": found_question_type,
                    "success": False,
                    "message": "업데이트 대상 문항을 찾을 수 없습니다."
                })
                failed_count += 1
            else:
                results.append({
                    "question_id": item.question_id,
                    "question_type": found_question_type,
                    "success": True,
                    "message": "업데이트 완료"
                })
                updated_count += 1
                
        except Exception as e:
            results.append({
                "question_id": item.question_id,
                "success": False,
                "message": f"업데이트 중 오류 발생: {str(e)}"
            })
            failed_count += 1
    
    return QuestionMetaUpdateResponse(
        success=updated_count > 0,
        message=f"{updated_count}개 문항 업데이트 완료, {failed_count}개 실패",
        updated_count=updated_count,
        failed_count=failed_count,
        results=results
    )


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
    description="project_id 기준으로 문항을 조회하여 sample3.docx 양식으로 DOCX 파일을 생성/다운로드합니다. 카테고리는 DB에서 자동으로 조회합니다.",
    tags=["결과 관리"]
)
async def download_selected_results(
    project_id: int = Query(..., description="프로젝트 ID", example=1),
    current_user_id: str = Depends(get_current_user)
):
    """
    project_id로 문항을 조회하여 docx 파일로 반환합니다.
    카테고리는 project_scopes 테이블의 subject 필드에서 자동으로 조회합니다.
    """
    # 템플릿 경로 (app/download/sample3.docx)
    template_path = Path(__file__).resolve().parents[3] / "download" / "sample3.docx"
    if not template_path.exists():
        raise HTTPException(status_code=500, detail=f"템플릿 파일을 찾을 수 없습니다: {template_path}")

    # ✅ 프로젝트 소유권 확인 및 카테고리 조회
    user_id = int(current_user_id)
    
    # 프로젝트 정보와 카테고리(subject) 조회
    project_query = """
        SELECT 
            p.project_id,
            ps.subject as category
        FROM projects p
        LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
        WHERE p.project_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
    """
    project_result = select_with_query(project_query, (project_id, user_id))
    
    if not project_result:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")
    
    project_info = project_result[0]
    category = project_info.get("category") or ""  # subject가 없으면 빈 문자열

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


@router.get(
    "/meta",
    response_model=ProjectMetaResponse,
    summary="프로젝트 메타정보 조회",
    description="project_id를 기준으로 프로젝트의 설정 정보(학년, 학기, 교과목, 출판사, 대단원, 소단원)를 조회합니다.",
    tags=["결과 관리"]
)
async def get_project_meta(
    project_id: int = Query(..., description="프로젝트 ID", example=1),
    current_user_id: str = Depends(get_current_user)
):
    """
    project_id를 기반으로 프로젝트의 메타정보를 반환합니다.
    
    반환 정보:
    - 학년 (grade)
    - 학기 (semester)
    - 교과목 (subject)
    - 출판사/저자 (publisher_author)
    - 대단원 (large_unit_name)
    - 소단원 (small_unit_name)
    """
    user_id = int(current_user_id)
    
    # 프로젝트 소유권 확인 및 메타정보 조회
    project_query = """
        SELECT 
            p.project_id,
            ps.grade,
            ps.semester,
            ps.subject,
            ps.publisher_author,
            ps.large_unit_name,
            ps.small_unit_name
        FROM projects p
        LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
        WHERE p.project_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
    """
    project_result = select_with_query(project_query, (project_id, user_id))
    
    if not project_result:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")
    
    project_info = project_result[0]
    
    return ProjectMetaResponse(
        project_id=project_info.get("project_id"),
        grade=project_info.get("grade"),
        semester=project_info.get("semester"),
        subject=project_info.get("subject"),
        publisher_author=project_info.get("publisher_author"),
        large_unit_name=project_info.get("large_unit_name"),
        small_unit_name=project_info.get("small_unit_name")
    )