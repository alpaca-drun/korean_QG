from typing import Optional
from fastapi import BackgroundTasks
from app.schemas.question_generation import QuestionGenerationRequest
from app.services.question_generation_service import QuestionGenerationService


class QuestionGenerationTask:
    """문항 생성 비동기 작업"""
    
    def __init__(self):
        self.service = QuestionGenerationService()
    
    async def generate_async(
        self,
        request: QuestionGenerationRequest,
        provider: Optional[str] = None,
        callback_url: Optional[str] = None
    ):
        """
        비동기 문항 생성
        
        Args:
            request: 문항 생성 요청
            provider: LLM 제공자
            callback_url: 완료 후 콜백 URL (선택사항)
        """
        try:
            result = await self.service.generate_questions(request, provider)
            
            # 콜백이 있으면 호출
            if callback_url:
                await self._send_callback(callback_url, result)
            
            return result
            
        except Exception as e:
            # 에러 처리
            if callback_url:
                from app.schemas.question_generation import (
                    QuestionGenerationErrorResponse,
                    ErrorDetail
                )
                error_response = QuestionGenerationErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code="TASK_ERROR",
                        message="비동기 작업 중 오류가 발생했습니다.",
                        details=str(e)
                    )
                )
                await self._send_callback(callback_url, error_response)
            
            raise
    
    async def _send_callback(self, callback_url: str, result):
        """콜백 URL로 결과 전송"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json=result.dict())
        except Exception as e:
            # 콜백 실패는 로깅만 (작업 자체는 성공)
            print(f"콜백 전송 실패: {e}")


# Celery를 사용하는 경우 (선택사항)
try:
    from celery import Celery
    from app.core.config import settings
    
    if settings.enable_celery:
        celery_app = Celery(
            "question_generation",
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend
        )
        
        @celery_app.task(name="generate_questions_task")
        def generate_questions_celery_task(
            request_dict: dict,
            provider: Optional[str] = None
        ):
            """Celery 작업으로 문항 생성"""
            from app.schemas.question_generation import QuestionGenerationRequest
            
            request = QuestionGenerationRequest(**request_dict)
            task = QuestionGenerationTask()
            
            # 동기 실행 (Celery는 비동기 지원)
            import asyncio
            return asyncio.run(task.service.generate_questions(request, provider))
        
except ImportError:
    # Celery가 설치되지 않은 경우
    celery_app = None

