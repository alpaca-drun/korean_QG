from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Query, Depends
from typing import Optional, List
import json
from app.schemas.question_generation import (
    QuestionGenerationRequest,
    QuestionGeneration,
    QuestionGenerationSuccessResponse,
    QuestionGenerationErrorResponse
)
from app.services.question_generation_service import QuestionGenerationService
from app.tasks.question_generation_task import QuestionGenerationTask
from app.utils.dependencies import get_current_user

from app.db.generate import get_generation_config

router = APIRouter()

@router.post(
    "/batch",
    response_model=List[QuestionGenerationSuccessResponse | QuestionGenerationErrorResponse],
    summary="배치 문항 생성",
    description="여러 문항 생성 요청을 배치로 처리합니다.",
    tags=["문항 생성"]
)
async def generate_questions_batch(
    requests: List[QuestionGeneration],
    provider: Optional[str] = Query(None, description="LLM 제공자", example="gemini"),
    current_user_id: str = Depends(get_current_user)
):
    """
    배치 문항 생성 API
    
    여러 문항 생성 요청을 한 번에 처리합니다.
    - 최대 10개의 서로 다른 요청을 동시에 처리 가능 (10명의 사용자 또는 10개의 서로 다른 문항 생성 요청)
    - 각 요청은 독립적으로 처리됩니다
    - 각 요청 내에서 10문항씩 배치로 나뉘어 처리됩니다 (예: 30문항 요청 → 3개 배치)
    - 각 배치마다 다른 API 키를 사용하여 병렬 처리됩니다
    """
    # TODO: 토큰 검증 로직 추가
    
    if len(requests) > 10:
        raise HTTPException(
            status_code=400,
            detail="배치 요청은 최대 10개까지 가능합니다."
        )
    # QuestionGeneration 객체에서 필요한 필드만 빼내고, QuestionGenerationRequest에 맞춰 재구성
    question_generation_requests = []
    generation_configs = get_generation_config(requests[0].project_id)

    # 그대로 넘겨도 Pydantic이 알아서 QuestionGenerationRequest에 맞는 필드만 받고 나머지는 무시함
    # 추가 필드 필요하면 직접 넘길 수 있고, 누락/불필요한 필드는 자동 제외됨
    for request in requests:
        # dict로 만들고 추가 필드 있으면 미리 보강
        obj_dict = request.model_dump()
        # 새로운 필드 추가 예시 (아래 주석)
        # obj_dict["some_new_field"] = "default_value"
        obj_dict["config_id"] = generation_configs.get("config_id")
        obj_dict["passage"] = generation_configs.get("passage")
        obj_dict["learning_objective"] = generation_configs.get("learning_objective")
        obj_dict["learning_activity"] = generation_configs.get("learning_activity") or ""
        obj_dict["learning_element"] = generation_configs.get("learning_element") or ""
        obj_dict["semester"] = str(generation_configs.get("semester") or "1")
        # achievements를 JSON 문자열에서 리스트로 파싱
        achievements_raw = generation_configs.get("achievements")
        achievements = json.loads(achievements_raw) if achievements_raw else []
        
        obj_dict["curriculum_info"] = [
            {
                "achievement_code": ach.get("code"),
                "achievement_content": ach.get("description"),
                "evaluation_content": ach.get("evaluation_criteria"),
            }
            for ach in achievements
        ]
        obj_dict["school_level"] = generation_configs.get("school_level") or "중학교"
        obj_dict["grade_level"] = str(generation_configs.get("grade") or "")
        obj_dict["large_unit"] = generation_configs.get("large_unit_name") or ""
        obj_dict["small_unit"] = generation_configs.get("small_unit_name") or ""
        obj_dict["generation_count"] = request.target_count
        obj_dict["study_area"] = generation_configs.get("study_area")
        obj_dict["file_paths"] = ["국어과_교과서론_1권 요약.md", "국어과_교과서론_2권 요약본.md"]
        obj_dict["file_display_names"] = ["교과서론 1권", "교과서론 2권"]


        question_generation_requests.append(QuestionGenerationRequest(**obj_dict))
        print("🟣")
        print(question_generation_requests)

    service = QuestionGenerationService()
    results = await service.generate_questions_batch(question_generation_requests, current_user_id, provider)
    
    return results



@router.post(
    "",
    response_model=QuestionGenerationSuccessResponse | QuestionGenerationErrorResponse,
    summary="문항 생성",
    description="LLM API를 사용하여 문항을 생성합니다.",
    tags=["문항 생성"]
)
async def generate_questions(
    request: QuestionGenerationRequest,
    background_tasks: BackgroundTasks,
    token: Optional[str] = Header(None, alias="token", description="인증 토큰"),
    provider: Optional[str] = Query(None, description="LLM 제공자 (gemini, openai)", example="gemini"),
    async_mode: bool = Query(False, description="비동기 모드 사용 여부"),
    current_user_id: str = Depends(get_current_user)
):
    """
    문항 생성 API
    
    - **passage**: 원본 지문 텍스트
    - **learning_objective**: 학습목표
    - **curriculum_info**: 교육과정 정보
    - **generation_count**: 생성할 문항 수 (1-50)
    
    비동기 모드를 사용하면 백그라운드에서 처리됩니다.
    """
    # TODO: 토큰 검증 로직 추가
    
    service = QuestionGenerationService()
    
    if async_mode:
        # 비동기 모드 (BackgroundTasks 사용)
        task = QuestionGenerationTask()
        background_tasks.add_task(
            task.generate_async,
            request=request,
            user_id=current_user_id,
            provider=provider
        )
        
        # 즉시 응답 반환 (작업은 백그라운드에서 진행)
        return QuestionGenerationSuccessResponse(
            success=True,
            total_questions=0,
            questions=[],
            message="문항 생성이 백그라운드에서 시작되었습니다."
        )
    else:
        # 동기 모드
        result = await service.generate_questions(request, current_user_id, provider)
        return result


@router.get(
    "/providers",
    summary="사용 가능한 LLM 제공자 조회",
    description="사용 가능한 LLM 제공자 목록을 조회합니다.",
    tags=["문항 생성"]
)
async def get_available_providers():
    """사용 가능한 LLM 제공자 목록 반환"""
    from app.clients.factory import LLMClientFactory
    
    providers = LLMClientFactory.get_available_providers()
    
    return {
        "providers": providers,
        "default": "gemini"
    }

