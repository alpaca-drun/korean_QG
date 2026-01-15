from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.schemas.question_generation import Question


class LLMClientBase(ABC):
    """LLM 클라이언트 기본 인터페이스"""
    
    @abstractmethod
    async def generate_questions(
        self,
        system_prompt: str,
        user_prompt: str,
        count: int,
        file_paths: Optional[List[str]] = None,
        file_display_names: Optional[List[str]] = None,
        **kwargs
    ) -> List[Question]:
        """
        문항 생성
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            count: 생성할 문항 수
            file_paths: 업로드할 파일 경로 리스트
            file_display_names: 파일 표시 이름 리스트
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 문항 리스트
        """
        pass
    
    @abstractmethod
    async def generate_questions_batch(
        self,
        system_prompts: List[str],
        user_prompts: List[str],
        counts: List[int],
        file_paths_list: Optional[List[Optional[List[str]]]] = None,
        file_display_names_list: Optional[List[Optional[List[str]]]] = None,
        **kwargs
    ) -> List[List[Question]]:
        """
        배치 문항 생성
        
        Args:
            system_prompts: 시스템 프롬프트 리스트
            user_prompts: 사용자 프롬프트 리스트
            counts: 각 프롬프트별 생성할 문항 수 리스트
            file_paths_list: 각 요청별 파일 경로 리스트
            file_display_names_list: 각 요청별 파일 표시 이름 리스트
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 문항 리스트의 리스트
        """
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """API 키 유효성 검증"""
        pass

