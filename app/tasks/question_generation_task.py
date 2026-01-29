from typing import Optional, List
import logging
from fastapi import BackgroundTasks
from app.schemas.question_generation import (
    QuestionGenerationRequest,
    QuestionGenerationSuccessResponse,
    QuestionGenerationErrorResponse
)
from app.services.question_generation_service import QuestionGenerationService
from app.db.generate import save_batch_log, save_questions_batch_to_db
from app.db.generate import update_project_status
from app.clients.email import get_email_client
from app.core.logger import logger

class QuestionGenerationTask:
    """문항 생성 비동기 작업"""
    
    def __init__(self):
        self.service = QuestionGenerationService()
    
    async def generate_batch_async(
        self,
        requests: List[QuestionGenerationRequest],
        user_id: str,
        provider: Optional[str] = None
    ):
        """
        배치 문항 생성 백그라운드 작업
        
        Args:
            requests: 문항 생성 요청 리스트
            user_id: 사용자 ID
            provider: LLM 제공자
        """
        try:
            logger.info(f"🚀 배치 문항 생성 백그라운드 작업 시작 (요청 수: {len(requests)})")
            
            # 서비스를 통해 배치 생성
            results = await self.service.generate_questions_batch(requests, user_id, provider)
            
            logger.info(f"✅ 배치 생성 완료 (결과 수: {len(results)})")
            
            # DB에 저장
            for idx, result in enumerate(results):
                # 에러 응답 처리
                if not isinstance(result, QuestionGenerationSuccessResponse) or not result.success:
                    logger.warning(f"⚠️ 배치 {idx+1} 생성 실패 - DB 저장 생략")
                    if isinstance(result, QuestionGenerationErrorResponse):
                        logger.error(f"  에러: {result.error.message if hasattr(result, 'error') else 'Unknown error'}")
                    continue
                
                # 성공 응답만 처리
                batch_log_data = result.metadata.batches
                if True:
                    try:
                        # project_id 가져오기
                        project_id = None
                        config_id = None
                        if idx < len(requests) and hasattr(requests[idx], 'project_id'):
                            project_id = requests[idx].project_id
                            logger.debug(f"📌 배치 {idx+1} - project_id: {project_id}")
                            config_id = requests[idx].config_id
                            logger.debug(f"📌 배치 {idx+1} - config_id: {config_id}")
                        else:
                            logger.warning(f"⚠️ 배치 {idx+1} - project_id 없음, 기본값 사용")
                            project_id = 1  # 기본값
                        
                        # 1단계: 배치 로그를 DB에 저장하고 매핑 테이블 생성
                        batch_index_mapping = {}  # {원래_batch_number: DB_batch_id}
                        
                        logger.info(f"📊 배치 로그 및 문항 저장 시작: {len(batch_log_data)}개 배치")
                        
                        from app.db.database import get_db_connection
                        with get_db_connection() as connection:
                            for batch_log in batch_log_data:
                                # 배치 로그 DB 저장 후 ID 반환
                                batch_id = save_batch_log(
                                    batch_log_data=batch_log.model_dump(),
                                    project_id=project_id,
                                    connection=connection
                                )
                                
                                # 원래 batch_number와 DB의 batch_id 매핑
                                original_batch_number = batch_log.batch_number
                                
                                if batch_id is None:
                                    logger.warning(f"  ⚠️ 배치 로그 저장 실패: {original_batch_number}")
                                    batch_index_mapping[original_batch_number] = original_batch_number
                                else:
                                    batch_index_mapping[original_batch_number] = batch_id
                            
                            # 2단계: 각 question의 batch_index를 DB ID로 업데이트
                            for question in result.questions:
                                original_batch_index = getattr(question, 'batch_index', None)
                                
                                # 매핑 테이블에서 새 batch_id 찾아서 업데이트
                                if original_batch_index in batch_index_mapping:
                                    new_batch_id = batch_index_mapping[original_batch_index]
                                    question.batch_index = new_batch_id
                            
                            # 3단계: 업데이트된 questions를 DB에 저장
                            valid_questions = []
                            for question in result.questions:
                                batch_idx = getattr(question, 'batch_index', None)
                                if isinstance(batch_idx, int):
                                    valid_questions.append(question.model_dump())
                            
                            if valid_questions:
                                save_questions_batch_to_db(
                                    questions_data=valid_questions,
                                    project_id=project_id,
                                    config_id=config_id
                                )
                            
                            connection.commit()
                            logger.info("✅ 모든 배치 로그 및 문항 저장 완료")

                        ## 📢 project 테이블 상태값 업데이트
                        update_project_status(project_id, "COMPLETED")
                        
                        # 반환된 DB ID를 문항 객체에 매핑
                        for question, db_id in zip(result.questions, saved_ids):
                            if db_id:
                                question.db_question_id = db_id
                        
                        logger.info(f"✅ 배치 {idx+1} 문항 저장 완료: {len(saved_ids)}개 (DB ID 샘플: {[id for id in saved_ids[:3] if id]})")
                        
                    except Exception as e:
                        logger.error(f"❌ 배치 {idx+1} DB 저장 실패: {e}", exc_info=True)
                else:
                    logger.warning(f"⚠️ 배치 {idx+1}은 생성 실패하여 DB 저장 생략")
            
            logger.info(f"🎉 배치 문항 생성 및 DB 저장 완료!")

            # ✉️ 완료 메일 전송
            try:
                # 성공/실패 집계
                success_count = sum(
                    1 for r in results 
                    if isinstance(r, QuestionGenerationSuccessResponse) and r.success
                )
                total_count = len(results)
                total_questions = sum(
                    r.total_questions for r in results 
                    if isinstance(r, QuestionGenerationSuccessResponse) and r.success
                )
                
                # 프로젝트 이름 가져오기 (첫 번째 요청에서)
                project_name = getattr(requests[0], 'project_name', None) if requests else None
                if not project_name:
                    project_name = "알 수 없는 프로젝트"
                
                # 사용자 이메일 가져오기
                user_email = self._get_user_email(user_id)
                
                if user_email and success_count > 0:
                    email_client = get_email_client()
                    email_sent = email_client.send_success_email(
                        to_address=user_email,
                        project_name=project_name,
                        success_count=success_count,    
                        total_count=total_count,
                        total_questions=total_questions
                    )
                    
                    if email_sent:
                        logger.info(f"📧 완료 메일 전송 성공: {user_email}")
                    else:
                        logger.warning(f"📧 완료 메일 전송 실패: {user_email}")
                elif not user_email:
                    logger.warning(f"⚠️ 사용자 이메일을 찾을 수 없음: user_id={user_id}")
                else:
                    logger.info(f"⚠️ 성공한 배치가 없어 메일을 전송하지 않음")
                    
            except Exception as e:
                logger.error(f"⚠️ 완료 메일 전송 중 오류 발생 (작업은 성공): {e}")

        except Exception as e:
            logger.error(f"❌ 배치 백그라운드 작업 중 오류 발생: {e}", exc_info=True)
            
            # ✉️ 실패 메일 전송
            try:
                user_email = self._get_user_email(user_id)
                project_name = requests[0].project_name if requests else "알 수 없는 프로젝트"
                
                if user_email:
                    email_client = get_email_client()
                    email_client.send_failure_email(
                        to_address=user_email,
                        project_name=project_name,
                        error_message=str(e)
                    )
                    logger.info(f"📧 실패 메일 전송 완료: {user_email}")
            except Exception as email_error:
                logger.error(f"⚠️ 실패 메일 전송 중 오류 발생: {email_error}")
    
    def _get_user_email(self, user_id: str) -> Optional[str]:
        """
        사용자 ID로 이메일 주소 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            Optional[str]: 사용자 이메일 (없으면 None)
        """
        try:
            from app.db.database import select_one
            
            logger.info("사용자 이메일 조회: user_id=%s", user_id)
            
            # select_one 사용 (훨씬 간단!)
            user = select_one(
                table="users",
                where={"user_id": user_id, "is_active": 1},
                columns="email"
            )
            
            if user and user.get('email'):
                return user['email']
            else:
                logger.warning("사용자를 찾을 수 없음: user_id=%s", user_id)
                return None
                
        except Exception as e:
            logger.warning("사용자 이메일 조회 실패: %s", e)
            return None
    
    async def generate_async(
        self,
        request: QuestionGenerationRequest,
        user_id: str,
        provider: Optional[str] = None,
        callback_url: Optional[str] = None
    ):
        """
        비동기 문항 생성
        
        Args:
            request: 문항 생성 요청
            user_id: 사용자 ID
            provider: LLM 제공자
            callback_url: 완료 후 콜백 URL (선택사항)
        """
        try:
            result = await self.service.generate_questions(request, user_id, provider)
            
            # 콜백이 있으면 호출
            if callback_url:
                await self._send_callback(callback_url, result)
            
            return result
            
        except Exception as e:
            logger.exception("비동기 문항 생성 중 오류")
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
            logger.warning("콜백 전송 실패: %s", e)


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

