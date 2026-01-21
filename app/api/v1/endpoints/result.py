from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile

from app.download.dev import fill_table_from_list, get_question_data_from_db
from app.db.database import select_one
from app.schemas.curriculum import (
    ListResponse, 
    SelectSaveResultRequest,
    SelectSaveResultResponse
)
from app.utils.dependencies import get_current_user
router = APIRouter()


# 더미 데이터 - 생성된 결과 목록 (추후 DB 조회로 변경 예정)
DUMMY_GENERATED_RESULTS = [
    {"id": 1, "name": "생성된 문항 1", "content": "문항 내용 1", "status": "pending"},
    {"id": 2, "name": "생성된 문항 2", "content": "문항 내용 2", "status": "pending"},
    {"id": 3, "name": "생성된 문항 3", "content": "문항 내용 3", "status": "pending"},
    {"id": 4, "name": "생성된 문항 4", "content": "문항 내용 4", "status": "pending"},
]

# 더미 데이터 - 저장된 결과 목록
DUMMY_SAVED_RESULTS = []



@router.get(
    "/list",
    response_model=ListResponse,
    summary="결과 리스트 조회",
    description="결과 아이디를 바탕으로 리스트를 조회합니다.",
    tags=["결과 관리"]
)
async def get_result(
    result_id: int = Query(..., description="결과 ID", example=1), 
    current_user_id: str = Depends(get_current_user)
):
    """
    결과 ID를 기반으로 결과 리스트를 반환합니다.
    
    추후 DB 조회로 변경 예정입니다.
    """
    # ✅ 임시 권한 체크:
    # 현재는 result 관련 테이블이 없어 더미 데이터를 반환하므로,
    # result_id를 project_id로 간주하여 해당 프로젝트 소유자인지 확인합니다.
    user_id = int(current_user_id)
    project = select_one(
        "projects",
        where={"project_id": result_id, "user_id": user_id, "is_deleted": False},
        columns="project_id",
    )
    if not project:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다. (권한 없음 또는 삭제됨)")

    # TODO: DB 조회로 변경
    filtered_results = [
        result for result in DUMMY_GENERATED_RESULTS 
        if result["id"] == result_id
    ]
    
    if not filtered_results:
        raise HTTPException(
            status_code=404,
            detail=f"결과 ID {result_id}에 해당하는 결과를 찾을 수 없습니다."
        )

    return ListResponse(items=filtered_results, total=len(filtered_results))





@router.post(
    "/save",
    response_model=SelectSaveResultRequest,
    summary="선택한 결과 저장",
    description="선택한 결과들을 DB에 저장합니다.",
    tags=["결과 관리"]
)
async def save_selected_results(request: SelectSaveResultRequest, current_user_id: str = Depends(get_current_user)):
    """
    선택한 결과들을 DB에 저장합니다.
    
    - **result_ids**: 저장할 결과 ID 리스트
    
    **성공 시:**
    ```json
    {
        "success": true,
        "message": "3개의 결과가 성공적으로 저장되었습니다.",
        "saved_count": 3
    }
    ```
    
    **실패 시:**
    ```json
    {
        "success": false,
        "message": "일부 결과를 찾을 수 없습니다.",
        "saved_count": 0
    }
    ```
    
    추후 DB 저장으로 변경 예정입니다.
    """
    # TODO: DB 저장으로 변경
    # ✅ 임시 권한 체크 (더미 저장이므로 request.result_ids를 project_id로 간주)
    user_id = int(current_user_id)
    for rid in request.result_ids or []:
        project = select_one(
            "projects",
            where={"project_id": rid, "user_id": user_id, "is_deleted": False},
            columns="project_id",
        )
        if not project:
            raise HTTPException(status_code=403, detail=f"저장 권한이 없습니다. (result_id={rid})")
    
    if not request.result_ids:
        return SelectSaveResultResponse(
            success=False,
            message="저장할 결과를 선택하지 않았습니다.",
            saved_count=0
        )
    
    # 존재하는 결과 ID 확인
    existing_ids = {result["id"] for result in DUMMY_GENERATED_RESULTS}
    valid_ids = [rid for rid in request.result_ids if rid in existing_ids]
    invalid_ids = [rid for rid in request.result_ids if rid not in existing_ids]
    
    if not valid_ids:
        return SelectSaveResultResponse(
            success=False,
            message=f"요청한 결과를 찾을 수 없습니다. 잘못된 ID: {invalid_ids}",
            saved_count=0
        )
    
    try:
        # DB 저장 시뮬레이션
        saved_count = 0
        for result in DUMMY_GENERATED_RESULTS:
            if result["id"] in valid_ids:
                # 이미 저장된 결과인지 확인
                if result["status"] == "saved":
                    continue
                
                # 저장 처리
                result["status"] = "saved"
                DUMMY_SAVED_RESULTS.append(result.copy())
                saved_count += 1
        
        if saved_count == 0:
            return SelectSaveResultResponse(
                success=False,
                message="선택한 결과가 이미 저장되어 있습니다.",
                saved_count=0
            )
        
        # 일부만 성공한 경우
        if invalid_ids:
            return SelectSaveResultResponse(
                success=True,
                message=f"{saved_count}개의 결과가 저장되었습니다. (잘못된 ID {len(invalid_ids)}개 무시됨)",
                saved_count=saved_count
            )
        
        # 모두 성공
        return SelectSaveResultResponse(
            success=True,
            message=f"{saved_count}개의 결과가 성공적으로 저장되었습니다.",
            saved_count=saved_count
        )
        
    except Exception as e:
        # DB 저장 실패
        return SelectSaveResultResponse(
            success=False,
            message=f"저장 중 오류가 발생했습니다: {str(e)}",
            saved_count=0
        )


