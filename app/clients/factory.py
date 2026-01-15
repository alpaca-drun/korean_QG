from typing import Optional, List
from app.clients.base import LLMClientBase
from app.clients.gemini_client import GeminiClient
from app.clients.openai_client import OpenAIClient
from app.core.config import settings


class LLMClientFactory:
    """LLM 클라이언트 팩토리"""
    
    _clients = {
        "gemini": GeminiClient,
        "openai": OpenAIClient,
    }
    
    @classmethod
    def create_client(
        cls,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        api_keys: Optional[List[str]] = None
    ) -> LLMClientBase:
        """
        LLM 클라이언트 생성
        
        Args:
            provider: LLM 제공자 (gemini, openai)
            api_key: 단일 API 키 (선택사항, 하위 호환성)
            api_keys: 여러 API 키 리스트 (선택사항)
            
        Returns:
            LLMClientBase 인스턴스
        """
        provider = provider or settings.default_llm_provider
        
        if provider not in cls._clients:
            raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")
        
        client_class = cls._clients[provider]
        
        # Gemini 클라이언트인 경우 여러 API 키 지원
        if provider == "gemini" and api_keys:
            return client_class(api_keys=api_keys)
        elif provider == "gemini" and api_key:
            return client_class(api_key=api_key)
        else:
            return client_class(api_key=api_key)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """사용 가능한 LLM 제공자 목록 반환"""
        return list(cls._clients.keys())

