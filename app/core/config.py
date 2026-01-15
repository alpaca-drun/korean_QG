from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    app_name: str = "Curriculum API"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM API 설정
    gemini_api_key: Optional[str] = None
    gemini_api_keys: Optional[str] = None  # 콤마로 구분된 여러 키 (예: "key1,key2,key3")
    openai_api_key: Optional[str] = None
    default_llm_provider: str = "gemini"  # gemini, openai
    
    # API 키 로테이션 설정
    api_key_rotation_strategy: str = "round_robin"  # round_robin, random, failover
    max_parallel_api_keys: int = 5  # 병렬 처리에 사용할 최대 API 키 수
    
    # 비동기 작업 설정
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    enable_celery: bool = False  # True로 설정하면 Celery 사용
    
    # 배치 작업 설정
    max_batch_size: int = 10
    batch_timeout: int = 30  # 초
    
    # API 호출 타임아웃 설정
    api_call_timeout: int = 60  # 단일 API 호출 타임아웃 (초)
    api_retry_timeout: int = 30  # 재시도 시 타임아웃 (초)
    enable_fast_failover: bool = True  # 빠른 실패 전환 활성화
    
    # DB 설정
    db_host: Optional[str] = None
    db_port: int = 3306
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_database: Optional[str] = None
    db_env_prefix: str = "QG_db"  # DB 환경변수 접두사
    
    # 파일 저장소 설정
    file_storage_path: str = "storage/files"  # 파일 저장 폴더 경로 (env에서 설정 가능, app 디렉토리 기준)
    
    # JWT 인증 설정
    jwt_secret_key: str = "your-secret-key-change-this-in-production"  # 프로덕션에서는 반드시 변경
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30  # 액세스 토큰 만료 시간 (분)
    jwt_refresh_token_expire_days: int = 7  # 리프레시 토큰 만료 시간 (일)
    
    @field_validator('max_parallel_api_keys', 'max_batch_size', 'batch_timeout', 
                     'api_call_timeout', 'api_retry_timeout', 'db_port', mode='before')
    @classmethod
    def parse_int(cls, v):
        """정수 값 파싱 (문자열에서 공백 제거)"""
        if isinstance(v, str):
            return int(v.strip())
        return v
    
    @field_validator('enable_fast_failover', 'enable_celery', 'debug', mode='before')
    @classmethod
    def parse_bool(cls, v):
        """불린 값 파싱 (문자열에서 공백 제거 및 대소문자 무시)"""
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ('true', '1', 'yes', 'on'):
                return True
            elif v in ('false', '0', 'no', 'off'):
                return False
        return v
    
    @property
    def gemini_api_key_list(self) -> List[str]:
        """Gemini API 키 리스트 반환"""
        if self.gemini_api_keys:
            keys = [key.strip() for key in self.gemini_api_keys.split(",") if key.strip()]
            if keys:
                return keys
        if self.gemini_api_key:
            return [self.gemini_api_key]
        return []
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
