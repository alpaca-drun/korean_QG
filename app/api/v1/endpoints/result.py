from fastapi import APIRouter, HTTPException, status, Query, Depends, BackgroundTasks
from typing import Optional
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile
import os
from urllib.parse import quote

from app.download.dev import fill_table_from_list, get_question_data_from_db
from app.db.database import select_one, update, select_with_query, get_db_connection
from app.db.generate import get_project_all_questions
from app.schemas.curriculum import (
    ListResponse, 
    SelectSaveResultRequest,
    SelectSaveResultResponse,
    QuestionMetaUpdateRequest,
    QuestionMetaUpdateResponse,
    QuestionMetaBatchUpdateRequest,
    ProjectMetaResponse,
    ProjectPassageResponse,
    ProjectPassageItem,
)

from app.utils.dependencies import get_current_user
from app.core.logger import logger
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
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    project_id를 기반으로 문항 리스트를 반환합니다.
    question_type을 제공하지 않으면 모든 타입의 문항을 반환합니다.
    """
    user_id, role = user_data

    if role == "admin":
        project = select_one(
            "projects",
            where={"project_id": project_id, "is_deleted": False},
            columns="project_id",
        )
    else:
        project = select_one(
            "projects",
            where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
            columns="project_id",
        )

    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")

    config = select_one(
        "project_source_config",
        where={"project_id": project_id},
        columns="is_modified",
        order_by="config_id DESC"
    )
    if not config:
        raise HTTPException(status_code=404, detail="프로젝트 설정을 찾을 수 없습니다. (권한 없음 또는 삭제됨)")



    items = get_project_all_questions(project_id=project_id)
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
async def save_selected_results(request: QuestionMetaBatchUpdateRequest, user_data: tuple[int, str] = Depends(get_current_user)):
    """
    여러 문항의 메타데이터를 한 번에 업데이트합니다.
    question_type은 자동으로 판단됩니다.
    
    **요청 형식:**
    ```json
    {
      "items": [
        {
          "project_id": 1,
          "question_id": 2,
          "feedback_score": 4.5,
          "is_checked": 1,
          "modified_difficulty": "상"
        },
        {
          "project_id": 1,
          "question_id": 4,
          "feedback_score": 3.0,
          "is_checked": 1,
          "modified_difficulty": "중"
        }
      ]
    }
    ```
    """
    user_id, role = user_data
    
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
    question_type = select_one(
        "project_source_config",
        where={"project_id": project_id},
        columns="question_type",
        order_by="config_id DESC"
    )
    if not project:
        return QuestionMetaUpdateResponse(
            success=False,
            message="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)",
            updated_count=0,
            failed_count=len(request.items),
            results=[]
        )
    if question_type == "5지선다":
        table_configs = [
            ("multiple_choice_questions", "question_id", "multiple_choice"),
        ]
    elif question_type == "단답형":
    # 테이블/PK 매핑 (question_id로 테이블 자동 판단)
        table_configs = [
            ("short_answer_questions", "short_question_id", "short_answer"),
        ]
    else:
        table_configs = [
            ("multiple_choice_questions", "question_id", "multiple_choice"),
            ("short_answer_questions", "short_question_id", "short_answer"),
            ("ox_questions", "ox_question_id", "true_false"),
        ]
    
    # 각 문항 업데이트 (단일 트랜잭션으로 처리)
    results = []
    updated_count = 0
    failed_count = 0
    
    try:
        with get_db_connection() as connection:
            for item in request.items:
                try:
                    # project_id와 question_id로 어떤 테이블에 있는지 찾기
                    found_table = None
                    found_pk = None
                    found_question_type = None
                    
                    for table, pk, question_type in table_configs:
                        # 각 테이블에서 question_id로 조회
                        check_query = f"SELECT {pk} FROM {table} WHERE {pk} = %s AND project_id = %s LIMIT 1"
                        check_result = select_with_query(check_query, (item.question_id, item.project_id), connection=connection)
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
                        connection=connection
                    )
                    
                    if updated <= 0:
                        results.append({
                            "question_id": item.question_id,
                            "question_type": found_question_type,
                            "success": False,
                            "message": "기존과 값이 동일하여 업데이트되지 않았습니다."
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
                    logger.exception("문항 메타 업데이트 중 오류 (question_id=%s)", item.question_id)
                    results.append({
                        "question_id": item.question_id,
                        "success": False,
                        "message": f"업데이트 중 오류 발생: {str(e)}"
                    })
                    failed_count += 1
            # 트랜잭션 성공 시 자동 commit (context manager에서 처리)
    except Exception as e:
        logger.exception("배치 업데이트 트랜잭션 실패")
        return QuestionMetaUpdateResponse(
            success=False,
            message=f"배치 업데이트 실패: {str(e)}",
            updated_count=0,
            failed_count=len(request.items),
            results=[]
        )
    
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
async def update_selected_results(request: QuestionMetaUpdateRequest, user_data: tuple[int, str] = Depends(get_current_user)):
    user_id, role = user_data

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
    user_data: tuple[int, str] = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
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
    user_id, role = user_data


    if role == "admin":
        # 프로젝트 정보와 카테고리(subject) 조회
        project_query = """
            SELECT 
                p.project_id,
                p.project_name,
                ps.subject as category
            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            LEFT JOIN project_source_config psc ON psc.config_id = (
                SELECT MAX(config_id)
                FROM project_source_config
                WHERE project_id = p.project_id
            )
            WHERE p.project_id = %s AND p.is_deleted = FALSE
        """
    else:
        # 프로젝트 정보와 카테고리(subject) 조회
        project_query = """
            SELECT 
                p.project_id,
                p.project_name,
                ps.subject as category
            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            LEFT JOIN project_source_config psc ON psc.config_id = (
                SELECT MAX(config_id)
                FROM project_source_config
                WHERE project_id = p.project_id
            )
            WHERE p.project_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
        """
    download_params = (project_id,) if role == "admin" else (project_id, user_id)
    project_result = select_with_query(project_query, download_params)
    
    if not project_result:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")
    
    project_info = project_result[0]
    category = project_info.get("category") or ""  # subject가 없으면 빈 문자열

    # 데이터 조회
    try:
        # 내부에서도 user_id로 한번 더 검증/필터링
        data_list = get_question_data_from_db(project_id, user_id=user_id)
    except Exception as e:
        logger.exception("문항 조회 실패 (project_id=%s)", project_id)
        raise HTTPException(status_code=500, detail=f"문항 조회 실패: {str(e)}")

    if not data_list:
        raise HTTPException(status_code=404, detail=f"project_id={project_id}에 해당하는 문항이 없습니다.")

    # 임시 파일 생성 후 docx 저장
    out_dir = Path("/app/downloads_tmp")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{project_info.get('project_name')}.docx"

    try:
        fill_table_from_list(str(template_path), str(out_path), data_list, category=category)
    except Exception as e:
        logger.exception("DOCX 생성 실패 (project_id=%s)", project_id)
        raise HTTPException(status_code=500, detail=f"DOCX 생성 실패: {str(e)}")

    # 파일명 인코딩 (한글 깨짐 방지)
    project_name = project_info.get('project_name') or "download"
    encoded_filename = quote(f"{project_name}.docx")

    # 파일 전송 후 삭제 예약
    background_tasks.add_task(os.remove, str(out_path))

    return FileResponse(
        path=str(out_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{project_name}.docx",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
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
    user_data: tuple[int, str] = Depends(get_current_user)
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
    user_id, role = user_data
    if role == "admin":
        # 프로젝트 소유권 확인 및 메타정보 조회
        project_query = """
            SELECT 
                p.project_id,
                p.project_name,

                ps.grade,
                ps.semester,
                ps.subject,
                ps.publisher_author,
                ps.large_unit_name,
                ps.small_unit_name,

                IFNULL(psc.question_type, '프로젝트타입') as question_type,

                IFNULL(psc.target_count, 0) as target_count,
                IFNULL(psc.additional_prompt, "") as additional_prompt,
                IFNULL(psc.stem_directive, "") as stem_directive

            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            LEFT JOIN project_source_config psc ON psc.config_id = (
                SELECT MAX(config_id)
                FROM project_source_config
                WHERE project_id = p.project_id
            )
            WHERE p.project_id = %s AND p.is_deleted = FALSE
        """
    else:
        # 프로젝트 소유권 확인 및 메타정보 조회
        project_query = """
            SELECT 
                p.project_id,
                p.project_name,

                ps.grade,
                ps.semester,
                ps.subject,
                ps.publisher_author,
                ps.large_unit_name,
                ps.small_unit_name,

                IFNULL(psc.question_type, '프로젝트타입') as question_type,

                IFNULL(psc.target_count, 0) as target_count,
                IFNULL(psc.additional_prompt, "") as additional_prompt,
                IFNULL(psc.stem_directive, "") as stem_directive

            FROM projects p
            LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
            LEFT JOIN project_source_config psc ON psc.config_id = (
                SELECT MAX(config_id)
                FROM project_source_config
                WHERE project_id = p.project_id
            )
            WHERE p.project_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
        """
    params = (project_id,) if role == "admin" else (project_id, user_id)
    project_result = select_with_query(project_query, params)
    
    if not project_result:
        return ProjectMetaResponse(success=False, message="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)", project_id=0, grade=None, semester=None, subject=None, publisher_author=None, large_unit_name=None, small_unit_name=None, target_count=None, additional_prompt=None, stem_directive=None)
    
    project_info = project_result[0]
    
    return ProjectMetaResponse(
        success=True,
        message="프로젝트 메타정보 조회 성공",
        project_id=project_info.get("project_id"),
        project_name=project_info.get("project_name"),
        grade=str(project_info.get("grade")) if project_info.get("grade") is not None else None,
        semester=str(project_info.get("semester")) if project_info.get("semester") is not None else None,
        subject=project_info.get("subject"),
        publisher_author=project_info.get("publisher_author"),
        large_unit_name=project_info.get("large_unit_name"),
        small_unit_name=project_info.get("small_unit_name"),
        question_type=project_info.get("question_type"),
        target_count=project_info.get("target_count"),
        additional_prompt=project_info.get("additional_prompt"),
        stem_directive=project_info.get("stem_directive")
    )


@router.get(
    "/passage",
    response_model=ProjectPassageResponse,
    summary="프로젝트에서 사용된 지문 목록 조회",
    description="project_id를 기준으로 해당 프로젝트에서 사용된 지문 목록을 조회합니다.",
    tags=["결과 관리"]
)
async def get_project_passages(
    project_id: int = Query(..., description="프로젝트 ID", example=1),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    project_id를 기반으로 해당 프로젝트에서 사용된 지문 목록을 반환합니다.
    
    반환 정보:
    - passage_id: 원본 지문 ID (원본인 경우)
    - custom_passage_id: 커스텀 지문 ID (커스텀인 경우)
    - title: 지문 제목
    - content: 지문 내용W
    - auth: 저자
    - is_custom: 0(원본) 또는 1(커스텀)
    """
    user_id, role = user_data
    # 프로젝트 소유권 확인
    if role == "admin":
        project = select_one(
            "projects",
            where={"project_id": project_id, "is_deleted": False},
            columns="project_id",
        )
    else:
        project = select_one(
            "projects",
            where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
            columns="project_id",
        )
        
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")
    
    config_data = select_one(
        "project_source_config",
        where={"project_id": project_id},
        columns="config_id, is_modified, passage_id, custom_passage_id",
    )


    if not config_data:
        return ProjectPassageResponse(success=False, message="프로젝트에서 사용된 지문 목록 조회 실패", items=[], total=0)
    

    # 프로젝트에서 사용된 지문 조회
    passage_query = """
        SELECT 
            CASE
                WHEN psc.is_modified = 0 THEN psc.passage_id
                WHEN psc.is_modified = 1 THEN psc.custom_passage_id
                ELSE NULL
            END as passage_id,
            CASE
                WHEN psc.is_modified = 0 THEN p.title
                WHEN psc.is_modified = 1 THEN pc.title
                ELSE NULL
            END as title,
            CASE
                WHEN psc.is_modified = 0 THEN p.context
                WHEN psc.is_modified = 1 THEN pc.context
                ELSE NULL
            END as content,
            CASE
                WHEN psc.is_modified = 0 THEN p.auth
                WHEN psc.is_modified = 1 THEN pc.auth
                ELSE NULL
            END as auth,
            CASE 
                WHEN psc.is_modified = 0 THEN 0
                WHEN psc.is_modified = 1 THEN 1
                ELSE NULL
            END as is_custom
            
        FROM project_source_config psc
        LEFT JOIN passages p ON psc.passage_id = p.passage_id
        LEFT JOIN passage_custom pc ON psc.custom_passage_id = pc.custom_passage_id
        WHERE psc.project_id = %s
        AND (psc.passage_id IS NOT NULL OR psc.custom_passage_id IS NOT NULL)
        ORDER BY psc.config_id DESC
        LIMIT 1
    """
    passage_results = select_with_query(passage_query, (project_id,))
    
    if not passage_results:
        return ProjectPassageResponse(success=False, message="프로젝트에서 사용된 지문 목록 조회 실패", items=[], total=0)
    
    # 중복 제거 (같은 지문이 여러 번 사용될 수 있으므로)
    seen = set()
    unique_passages = []
    for passage in passage_results:
        # passage_id 또는 custom_passage_id를 기준으로 중복 제거
        key = (passage.get("passage_id"), passage.get("custom_passage_id"))
        if key not in seen:
            seen.add(key)
            unique_passages.append(passage)
    
    # 스키마에 맞게 변환
    items = [
        ProjectPassageItem(
            passage_id=passage.get("passage_id"),
            title=passage.get("title") or "",
            content=passage.get("content") or "",
            auth=passage.get("auth"),
            is_custom=passage.get("is_custom") or 0
        )
        for passage in unique_passages
    ]
    
    return ProjectPassageResponse(
        success=True, 
        message="프로젝트에서 사용된 지문 목록 조회 성공", 
        items=items, 
        total=len(items)
        )