@router.put(
    "/update",
    response_model=SelectSaveResultResponse,
    summary="선택한 결과 수정",
    description="선택한 결과들을 DB에 수정합니다.",
    tags=["결과 관리"]
)
async def update_selected_results(request: SelectSaveResultRequest, current_user_id: str = Depends(get_current_user)):
    """
    선택한 결과들을 DB에 저장합니다.
    
    - **result_ids**: 저장할 결과 ID 리스트
    
    **성공 시:**
    ```json
    {
        "success": true,
        "message": "3개의 결과가 성공적으로 저장되었습니다.",
        "saved_count": 3
    }
    ```
    
    **실패 시:**
    ```json
    {
        "success": false,
        "message": "일부 결과를 찾을 수 없습니다.",
        "saved_count": 0
    }
    ```
    
    추후 DB 저장으로 변경 예정입니다.
    """
    # TODO: DB 저장으로 변경
    # ✅ 임시 권한 체크 (더미 수정이므로 request.result_ids를 project_id로 간주)
    user_id = int(current_user_id)
    for rid in request.result_ids or []:
        project = select_one(
            "projects",
            where={"project_id": rid, "user_id": user_id, "is_deleted": False},
            columns="project_id",
        )
        if not project:
            raise HTTPException(status_code=403, detail=f"수정 권한이 없습니다. (result_id={rid})")
    
    if not request.result_ids:
        return SelectSaveResultResponse(
            success=False,
            message="저장할 결과를 선택하지 않았습니다.",
            saved_count=0
        )
    
    # 존재하는 결과 ID 확인
    existing_ids = {result["id"] for result in DUMMY_GENERATED_RESULTS}
    valid_ids = [rid for rid in request.result_ids if rid in existing_ids]
    invalid_ids = [rid for rid in request.result_ids if rid not in existing_ids]
    
    if not valid_ids:
        return SelectSaveResultResponse(
            success=False,
            message=f"요청한 결과를 찾을 수 없습니다. 잘못된 ID: {invalid_ids}",
            saved_count=0
        )
    
    try:
        # DB 저장 시뮬레이션
        saved_count = 0
        for result in DUMMY_GENERATED_RESULTS:
            if result["id"] in valid_ids:
                # 이미 저장된 결과인지 확인
                if result["status"] == "saved":
                    continue
                
                # 저장 처리
                result["status"] = "saved"
                DUMMY_SAVED_RESULTS.append(result.copy())
                saved_count += 1
        
        if saved_count == 0:
            return SelectSaveResultResponse(
                success=False,
                message="선택한 결과가 이미 저장되어 있습니다.",
                saved_count=0
            )
        
        # 일부만 성공한 경우
        if invalid_ids:
            return SelectSaveResultResponse(
                success=True,
                message=f"{saved_count}개의 결과가 저장되었습니다. (잘못된 ID {len(invalid_ids)}개 무시됨)",
                saved_count=saved_count
            )
        
        # 모두 성공
        return SelectSaveResultResponse(
            success=True,
            message=f"{saved_count}개의 결과가 성공적으로 저장되었습니다.",
            saved_count=saved_count
        )
        
    except Exception as e:
        # DB 저장 실패
        return SelectSaveResultResponse(
            success=False,
            message=f"저장 중 오류가 발생했습니다: {str(e)}",
            saved_count=0
        )


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