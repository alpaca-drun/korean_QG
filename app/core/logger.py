import logging
import sys
from app.core.config import settings

def setup_logger(name: str = "app"):
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 중복 추가 방지
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# 기본 로거 인스턴스
logger = setup_logger()

