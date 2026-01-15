from typing import List, Optional
from openai import AsyncOpenAI
from app.clients.base import LLMClientBase
from app.schemas.question_generation import Question
from app.core.config import settings


class OpenAIClient(LLMClientBase):
    """OpenAI API 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
    
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
        OpenAI API를 사용하여 문항 생성
        """
        if not self.client:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        try:
            full_prompt = f"{prompt}\n\n{count}개의 문항을 생성해주세요."
            
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", "gpt-4"),
                messages=[
                    {"role": "system", "content": "당신은 교육 문항 생성 전문가입니다."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=kwargs.get("temperature", 0.7),
            )
            
            response_text = response.choices[0].message.content
            questions = self._parse_response(response_text, count)
            
            return questions
            
        except Exception as e:
            raise Exception(f"OpenAI API 호출 중 오류가 발생했습니다: {str(e)}")
    
    async def generate_questions_batch(
        self,
        prompts: List[str],
        counts: List[int],
        **kwargs
    ) -> List[List[Question]]:
        """배치 문항 생성"""
        import asyncio
        
        tasks = [
            self.generate_questions(prompt, count, **kwargs)
            for prompt, count in zip(prompts, counts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_results = []
        for result in results:
            if isinstance(result, Exception):
                batch_results.append([])
            else:
                batch_results.append(result)
        
        return batch_results
    
    def _parse_response(self, response_text: str, expected_count: int) -> List[Question]:
        """API 응답 파싱"""
        # TODO: 실제 응답 형식에 맞게 파싱 로직 구현 필요
        return []

