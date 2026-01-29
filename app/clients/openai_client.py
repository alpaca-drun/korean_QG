from typing import List, Optional
import asyncio
from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError
from app.clients.base import LLMClientBase
from app.schemas.question_generation import Question
from app.core.config import settings
from app.core.logger import logger


class OpenAIClient(LLMClientBase):
    """OpenAI API 클라이언트"""
    
    # 재시도 설정
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 초
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=settings.api_call_timeout  # 타임아웃 설정
        ) if self.api_key else None
    
    def validate_api_key(self) -> bool:
        """API 키 유효성 검증"""
        if not self.api_key:
            return False
        try:
            # 간단한 테스트 요청으로 검증
            return True
        except Exception:
            return False
    
    async def generate_questions(
        self,
        prompt: str,
        count: int,
        **kwargs
    ) -> List[Question]:
        """
        OpenAI API를 사용하여 문항 생성 (타임아웃 및 재시도 지원)
        """
        if not self.client:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        full_prompt = f"{prompt}\n\n{count}개의 문항을 생성해주세요."
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug("OpenAI API 호출 시작 (시도 %d/%d)", attempt + 1, self.MAX_RETRIES)
                
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=kwargs.get("model", "gpt-4"),
                        messages=[
                            {"role": "system", "content": "당신은 교육 문항 생성 전문가입니다."},
                            {"role": "user", "content": full_prompt}
                        ],
                        temperature=kwargs.get("temperature", 0.7),
                    ),
                    timeout=settings.api_call_timeout
                )
                
                response_text = response.choices[0].message.content
                questions = self._parse_response(response_text, count)
                
                logger.debug("OpenAI API 호출 성공")
                return questions
                
            except RateLimitError as e:
                logger.warning("OpenAI API Rate Limit 도달 (시도 %d/%d): %s", attempt + 1, self.MAX_RETRIES, e)
                last_error = e
                # Rate limit은 더 오래 대기
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1) * 2)
                
            except (APITimeoutError, asyncio.TimeoutError) as e:
                logger.warning("OpenAI API 타임아웃 (시도 %d/%d): %s", attempt + 1, self.MAX_RETRIES, e)
                last_error = e
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except APIConnectionError as e:
                logger.warning("OpenAI API 연결 오류 (시도 %d/%d): %s", attempt + 1, self.MAX_RETRIES, e)
                last_error = e
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except Exception as e:
                logger.exception("OpenAI API 호출 중 예기치 않은 오류 (시도 %d/%d)", attempt + 1, self.MAX_RETRIES)
                last_error = e
                # 예기치 않은 오류는 재시도하지 않고 바로 실패
                break
        
        logger.error("OpenAI API 호출 최종 실패: %s", last_error)
        raise Exception(f"OpenAI API 호출 중 오류가 발생했습니다: {str(last_error)}")
    
    async def generate_questions_batch(
        self,
        prompts: List[str],
        counts: List[int],
        **kwargs
    ) -> List[List[Question]]:
        """배치 문항 생성 (타임아웃 지원)"""
        tasks = [
            self.generate_questions(prompt, count, **kwargs)
            for prompt, count in zip(prompts, counts)
        ]
        
        try:
            # 배치 전체에 대한 타임아웃 설정
            batch_timeout = settings.api_call_timeout * len(tasks)
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=batch_timeout
            )
        except asyncio.TimeoutError:
            logger.error("배치 문항 생성 전체 타임아웃")
            return [[] for _ in prompts]
        
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("배치 %d 문항 생성 실패: %s", i, result)
                batch_results.append([])
            else:
                batch_results.append(result)
        
        return batch_results
    
    def _parse_response(self, response_text: str, expected_count: int) -> List[Question]:
        """API 응답 파싱"""
        # TODO: 실제 응답 형식에 맞게 파싱 로직 구현 필요
        return []

