import json
import asyncio
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from app.clients.base import LLMClientBase
from app.clients.api_key_manager import APIKeyManager
from app.schemas.question_generation import Question
from app.core.config import settings


class GeminiClient(LLMClientBase):
    """Google Gemini API 클라이언트 - 여러 API 키 지원 및 병렬 처리"""
    
    def __init__(self, api_key: Optional[str] = None, api_keys: Optional[List[str]] = None):
        """
        Args:
            api_key: 단일 API 키 (하위 호환성)
            api_keys: 여러 API 키 리스트
        """
        if api_keys:
            self.api_key_manager = APIKeyManager(api_keys, strategy=settings.api_key_rotation_strategy)
            self.api_keys = api_keys
        elif api_key:
            self.api_key_manager = APIKeyManager([api_key])
            self.api_keys = [api_key]
        elif settings.gemini_api_key_list:
            self.api_key_manager = APIKeyManager(
                settings.gemini_api_key_list,
                strategy=settings.api_key_rotation_strategy
            )
            self.api_keys = settings.gemini_api_key_list
        else:
            self.api_key_manager = None
            self.api_keys = []
        
        self.current_model = None
        self.current_key = None
        self.max_parallel = min(settings.max_parallel_api_keys, len(self.api_keys) if self.api_keys else 1)
    
    def validate_api_key(self) -> bool:
        """API 키 유효성 검증"""
        if not self.api_key_manager or not self.api_keys:
            return False
        return len(self.api_keys) > 0
    
    def _get_model(self, api_key: str, model_name: Optional[str] = None):
        """특정 API 키로 모델 생성"""
        if model_name is None:
            model_name = settings.gemini_model_name
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name)
    
    async def generate_questions(
        self,
        system_prompt: str,
        user_prompt: str,
        count: int,
        max_retries: int = 3,
        file_paths: Optional[List[str]] = None,
        file_display_names: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        return_metadata: bool = False,
        **kwargs
    ):
        """
        Gemini API를 사용하여 문항 생성 (자동 재시도 및 키 로테이션, 타임아웃 처리)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            count: 생성할 문항 수
            max_retries: 최대 재시도 횟수
            file_paths: 업로드할 파일 경로 리스트
            file_display_names: 파일 표시 이름 리스트
            model_name: 사용할 모델 이름
            return_metadata: True이면 메타데이터 포함한 Dict 반환, False면 List[Question] 반환
            **kwargs: 추가 파라미터
            
        Returns:
            return_metadata=False: List[Question]
            return_metadata=True: Dict[str, Any] with 'questions' and 'metadata'
        """
        if not self.api_key_manager:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")
        
        # model_name이 지정되지 않은 경우 기본값 사용
        if model_name is None:
            model_name = settings.gemini_model_name
        
        # 빠른 실패 전환 활성화 시 여러 키를 동시에 시도
        if settings.enable_fast_failover and len(self.api_keys) > 1:
            return await self._generate_with_fast_failover(
                system_prompt, user_prompt, count, 
                file_paths, file_display_names, model_name, **kwargs
            )
        
        # 일반적인 순차 재시도 방식
        last_error = None
        import time
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                api_key = self.api_key_manager.get_next_key()
                if not api_key:
                    raise ValueError("사용 가능한 Gemini API 키가 없습니다.")
                
                model = self._get_model(api_key, model_name)
                
                # 타임아웃 설정 (재시도 시 더 짧은 타임아웃)
                timeout = settings.api_retry_timeout if attempt > 0 else settings.api_call_timeout
                
                try:
                    response_obj = await asyncio.wait_for(
                        self._call_api_with_files(
                            system_prompt, user_prompt, model, 
                            file_paths, file_display_names, count, model_name,
                            return_response_obj=return_metadata
                        ),
                        timeout=timeout
                    )
                    
                    # return_metadata=True면 response 객체, False면 response.text
                    if return_metadata:
                        response_text = response_obj.text
                    else:
                        response_text = response_obj
                    
                    questions = self._parse_response(response_text, count)
                except asyncio.TimeoutError:
                    # 타임아웃 발생 시 해당 키를 일시적으로 차단
                    self.api_key_manager.mark_error(api_key, "timeout")
                    raise Exception(f"API 호출 타임아웃 ({timeout}초 초과)")
                
                # 성공 시 현재 키 성공 표시
                self.api_key_manager.mark_success(api_key)
                
                # 메타데이터 추출 (요청된 경우)
                if return_metadata:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    metadata = {
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'duration_seconds': round(duration, 2)
                    }
                    
                    # usage_metadata 추출
                    print(f"🔍 [DEBUG] response 객체 확인: hasattr(usage_metadata) = {hasattr(response_obj, 'usage_metadata')}")
                    if hasattr(response_obj, 'usage_metadata'):
                        usage = response_obj.usage_metadata
                        print(f"📊 [토큰 정보] usage_metadata: {usage}")
                        metadata['input_tokens'] = getattr(usage, 'prompt_token_count', 0)
                        metadata['output_tokens'] = getattr(usage, 'candidates_token_count', 0)
                        metadata['total_tokens'] = getattr(usage, 'total_token_count', 0)
                        print(f"✅ [토큰 추출] input={metadata['input_tokens']}, output={metadata['output_tokens']}, total={metadata['total_tokens']}, duration={metadata['duration_seconds']}초")
                    else:
                        print(f"⚠️ [WARNING] response에 usage_metadata 없음. response 타입: {type(response_obj)}")
                    
                    return {
                        'questions': questions,
                        'metadata': metadata
                    }
                
                return questions
                
            except asyncio.TimeoutError:
                # 타임아웃 에러는 이미 처리됨
                last_error = Exception("API 호출 타임아웃")
                if attempt < max_retries - 1:
                    continue
                else:
                    raise Exception("모든 API 키에서 타임아웃 발생")
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # 타임아웃 에러 처리
                if "timeout" in error_str:
                    if api_key:
                        self.api_key_manager.mark_error(api_key, "timeout")
                # Rate limit 또는 API 키 에러인 경우
                elif "rate limit" in error_str or "quota" in error_str or "resource exhausted" in error_str:
                    if api_key:
                        self.api_key_manager.mark_error(api_key, "rate_limit")
                elif "api key" in error_str or "permission" in error_str:
                    if api_key:
                        self.api_key_manager.mark_error(api_key, "invalid_key")
                
                # 마지막 시도가 아니면 다음 키로 재시도
                if attempt < max_retries - 1:
                    continue
                else:
                    raise Exception(f"Gemini API 호출 중 오류가 발생했습니다: {str(e)}")
        
        raise Exception(f"모든 API 키 시도 실패: {str(last_error)}")
    
    async def _generate_with_fast_failover(
        self,
        system_prompt: str,
        user_prompt: str,
        count: int,
        file_paths: Optional[List[str]] = None,
        file_display_names: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> List[Question]:
        """
        빠른 실패 전환: 여러 API 키를 동시에 시도하고 가장 빠른 응답 사용
        """
        # model_name이 지정되지 않은 경우 기본값 사용
        if model_name is None:
            model_name = settings.gemini_model_name
        
        available_keys = self.api_key_manager._get_available_keys()
        if not available_keys:
            raise ValueError("사용 가능한 API 키가 없습니다.")
        
        # 최대 3개 키를 동시에 시도 (너무 많으면 리소스 낭비)
        max_concurrent = min(3, len(available_keys))
        keys_to_try = available_keys[:max_concurrent]
        
        # 여러 키로 동시에 시도
        tasks = []
        for api_key in keys_to_try:
            model = self._get_model(api_key, model_name)
            task = asyncio.create_task(
                self._call_api_with_files(
                    system_prompt, user_prompt, model,
                    file_paths, file_display_names, count, model_name
                )
            )
            tasks.append((task, api_key))
        
        # 가장 빠른 응답을 기다림 (race condition)
        done, pending = await asyncio.wait(
            [task for task, _ in tasks],
            return_when=asyncio.FIRST_COMPLETED,
            timeout=settings.api_call_timeout
        )
        
        # 완료된 작업 처리
        for task, api_key in tasks:
            if task in done:
                try:
                    result = await task
                    if result:
                        questions, used_key = result
                        # 성공한 키 표시
                        self.api_key_manager.mark_success(used_key)
                        # 나머지 작업 취소
                        for pending_task, _ in tasks:
                            if pending_task not in done:
                                pending_task.cancel()
                        return questions
                except Exception as e:
                    error_str = str(e).lower()
                    if "timeout" in error_str:
                        self.api_key_manager.mark_error(api_key, "timeout")
                    continue
        
        # 모든 작업이 실패한 경우
        # 나머지 키로 재시도
        remaining_keys = [k for k in available_keys if k not in keys_to_try]
        if remaining_keys:
            # 재시도 (일반 방식, 최대 3개)
            for api_key in remaining_keys[:3]:
                try:
                    model = self._get_model(api_key, model_name)
                    response = await asyncio.wait_for(
                        self._call_api_with_files(
                            system_prompt, user_prompt, model,
                            file_paths, file_display_names, count, model_name
                        ),
                        timeout=settings.api_retry_timeout
                    )
                    questions = self._parse_response(response, count)
                    self.api_key_manager.mark_success(api_key)
                    return questions
                except Exception as e:
                    error_str = str(e).lower()
                    if "timeout" in error_str:
                        self.api_key_manager.mark_error(api_key, "timeout")
                    continue
        
        raise Exception("모든 API 키에서 실패했습니다.")
    
    async def generate_questions_batch(
        self,
        system_prompts: List[str],
        user_prompts: List[str],
        counts: List[int],
        file_paths_list: Optional[List[Optional[List[str]]]] = None,
        file_display_names_list: Optional[List[Optional[List[str]]]] = None,
        model_names: Optional[List[str]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        배치 문항 생성 (병렬 처리 - 최대 5개 API 키 동시 사용, 타임아웃 처리)
        
        Returns:
            각 배치의 결과를 담은 딕셔너리 리스트:
            [
                {
                    'questions': List[Question],
                    'metadata': {
                        'input_tokens': int,
                        'output_tokens': int,
                        'total_tokens': int,
                        'duration_seconds': float
                    }
                }
            ]
        """
        if not self.api_key_manager:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")
        
        # 입력 검증
        if len(system_prompts) != len(user_prompts) or len(system_prompts) != len(counts):
            raise ValueError("system_prompts, user_prompts, counts의 길이가 같아야 합니다.")
        
        # 배치 크기 결정 (최대 5개 또는 사용 가능한 키 수)
        batch_size = min(self.max_parallel, len(system_prompts), len(self.api_keys))
        
        all_results = []
        
        # 배치 단위로 처리
        for i in range(0, len(system_prompts), batch_size):
            batch_sys_prompts = system_prompts[i:i+batch_size]
            batch_usr_prompts = user_prompts[i:i+batch_size]
            batch_counts = counts[i:i+batch_size]
            batch_file_paths_list = file_paths_list[i:i+batch_size] if file_paths_list else [None] * len(batch_sys_prompts)
            batch_file_display_names_list = file_display_names_list[i:i+batch_size] if file_display_names_list else [None] * len(batch_sys_prompts)
            batch_model_names = model_names[i:i+batch_size] if model_names else [settings.gemini_model_name] * len(batch_sys_prompts)
            
            # 이번 배치에 사용할 API 키 가져오기
            batch_api_keys = self.api_key_manager.get_keys_for_batch(len(batch_sys_prompts))
            
            # ThreadPoolExecutor로 병렬 처리 (타임아웃 포함)
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=len(batch_api_keys)) as executor:
                futures = []
                
                for j, (sys_prompt, usr_prompt, count) in enumerate(zip(batch_sys_prompts, batch_usr_prompts, batch_counts)):
                    api_key = batch_api_keys[j % len(batch_api_keys)]
                    file_paths = batch_file_paths_list[j] if j < len(batch_file_paths_list) else None
                    file_display_names = batch_file_display_names_list[j] if j < len(batch_file_display_names_list) else None
                    model_name = batch_model_names[j] if j < len(batch_model_names) else settings.gemini_model_name
                    
                    future = loop.run_in_executor(
                        executor,
                        self._generate_single_question_sync,
                        api_key,
                        sys_prompt,
                        usr_prompt,
                        count,
                        file_paths,
                        file_display_names,
                        model_name,
                        **kwargs
                    )
                    futures.append(future)
                
                # 타임아웃을 포함한 결과 수집
                batch_results = []
                for future in futures:
                    try:
                        # 각 작업에 개별 타임아웃 설정
                        result = await asyncio.wait_for(
                            asyncio.wrap_future(future),
                            timeout=settings.api_call_timeout
                        )
                        batch_results.append(result)
                    except asyncio.TimeoutError:
                        # 타임아웃 발생 시 빈 결과 반환
                        print(f"⚠️ API 호출 타임아웃 ({settings.api_call_timeout}초 초과)")
                        batch_results.append({
                            'questions': [],
                            'metadata': {
                                'input_tokens': 0,
                                'output_tokens': 0,
                                'total_tokens': 0,
                                'duration_seconds': settings.api_call_timeout,
                                'error': 'Timeout'
                            }
                        })
                    except Exception as e:
                        print(f"⚠️ API 호출 실패: {str(e)[:100]}")
                        batch_results.append({
                            'questions': [],
                            'metadata': {
                                'input_tokens': 0,
                                'output_tokens': 0,
                                'total_tokens': 0,
                                'duration_seconds': 0,
                                'error': str(e)[:100]
                            }
                        })
                
                # 결과 추가
                all_results.extend(batch_results)
        
        return all_results
    
    def _generate_single_question_sync(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        count: int,
        file_paths: Optional[List[str]] = None,
        file_display_names: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        동기 방식으로 단일 문항 생성 (ThreadPoolExecutor용)
        주의: 타임아웃은 상위 레벨의 asyncio.wait_for에서 처리됨
        
        Returns:
            {
                'questions': List[Question],
                'metadata': {
                    'input_tokens': int,
                    'output_tokens': int,
                    'total_tokens': int,
                    'duration_seconds': float
                }
            }
        """
        # model_name이 지정되지 않은 경우 기본값 사용
        if model_name is None:
            model_name = settings.gemini_model_name
        import time
        start_time = time.time()
        
        try:
            model = self._get_model(api_key, model_name)
            
            # 동기 방식으로 파일 업로드 및 API 호출
            import os
            from app.schemas.question_generation import MultipleQuestion
            
            # JSON 스키마 생성
            question_schema_raw = MultipleQuestion.model_json_schema()
            question_schema = self._convert_schema_for_google_genai(question_schema_raw)
            
            # 파일 업로드
            uploaded_files = []
            if file_paths:
                for idx, path in enumerate(file_paths):
                    if path and os.path.exists(path):
                        try:
                            display_name = None
                            if file_display_names and idx < len(file_display_names):
                                display_name = file_display_names[idx]
                            if not display_name:
                                display_name = os.path.basename(path)
                            
                            # upload_file은 path를 첫 번째 위치 인자로 받음
                            uploaded_file = genai.upload_file(
                                path,
                                display_name=display_name if display_name else None
                            )
                            uploaded_files.append(uploaded_file)
                        except Exception as e:
                            print(f"⚠️ 파일 업로드 실패: {path} - {e}")
            
            # 구조화된 출력 설정
            generation_config = genai.GenerationConfig(
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40),
                response_mime_type="application/json",
                response_schema=question_schema
            )
            
            structured_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
            
            # 프롬프트 구성
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # API 호출
            if uploaded_files:
                content_list = uploaded_files + [full_prompt]
                response = structured_model.generate_content(content_list)
            else:
                response = structured_model.generate_content(full_prompt)
            
            # 소요 시간 계산
            end_time = time.time()
            duration = end_time - start_time
            
            # 토큰 정보 추출
            metadata = {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'duration_seconds': round(duration, 2)
            }
            
            # Gemini API의 usage_metadata에서 토큰 정보 추출
            print(f"🔍 [DEBUG] response 객체 확인: hasattr(usage_metadata) = {hasattr(response, 'usage_metadata')}")
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                print(f"📊 [토큰 정보] usage_metadata: {usage}")
                metadata['input_tokens'] = getattr(usage, 'prompt_token_count', 0)
                metadata['output_tokens'] = getattr(usage, 'candidates_token_count', 0)
                metadata['total_tokens'] = getattr(usage, 'total_token_count', 0)
                print(f"✅ [토큰 추출] input={metadata['input_tokens']}, output={metadata['output_tokens']}, total={metadata['total_tokens']}, duration={metadata['duration_seconds']}초")
            else:
                print(f"⚠️ [WARNING] response에 usage_metadata 없음. response 타입: {type(response)}")
                print(f"⚠️ [WARNING] response 속성: {dir(response)}")
            
            questions = self._parse_response(response.text, count)
            
            # 성공 표시
            self.api_key_manager.mark_success(api_key)
            
            return {
                'questions': questions,
                'metadata': metadata
            }
            
        except google_exceptions.ResourceExhausted as e:
            # Rate limit 에러
            self.api_key_manager.mark_error(api_key, "rate_limit")
            end_time = time.time()
            return {
                'questions': [],
                'metadata': {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'duration_seconds': round(end_time - start_time, 2),
                    'error': f"Rate limit exceeded: {str(e)}"
                }
            }
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                self.api_key_manager.mark_error(api_key, "timeout")
            elif "api key" in error_str or "permission" in error_str:
                self.api_key_manager.mark_error(api_key, "invalid_key")
            end_time = time.time()
            return {
                'questions': [],
                'metadata': {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'duration_seconds': round(end_time - start_time, 2),
                    'error': str(e)
                }
            }
    
    async def _call_api(self, prompt: str, model) -> str:
        """Gemini API 호출 (비동기 래퍼)"""
        # 동기 API를 비동기로 실행
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(prompt)
        )
        
        return response.text
    
    async def _call_api_with_files(
        self,
        system_prompt: str,
        user_prompt: str,
        model,
        file_paths: Optional[List[str]] = None,
        file_display_names: Optional[List[str]] = None,
        count: int = 10,
        model_name: Optional[str] = None,
        return_response_obj: bool = False,
        **kwargs
    ):
        """파일이 포함된 Gemini API 호출 (구조화된 출력)
        
        Args:
            return_response_obj: True면 response 객체 전체 반환, False면 response.text만 반환
            
        Returns:
            response 객체 또는 response.text
        """
        # model_name이 지정되지 않은 경우 기본값 사용
        if model_name is None:
            model_name = settings.gemini_model_name
        
        import os
        from app.schemas.question_generation import MultipleQuestion
        
        # JSON 스키마 생성
        question_schema_raw = MultipleQuestion.model_json_schema()
        question_schema = self._convert_schema_for_google_genai(question_schema_raw)
        
        # 파일 업로드
        uploaded_files = []
        if file_paths:
            for idx, path in enumerate(file_paths):
                if path and os.path.exists(path):
                    try:
                        display_name = None
                        if file_display_names and idx < len(file_display_names):
                            display_name = file_display_names[idx]
                        if not display_name:
                            display_name = os.path.basename(path)
                        
                        # upload_file은 path를 첫 번째 위치 인자로 받음
                        uploaded_file = genai.upload_file(
                            path,
                            display_name=display_name if display_name else None
                        )
                        uploaded_files.append(uploaded_file)
                    except Exception as e:
                        print(f"⚠️ 파일 업로드 실패: {path} - {e}")
        
        # 구조화된 출력 설정
        temperature = kwargs.get("temperature", 0.7) if kwargs else 0.7
        top_p = kwargs.get("top_p", 0.95) if kwargs else 0.95
        top_k = kwargs.get("top_k", 40) if kwargs else 40
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            response_mime_type="application/json",
            response_schema=question_schema
        )
        
        # 모델 재생성 (구조화된 출력 설정 포함)
        structured_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        # 프롬프트 구성
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # API 호출
        loop = asyncio.get_event_loop()
        if uploaded_files:
            content_list = uploaded_files + [full_prompt]
            response = await loop.run_in_executor(
                None,
                lambda: structured_model.generate_content(content_list)
            )
        else:
            response = await loop.run_in_executor(
                None,
                lambda: structured_model.generate_content(full_prompt)
            )
        
        # return_response_obj에 따라 반환 형식 결정
        if return_response_obj:
            return response  # 전체 response 객체 반환
        else:
            return response.text  # text만 반환
    
    def _parse_response(self, response_text: str, expected_count: int) -> List[Question]:
        """
        API 응답을 Question 객체 리스트로 파싱
        MultipleQuestion 형식으로 응답이 오는 경우 처리
        """
        from app.schemas.question_generation import MultipleQuestion, LLMQuestion
        
        questions = []
        
        try:
            # JSON 파싱
            data = json.loads(response_text)
            
            # MultipleQuestion 형식인 경우
            if "questions" in data:
                multiple_question = MultipleQuestion(**data)
                for idx, llm_question in enumerate(multiple_question.questions[:expected_count], 1):
                    question = self._convert_llm_question_to_question(llm_question, idx)
                    if question:
                        questions.append(question)
            # 리스트 형식인 경우
            elif isinstance(data, list):
                for idx, item in enumerate(data[:expected_count], 1):
                    if isinstance(item, dict) and "question_text" in item:
                        # LLMQuestion 형식
                        llm_question = LLMQuestion(**item)
                        question = self._convert_llm_question_to_question(llm_question, idx)
                    else:
                        # 기존 형식
                        question = self._parse_question(item, idx)
                    if question:
                        questions.append(question)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 파싱 실패: {e}")
            print(f"응답 텍스트: {response_text[:500]}")
        except Exception as e:
            print(f"⚠️ 응답 파싱 중 오류: {e}")
        
        return questions
    
    def _convert_llm_question_to_question(
        self, 
        llm_question, 
        question_number: int
    ) -> Optional[Question]:
        """LLMQuestion을 Question 형식으로 변환"""
        try:
            from app.schemas.question_generation import (
                Question, PassageInfo, QuestionText, LLMQuestion
            )
            
            # dict인 경우 LLMQuestion으로 변환
            if isinstance(llm_question, dict):
                llm_question = LLMQuestion(**llm_question)
            elif not isinstance(llm_question, LLMQuestion):
                return None
            
            # passage 사용 여부 판단 (빈 문자열이나 None 처리)
            passage = llm_question.passage
            
            # passage가 None이거나 빈 문자열인 경우 처리
            if not passage or (isinstance(passage, str) and not passage.strip()):
                has_passage = False
                original_used = False  # 명시적으로 False 할당
                source_type = "none"
            elif passage == "1":
                has_passage = False
                original_used = True  # 명시적으로 True 할당
                source_type = "original"
            else:
                has_passage = True
                original_used = True  # 명시적으로 True 할당
                source_type = "modified"
            
            return Question(
                question_id=str(question_number),
                question_number=question_number,
                passage_info=PassageInfo(
                    original_used=original_used,
                    source_type=source_type
                ),
                question_text=QuestionText(
                    text=llm_question.question_text,
                    modified_passage=passage if has_passage else None,
                    box_content=llm_question.reference_text if llm_question.reference_text and llm_question.reference_text.strip() else None
                ),
                choices=llm_question.choices,
                correct_answer=llm_question.correct_answer,
                explanation=llm_question.explanation,
                llm_difficulty=llm_question.llm_difficulty
            )
        except Exception as e:
            print(f"⚠️ 문항 변환 실패 [Q{question_number}]: {e}")
            return None
    
    def _convert_schema_for_google_genai(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pydantic JSON 스키마를 Google Generative AI 호환 형식으로 변환 (단순화 버전)
        - $ref를 인라인으로 해결
        - title, default, examples 등 지원하지 않는 필드 제거
        - anyOf는 첫 번째 non-null 옵션 선택
        """
        def resolve_ref(ref_path: str, defs: Dict) -> Dict:
            """$ref 경로를 해결해 실제 스키마 반환"""
            if ref_path.startswith("#/$defs/"):
                def_name = ref_path.split("/")[-1]
                return defs.get(def_name, {})
            return {}
        
        def clean_schema_recursive(obj: Any, defs: Dict) -> Any:
            """재귀적으로 스키마 정리"""
            if isinstance(obj, dict):
                # $ref가 있으면 해결
                if "$ref" in obj:
                    resolved = resolve_ref(obj["$ref"], defs)
                    return clean_schema_recursive(resolved, defs)
                
                result = {}
                for key, value in obj.items():
                    # 지원하지 않는 필드 제거
                    if key in ["title", "default", "examples", "example", "$defs", 
                              "additionalProperties", "const", "format", "$schema", "$id",
                              "minimum", "maximum", "minLength", "maxLength", "pattern",
                              "minItems", "maxItems", "uniqueItems", "multipleOf"]:
                        continue
                    
                    # anyOf 처리: null이 아닌 첫 번째 옵션 선택
                    if key == "anyOf":
                        if isinstance(value, list) and len(value) > 0:
                            for option in value:
                                if isinstance(option, dict):
                                    if "$ref" in option:
                                        resolved = resolve_ref(option["$ref"], defs)
                                        cleaned = clean_schema_recursive(resolved, defs)
                                        if cleaned.get("type") != "null":
                                            result.update(cleaned)
                                            break
                                    elif option.get("type") != "null":
                                        result.update(clean_schema_recursive(option, defs))
                                        break
                        continue
                    
                    # oneOf, allOf도 비슷하게 처리
                    if key == "oneOf":
                        if isinstance(value, list) and len(value) > 0:
                            result.update(clean_schema_recursive(value[0], defs))
                        continue
                    
                    if key == "allOf":
                        if isinstance(value, list):
                            for item in value:
                                result.update(clean_schema_recursive(item, defs))
                        continue
                    
                    # 재귀적으로 정리
                    result[key] = clean_schema_recursive(value, defs)
                
                return result
            elif isinstance(obj, list):
                return [clean_schema_recursive(item, defs) for item in obj]
            else:
                return obj
        
        # 스키마 복사 및 $defs 추출
        schema_copy = schema.copy()
        defs = schema_copy.pop("$defs", {})
        
        # 정리된 스키마 생성
        cleaned = clean_schema_recursive(schema_copy, defs)
        
        # required 검증: properties에 없는 필드 제거
        if isinstance(cleaned, dict) and "required" in cleaned and "properties" in cleaned:
            properties = cleaned.get("properties", {})
            required = cleaned.get("required", [])
            if isinstance(properties, dict) and isinstance(required, list):
                valid_required = [f for f in required if f in properties]
                if valid_required:
                    cleaned["required"] = valid_required
                else:
                    cleaned.pop("required", None)
        
        return cleaned if cleaned else {"type": "object"}
    
    def _parse_question(self, data: dict, question_number: int) -> Optional[Question]:
        """단일 문항 파싱"""
        try:
            from app.schemas.question_generation import (
                Question, PassageInfo, QuestionText, Choice
            )
            
            # original_used 값 처리 (빈 문자열이면 기본값 사용)
            passage_info_data = data.get("passage_info", {})
            original_used_value = passage_info_data.get("original_used", True)
            
            if original_used_value == "" or original_used_value is None:
                original_used_value = True
            
            source_type_value = passage_info_data.get("source_type") or "original"
            
            return Question(
                question_id=str(data.get("question_id", question_number)),
                question_number=question_number,
                passage_info=PassageInfo(
                    original_used=original_used_value,
                    source_type=source_type_value
                ),
                question_text=QuestionText(
                    text=data.get("question_text", {}).get("text", ""),
                    modified_passage=data.get("question_text", {}).get("modified_passage"),
                    box_content=data.get("question_text", {}).get("box_content")
                ),
                choices=[
                    Choice(number=choice["number"], text=choice["text"])
                    for choice in data.get("choices", [])
                ],
                correct_answer=str(data.get("correct_answer", "")),
                explanation=data.get("explanation", "")
            )
        except Exception as e:
            print(f"⚠️ _parse_question 에러: {e}")
            import traceback
            traceback.print_exc()
            return None

