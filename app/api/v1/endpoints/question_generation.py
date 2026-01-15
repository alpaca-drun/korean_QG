from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Query
from typing import Optional, List
from app.schemas.question_generation import (
    QuestionGenerationRequest,
    QuestionGenerationSuccessResponse,
    QuestionGenerationErrorResponse
)
from app.services.question_generation_service import QuestionGenerationService
from app.tasks.question_generation_task import QuestionGenerationTask

router = APIRouter()


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
    async_mode: bool = Query(False, description="비동기 모드 사용 여부")
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
        result = await service.generate_questions(request, provider)
        return result


@router.post(
    "/batch",
    response_model=List[QuestionGenerationSuccessResponse | QuestionGenerationErrorResponse],
    summary="배치 문항 생성",
    description="여러 문항 생성 요청을 배치로 처리합니다.",
    tags=["문항 생성"]
)
async def generate_questions_batch(
    requests: List[QuestionGenerationRequest],
    token: Optional[str] = Header(None, alias="token", description="인증 토큰"),
    provider: Optional[str] = Query(None, description="LLM 제공자", example="gemini")
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
    
    service = QuestionGenerationService()
    results = await service.generate_questions_batch(requests, provider)
    
    return results


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

