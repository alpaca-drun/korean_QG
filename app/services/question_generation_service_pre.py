from typing import List, Optional
from threading import Lock
from app.schemas.question_generation import (
    QuestionGenerationRequest,
    Question,
    QuestionGenerationSuccessResponse,
    QuestionGenerationErrorResponse,
    ErrorDetail
)
from app.clients.factory import LLMClientFactory
from app.clients.base import LLMClientBase
from app.prompts.templates import PromptTemplate
from app.db.storage import save_questions_batch_to_db
from app.utils.file_path import resolve_file_paths, ensure_storage_directory
from app.core.config import settings


class QuestionGenerationService:
    """문항 생성 서비스"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 기본 클라이언트 사용)
        """
        self.llm_client = llm_client or LLMClientFactory.create_client()
    
    async def generate_questions(
        self,
        request: QuestionGenerationRequest,
        provider: Optional[str] = None
    ) -> QuestionGenerationSuccessResponse | QuestionGenerationErrorResponse:
        """
        문항 생성
        
        Args:
            request: 문항 생성 요청
            provider: LLM 제공자 (선택사항)
            
        Returns:
            성공 또는 실패 응답
        """
        try:
            # LLM 클라이언트 설정
            if provider:
                self.llm_client = LLMClientFactory.create_client(provider=provider)
            
            # API 키 검증
            if not self.llm_client.validate_api_key():
                return QuestionGenerationErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code="INVALID_API_KEY",
                        message="LLM API 키가 유효하지 않습니다.",
                        details="환경 변수에 API 키를 설정해주세요."
                    )
                )
            
            # grade_level 추출
            grade_level = request.curriculum_info.grade_level if request.curriculum_info else None
            
            # 파일 저장 디렉토리 확인 및 생성 (grade_level에 따라 경로 결정)
            ensure_storage_directory(grade_level)
            
            # 파일 경로를 실제 경로로 변환 (grade_level에 따라 경로 결정)
            resolved_file_paths = resolve_file_paths(
                request.file_paths, 
                grade_level=grade_level
            ) if request.file_paths else None
            
            # 사용자가 요청한 문항 수를 10으로 나눠서 배치 생성
            # 예: 30문항 요청 → 3개 배치 (각 10문항씩)
            total_count = request.generation_count
            batch_size = 10
            num_batches = (total_count + batch_size - 1) // batch_size  # 올림 계산
            
            all_questions = []
            
            # 각 배치마다 프롬프트 생성 및 API 호출
            for batch_idx in range(num_batches):
                # 마지막 배치는 남은 문항 수만큼 (하지만 프롬프트는 항상 10으로 고정)
                batch_request = request.model_copy()  # 요청 복사
                batch_request.generation_count = batch_size  # 배치 크기는 10으로 고정
                
                # 프롬프트 생성 (시스템 프롬프트와 사용자 프롬프트 분리)
                system_prompt, user_prompt = PromptTemplate.build_prompt(batch_request)
                
                # LLM API 호출 (각 배치마다 다른 API 키 사용)
                batch_questions = await self.llm_client.generate_questions(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    count=batch_size,  # 항상 10문항
                    file_paths=resolved_file_paths,
                    file_display_names=request.file_display_names
                )
                
                all_questions.extend(batch_questions)
            
            # 요청한 문항 수만큼만 반환 (초과 생성된 경우 자름)
            questions = all_questions[:total_count]
            
            # JSON 파일로 저장
            try:
                import json
                from datetime import datetime
                import os
                
                # 저장 디렉토리 생성 (grade_level에 따라)
                output_dir = f"storage/{grade_level}" if grade_level else "storage/default"
                os.makedirs(output_dir, exist_ok=True)
                
                # 타임스탬프
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 파일명 생성
                achievement_std = request.curriculum_info.achievement_standard if request.curriculum_info else "unknown"
                filename = f"questions_{achievement_std}_{timestamp}.json"
                filepath = os.path.join(output_dir, filename)
                
                # 데이터 변환
                questions_data = [q.model_dump() if hasattr(q, 'model_dump') else q.dict() for q in questions]
                
                # JSON 파일로 저장
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump({
                        "metadata": {
                            "achievement_standard": achievement_std,
                            "grade_level": grade_level,
                            "total_questions": len(questions),
                            "generated_at": timestamp
                        },
                        "questions": questions_data
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"✅ JSON 파일 저장 완료: {filepath}")
                
            except Exception as e:
                print(f"⚠️ JSON 저장 실패: {e}")
            
            # # DB 저장 (설정된 경우) - 주석처리
            # if settings.db_host and settings.db_database:
            #     try:
            #         lock = Lock()
            #         # Pydantic v2에서는 model_dump() 사용
            #         questions_data = [q.model_dump() if hasattr(q, 'model_dump') else q.dict() for q in questions]
            #         question_ids = save_questions_batch_to_db(
            #             questions_data,
            #             lock=lock,
            #             info_id=None  # TODO: info_id를 요청에서 받아오도록 수정
            #         )
            #         
            #         # DB ID를 문항에 매핑
            #         for question, db_id in zip(questions, question_ids):
            #             if db_id:
            #                 question.db_question_id = db_id
            #     except Exception as e:
            #         # DB 저장 실패해도 문항 생성은 성공으로 처리
            #         print(f"DB 저장 실패 (문항은 생성됨): {e}")
            
            # 응답 생성
            return QuestionGenerationSuccessResponse(
                success=True,
                total_questions=len(questions),
                questions=questions
            )
            
        except Exception as e:
            error_code = "API_ERROR"
            error_message = "LLM API 호출 중 오류가 발생했습니다."
            error_details = str(e)
            
            # 에러 타입에 따른 분류
            if "Rate limit" in str(e) or "rate limit" in str(e).lower():
                error_code = "RATE_LIMIT_EXCEEDED"
                error_message = "API 호출 한도가 초과되었습니다."
            elif "API 키" in str(e) or "api key" in str(e).lower():
                error_code = "INVALID_API_KEY"
                error_message = "API 키가 유효하지 않습니다."
            
            return QuestionGenerationErrorResponse(
                success=False,
                error=ErrorDetail(
                    code=error_code,
                    message=error_message,
                    details=error_details
                )
            )
    
    async def generate_questions_batch(
        self,
        requests: List[QuestionGenerationRequest],
        provider: Optional[str] = None
    ) -> List[QuestionGenerationSuccessResponse | QuestionGenerationErrorResponse]:
        """
        배치 문항 생성
        
        여러 문항 생성 요청을 한 번에 처리합니다.
        - 최대 10개의 서로 다른 요청을 동시에 처리 가능
        - 각 요청은 독립적으로 처리됩니다
        - 각 요청 내에서 10문항씩 배치로 나뉘어 처리됩니다 (예: 30문항 요청 → 3개 배치)
        - 각 배치마다 다른 API 키를 사용하여 병렬 처리됩니다
        
        Args:
            requests: 문항 생성 요청 리스트 (최대 10개)
            provider: LLM 제공자 (선택사항)
            
        Returns:
            성공 또는 실패 응답 리스트 (요청 순서대로 반환)
        """
        # LLM 클라이언트 설정
        if provider:
            self.llm_client = LLMClientFactory.create_client(provider=provider)
        
        # 각 요청을 10문항씩 배치로 나누기
        # 예: 30문항 요청 → 3개 배치 (각 10문항씩)
        system_prompts = []
        user_prompts = []
        counts = []
        file_paths_list = []
        file_display_names_list = []
        request_mapping = []  # 배치 결과를 원래 요청에 매핑하기 위한 리스트
        
        # 각 요청마다 grade_level에 따라 디렉토리 생성 및 경로 변환
        for req_idx, req in enumerate(requests):
            total_count = req.generation_count
            batch_size = 10
            num_batches = (total_count + batch_size - 1) // batch_size  # 올림 계산
            
            # grade_level 추출
            grade_level = req.curriculum_info.grade_level if req.curriculum_info else None
            
            # 파일 저장 디렉토리 확인 및 생성 (grade_level에 따라 경로 결정)
            if grade_level:
                ensure_storage_directory(grade_level)
            
            # 파일 경로를 실제 경로로 변환 (grade_level에 따라 경로 결정)
            resolved_file_paths = resolve_file_paths(
                req.file_paths, 
                grade_level=grade_level
            ) if req.file_paths else None
            
            # 각 배치마다 프롬프트 생성
            for batch_idx in range(num_batches):
                batch_request = req.model_copy()  # 요청 복사
                batch_request.generation_count = batch_size  # 배치 크기는 10으로 고정
                
                sys_prompt, usr_prompt = PromptTemplate.build_prompt(batch_request)
                system_prompts.append(sys_prompt)
                user_prompts.append(usr_prompt)
                counts.append(batch_size)  # 항상 10문항
                file_paths_list.append(resolved_file_paths)  # 변환된 경로 사용
                file_display_names_list.append(req.file_display_names)
                
                # 원래 요청 인덱스와 배치 정보 저장
                request_mapping.append({
                    'request_idx': req_idx,
                    'batch_idx': batch_idx,
                    'total_count': total_count
                })
        
        try:
            # 배치 API 호출
            batch_results = await self.llm_client.generate_questions_batch(
                system_prompts=system_prompts,
                user_prompts=user_prompts,
                counts=counts,
                file_paths_list=file_paths_list,
                file_display_names_list=file_display_names_list
            )
            
            # 배치 결과를 원래 요청별로 그룹화
            request_questions = {}  # {request_idx: [questions]}
            
            for batch_result, mapping in zip(batch_results, request_mapping):
                req_idx = mapping['request_idx']
                if req_idx not in request_questions:
                    request_questions[req_idx] = []
                
                if batch_result:
                    request_questions[req_idx].extend(batch_result)
            
            # 응답 생성 및 DB 저장
            responses = []
            lock = Lock()
            
            for req_idx, request in enumerate(requests):
                questions = request_questions.get(req_idx, [])
                
                # 요청한 문항 수만큼만 반환 (초과 생성된 경우 자름)
                questions = questions[:request.generation_count]
                
                if questions:
                    # JSON 파일로 저장 (배치)
                    try:
                        import json
                        from datetime import datetime
                        import os
                        
                        # 저장 디렉토리 생성
                        grade_level = request.curriculum_info.grade_level if request.curriculum_info else None
                        output_dir = f"storage/{grade_level}" if grade_level else "storage/default"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # 타임스탬프
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # 파일명 생성
                        achievement_std = request.curriculum_info.achievement_standard if request.curriculum_info else "unknown"
                        filename = f"questions_batch_{req_idx}_{achievement_std}_{timestamp}.json"
                        filepath = os.path.join(output_dir, filename)
                        
                        # 데이터 변환
                        questions_data = [q.model_dump() if hasattr(q, 'model_dump') else q.dict() for q in questions]
                        
                        # JSON 파일로 저장
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump({
                                "metadata": {
                                    "batch_index": req_idx,
                                    "achievement_standard": achievement_std,
                                    "grade_level": grade_level,
                                    "total_questions": len(questions),
                                    "generated_at": timestamp
                                },
                                "questions": questions_data
                            }, f, ensure_ascii=False, indent=2)
                        
                        print(f"✅ JSON 파일 저장 완료 (배치 {req_idx}): {filepath}")
                        
                    except Exception as e:
                        print(f"⚠️ JSON 저장 실패 (배치 {req_idx}): {e}")
                    
                    # # DB 저장 (설정된 경우) - 주석처리
                    # if settings.db_host and settings.db_database:
                    #     try:
                    #         # Question 객체를 dict로 변환
                    #         questions_data = []
                    #         for q in questions:
                    #             q_dict = q.model_dump() if hasattr(q, 'model_dump') else q.dict()
                    #             questions_data.append(q_dict)
                    #         
                    #         question_ids = save_questions_batch_to_db(
                    #             questions_data,
                    #             lock=lock,
                    #             info_id=None  # TODO: info_id를 요청에서 받아오도록 수정
                    #         )
                    #         
                    #         # DB ID를 문항에 매핑
                    #         for question, db_id in zip(questions, question_ids):
                    #             if db_id:
                    #                 question.db_question_id = db_id
                    #     except Exception as e:
                    #         # DB 저장 실패해도 문항 생성은 성공으로 처리
                    #         print(f"DB 저장 실패 (문항은 생성됨): {e}")
                    
                    responses.append(
                        QuestionGenerationSuccessResponse(
                            success=True,
                            total_questions=len(questions),
                            questions=questions
                        )
                    )
                else:
                    responses.append(
                        QuestionGenerationErrorResponse(
                            success=False,
                            error=ErrorDetail(
                                code="GENERATION_FAILED",
                                message="문항 생성에 실패했습니다.",
                                details=""
                            )
                        )
                    )
            
            return responses
            
        except Exception as e:
            # 전체 실패 시 모든 요청에 대해 에러 응답 반환
            return [
                QuestionGenerationErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code="BATCH_ERROR",
                        message="배치 문항 생성 중 오류가 발생했습니다.",
                        details=str(e)
                    )
                )
                for _ in requests
            ]

