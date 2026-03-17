from typing import List, Optional
import logging
from app.schemas.question_generation import (
    QuestionGeneration,
    QuestionGenerationRequest,
    Question,
    QuestionGenerationSuccessResponse,
    QuestionGenerationErrorResponse,
    ErrorDetail,
    GenerationMetadata,
    BatchInfo
)
from app.clients.factory import LLMClientFactory
from app.clients.base import LLMClientBase
from app.prompts.templates import PromptTemplate
from app.utils.file_path import resolve_file_paths, ensure_storage_directory
from app.core.config import settings
from app.core.logger import logger


class QuestionGenerationService:
    """문항 생성 서비스"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 기본 클라이언트 사용)
        """
        self.llm_client = llm_client or LLMClientFactory.create_client()
        
    async def generate_questions_batch(
        self,
        requests: List[QuestionGenerationRequest],
        current_user_id: str,
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
        response_schema_classes = []
        request_mapping = []  # 배치 결과를 원래 요청에 매핑하기 위한 리스트
        
        # 각 요청마다 school_level에 따라 디렉토리 생성 및 경로 변환
        from app.schemas.question_generation import MultipleQuestion, MultipleMatchingQuestion
        
        for req_idx, req in enumerate(requests):
            total_count = req.generation_count
            
            # 스키마 클래스 결정
            schema_class = MultipleQuestion
            if req.question_type == "선긋기":
                schema_class = MultipleMatchingQuestion
            
            batch_size = 10
            num_batches = (total_count + batch_size - 1) // batch_size  # 올림 계산
            
            # school_level 추출
            school_level = req.school_level if hasattr(req, 'school_level') else None

            logger.info(f"🟣🟣 요청 {req_idx}: {total_count}개 문항 → {num_batches}개 배치")
            logger.debug(f"🟣🟣 School Level: {school_level}")

            
            # 파일 저장 디렉토리 확인 및 생성 (school_level에 따라 경로 결정)
            if school_level:
                ensure_storage_directory(school_level)
            
            # 파일 경로를 실제 경로로 변환 (school_level에 따라 경로 결정)
            resolved_file_paths = resolve_file_paths(
                req.file_paths, 
                school_level=school_level
            ) if req.file_paths else None
            
            # 첫 번째 배치에서 system_prompt 생성 (모든 배치에서 동일)
            first_batch_request = req.model_copy()
            first_batch_request.generation_count = batch_size
            sys_prompt, _ = PromptTemplate.build_prompt(first_batch_request)
            
            # 각 배치마다 user_prompt 생성 (문항 수만 다름)
            for batch_idx in range(num_batches):
                batch_request = req.model_copy()  # 요청 복사
                
                # 현재 배치에서 요청할 문항 수 계산 (마지막 배치는 남은 개수만큼)
                remaining = total_count - (batch_idx * batch_size)
                current_batch_size = min(batch_size, remaining)
                batch_request.generation_count = current_batch_size
                
                logger.info(f"  📦 배치 {batch_idx + 1}/{num_batches}: {current_batch_size}개 문항")
                
                # user_prompt만 다시 생성 (문항 개수가 반영됨)
                _, user_prompt = PromptTemplate.build_prompt(batch_request)
                
                system_prompts.append(sys_prompt)  # 동일한 system_prompt 재사용
                user_prompts.append(user_prompt)
                counts.append(current_batch_size)  # 실제 배치 크기
                file_paths_list.append(resolved_file_paths)  # 변환된 경로 사용
                file_display_names_list.append(req.file_display_names)
                response_schema_classes.append(schema_class)
                
                # 원래 요청 인덱스와 배치 정보 저장
                request_mapping.append({
                    'request_idx': req_idx,
                    'batch_idx': batch_idx,
                    'total_count': total_count,
                    'current_batch_size': current_batch_size
                })
        
        try:
            # 배치 API 호출
            batch_results = await self.llm_client.generate_questions_batch(
                system_prompts=system_prompts,
                user_prompts=user_prompts,
                counts=counts,
                file_paths_list=file_paths_list,
                file_display_names_list=file_display_names_list,
                response_schema_classes=response_schema_classes
            )
            
            # 배치 결과를 원래 요청별로 그룹화 (배치 정보 포함)
            request_questions = {}  # {request_idx: [questions]}
            request_batch_info = {}  # {request_idx: [batch_info]}
            
            for batch_result, mapping in zip(batch_results, request_mapping):
                req_idx = mapping['request_idx']
                batch_idx = mapping['batch_idx']
                
                if req_idx not in request_questions:
                    request_questions[req_idx] = []
                    request_batch_info[req_idx] = []
                
                # batch_result는 이제 Dict 형태: {'questions': [...], 'metadata': {...}}
                questions = batch_result.get('questions', []) if isinstance(batch_result, dict) else batch_result
                metadata = batch_result.get('metadata', {}) if isinstance(batch_result, dict) else {}
                
                logger.debug("[배치 결과] req_idx=%s, batch_idx=%s, 문항수=%s", req_idx, batch_idx, len(questions))
                logger.debug("[메타데이터] %s", metadata)
                
                if questions:
                    # 각 문항에 배치 정보 추가
                    for question in questions:
                        # 문항 데이터에 배치 정보 추가 (dict로 변환 후 추가)
                        question_dict = question.model_dump() if hasattr(question, 'model_dump') else question.dict()
                        question_dict['batch_index'] = batch_idx + 1  # 1부터 시작
                        request_questions[req_idx].append(question_dict)
                    
                    # 배치별 정보 기록 (토큰 정보 및 소요 시간 포함)
                    batch_info = {
                        'batch_number': batch_idx + 1,
                        'requested_count': mapping['current_batch_size'],
                        'generated_count': len(questions),
                        'input_tokens': metadata.get('input_tokens', 0),
                        'output_tokens': metadata.get('output_tokens', 0),
                        'total_tokens': metadata.get('total_tokens', 0),
                        'duration_seconds': metadata.get('duration_seconds', 0)
                    }
                    
                    # 에러가 있으면 추가
                    if 'error' in metadata:
                        batch_info['error'] = metadata['error']
                    
                    logger.info("[배치 정보 저장] %s", batch_info)
                    request_batch_info[req_idx].append(batch_info)
            
            # 응답 생성 및 DB 저장
            responses = []
            
            for req_idx, request in enumerate(requests):
                questions = request_questions.get(req_idx, [])
                
                # 부족한 경우 재요청 로직 (최대 3회)
                retry_count = 0
                max_retries = 3
                
                while len(questions) < request.generation_count and retry_count < max_retries:
                    shortage = request.generation_count - len(questions)
                    retry_count += 1
                    
                    logger.info("재요청 %s/%s: %s개 부족 (요청 %s개 → 생성 %s개)", retry_count, max_retries, shortage, request.generation_count, len(questions))
                    
                    try:
                        # 재요청을 위한 프롬프트 생성
                        retry_request = request.model_copy()
                        retry_request.generation_count = shortage
                        sys_prompt, user_prompt = PromptTemplate.build_prompt(retry_request)
                        
                        # 파일 경로 해결
                        school_level = request.school_level if hasattr(request, 'school_level') else None
                        resolved_file_paths = resolve_file_paths(
                            request.file_paths,
                            school_level=school_level
                        ) if request.file_paths else None
                        
                        # 스키마 클래스 결정
                        schema_class = MultipleQuestion
                        if request.question_type == "선긋기":
                            schema_class = MultipleMatchingQuestion
                        
                        # 부족한 만큼만 재요청 (단일 요청, 메타데이터 포함)
                        retry_result = await self.llm_client.generate_questions(
                            system_prompt=sys_prompt,
                            user_prompt=user_prompt,
                            count=shortage,
                            file_paths=resolved_file_paths,
                            file_display_names=request.file_display_names,
                            return_metadata=True,  # 메타데이터 포함 요청
                            response_schema_class=schema_class
                        )
                        
                        # retry_result는 Dict 형태: {'questions': [...], 'metadata': {...}}
                        retry_questions = retry_result.get('questions', []) if isinstance(retry_result, dict) else retry_result
                        retry_metadata = retry_result.get('metadata', {}) if isinstance(retry_result, dict) else {}
                        
                        logger.debug("[재요청 결과] 문항수=%s, 메타데이터=%s", len(retry_questions), retry_metadata)
                        
                        if retry_questions:
                            # 재요청 결과를 dict로 변환하여 추가
                            for question in retry_questions:
                                question_dict = question.model_dump() if hasattr(question, 'model_dump') else question.dict()
                                question_dict['batch_index'] = f"retry_{retry_count}"  # 재요청 표시
                                questions.append(question_dict)
                            
                            # 배치 정보 업데이트 (토큰 정보 포함)
                            if req_idx not in request_batch_info:
                                request_batch_info[req_idx] = []
                            
                            retry_batch_info = {
                                'batch_number': f'retry_{retry_count}',  # 문항의 batch_index와 동일하게
                                'requested_count': shortage,
                                'generated_count': len(retry_questions),
                                'input_tokens': retry_metadata.get('input_tokens', 0),
                                'output_tokens': retry_metadata.get('output_tokens', 0),
                                'total_tokens': retry_metadata.get('total_tokens', 0),
                                'duration_seconds': retry_metadata.get('duration_seconds', 0)
                            }
                            
                            # 에러가 있으면 추가
                            if 'error' in retry_metadata:
                                retry_batch_info['error'] = retry_metadata['error']
                            
                            request_batch_info[req_idx].append(retry_batch_info)
                            
                            logger.info("재요청 완료: %s개 추가 생성 (누적 %s개)", len(retry_questions), len(questions))
                            logger.debug("[재요청 배치 정보] %s", retry_batch_info)
                        else:
                            logger.warning("재요청 실패: 결과 없음")
                            break
                            
                    except Exception as e:
                        logger.exception("재요청 에러 (%s회차): %s", retry_count, e)
                        break
                
                # 최종 결과 확인
                if len(questions) < request.generation_count:
                    final_shortage = request.generation_count - len(questions)
                    logger.warning("최종 부족: %s개 (요청 %s개 → 최종 %s개)", final_shortage, request.generation_count, len(questions))
                else:
                    logger.info("목표 달성: %s개 생성 완료", len(questions))
                
                # 초과 생성된 경우 is_used 필드 추가 (0, 1 태깅)
                if len(questions) > request.generation_count:
                    trimmed = questions[:request.generation_count]
                    excess = questions[request.generation_count:]
                    # 사용분에 is_used=1, 나머지에 is_used=0 태그 추가
                    for q in trimmed:
                        q['is_used'] = 1
                    for q in excess:
                        q['is_used'] = 0
                    questions = trimmed + excess
                else:
                    # 요청 수 이하면 모두 is_used=1
                    for q in questions:
                        q['is_used'] = 1
                # 요청한 문항 수만 반환(배치 파일에는 is_used=0 포함되어 뒤에 붙음, 배치 반환에는 사용된 것만)
                questions = questions[:request.generation_count]
                
                if questions:
                    # JSON 파일로 저장 (배치)
                    try:
                        import json
                        from datetime import datetime
                        import os
                        
                        # 저장 디렉토리 생성
                        from app.utils.file_path import parse_school_level_to_path
                        school_level = request.school_level if hasattr(request, 'school_level') else None
                        school_path = parse_school_level_to_path(school_level) if school_level else "default"
                        output_dir = f"storage/{school_path}"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # 타임스탬프
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # 파일명 생성
                        achievement_code = request.curriculum_info[0].achievement_code if request.curriculum_info and len(request.curriculum_info) > 0 else "unknown"
                        filename = f"questions_batch_{req_idx}_{achievement_code}_{timestamp}.json"
                        filepath = os.path.join(output_dir, filename)
                        
                        # 배치별 정보 가져오기
                        batch_info = request_batch_info.get(req_idx, [])
                        
                        # JSON 파일로 저장
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump({
                                "metadata": {
                                    "request_index": req_idx,
                                    "achievement_code": achievement_code,
                                    "school_level": school_level,
                                    "total_questions": len(questions),
                                    "requested_count": request.generation_count,
                                    "generated_at": timestamp,
                                    "batches": batch_info
                                },
                                "questions": questions  # 이미 dict로 변환됨
                            }, f, ensure_ascii=False, indent=2)
                        
                        logger.info("JSON 파일 저장 완료 (배치 %s): %s", req_idx, filepath)
                        
                    except Exception as e:
                        logger.warning("JSON 저장 실패 (배치 %s): %s", req_idx, e)
                    
                    # dict를 Question 객체로 변환
                    question_objects = []
                    for q_idx, q_dict in enumerate(questions):
                        try:
                            # passage_info의 빈 문자열 처리
                            if 'passage_info' in q_dict and isinstance(q_dict['passage_info'], dict):
                                passage_info = q_dict['passage_info']
                                
                                # original_used 처리
                                orig_val = passage_info.get('original_used')
                                if orig_val == '' or orig_val is None:
                                    passage_info['original_used'] = True
                                elif isinstance(orig_val, str):
                                    # 문자열 "true"/"false" 처리
                                    passage_info['original_used'] = orig_val.lower() == 'true'
                                
                                # source_type 처리
                                src_val = passage_info.get('source_type')
                                if src_val == '' or src_val is None:
                                    passage_info['source_type'] = 'original'
                            
                            question_obj = Question(**q_dict)
                            question_objects.append(question_obj)
                        except Exception as e:
                            logger.warning("문항 변환 실패 [%s]: %s", q_idx, e)
                            continue
                    
                    # 메타데이터 생성 (JSON 저장과 동일한 구조)
                    batch_info_objects = [BatchInfo(**bi) for bi in batch_info]
                    metadata = GenerationMetadata(
                        request_index=req_idx,
                        achievement_code=achievement_code,
                        school_level=school_level,
                        total_questions=len(question_objects),
                        requested_count=request.generation_count,
                        generated_at=timestamp,
                        batches=batch_info_objects
                    )
                    
                    responses.append(
                        QuestionGenerationSuccessResponse(
                            success=True,
                            total_questions=len(question_objects),
                            questions=question_objects,
                            metadata=metadata
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
            logger.exception("배치 문항 생성 중 오류")
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

