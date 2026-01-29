"""파일 경로 유틸리티 모듈"""
import os
import re
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.core.logger import logger


def parse_school_level_to_path(school_level: str) -> str:
    """
    school_level 값을 파일 경로 형식으로 변환
    
    Args:
        school_level: 학교급 정보 (예: "초등학교", "중학교", "고등학교")
        
    Returns:
        학교급 형식의 문자열 (예: "elementary_school", "middle_school", "high_school")
    """
    if not school_level:
        return "default"
    
    # 문자열로 변환 및 정규화
    school_level = str(school_level).strip().lower()
    
    # 학교급 매핑
    if "초등" in school_level or "elementary" in school_level:
        return "elementary_school"
    elif "중학" in school_level or "중등" in school_level or "middle" in school_level:
        return "middle_school"
    elif "고등" in school_level or "고교" in school_level or "high" in school_level:
        return "high_school"
    else:
        # 알 수 없는 경우 정규화된 값 반환
        return re.sub(r'[^\w]', '_', school_level).lower() or "default"


def resolve_file_paths(
    file_paths: Optional[List[str]],
    school_level: Optional[str] = None,
    base_path: Optional[str] = None
) -> List[str]:
    """
    파일 경로를 실제 경로로 변환
    
    Args:
        file_paths: 파일 경로 리스트 (파일명, 상대 경로, 또는 절대 경로)
        school_level: 학교급 정보 (예: "초등학교", "중학교", "고등학교") - 학교급별로 경로가 달라짐
        base_path: 기본 경로 (None이면 settings.file_storage_path 사용)
        
    Returns:
        실제 파일 경로 리스트 (존재하지 않는 파일은 제외)
    """
    if not file_paths:
        return []
    
    # 기본 경로 설정
    if base_path is None:
        base_path = settings.file_storage_path
    
    # school_level이 있으면 학교급 경로에 추가
    if school_level:
        school_path = parse_school_level_to_path(school_level)
        base_path = os.path.join(base_path, school_path)
    
    # 기본 경로를 절대 경로로 변환
    if not os.path.isabs(base_path):
        # 상대 경로인 경우 app 디렉토리 기준으로 변환
        app_dir = Path(__file__).parent.parent  # app 디렉토리
        base_path = str(app_dir / base_path)
    
    resolved_paths = []
    
    for file_path in file_paths:
        if not file_path:
            continue
        
        # 절대 경로인 경우 그대로 사용
        if os.path.isabs(file_path):
            resolved_path = file_path
        else:
            # 상대 경로 또는 파일명인 경우 기본 경로와 결합
            resolved_path = os.path.join(base_path, file_path)
        
        # 경로 정규화 (../, ./ 제거 등)
        resolved_path = os.path.normpath(resolved_path)
        
        # 파일 존재 여부 확인
        if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
            resolved_paths.append(resolved_path)
        else:
            logger.warning("파일을 찾을 수 없습니다: %s", resolved_path)
    
    return resolved_paths


def ensure_storage_directory(school_level: Optional[str] = None):
    """
    파일 저장 디렉토리가 존재하는지 확인하고, 없으면 생성
    
    Args:
        school_level: 학교급 정보 (예: "초등학교", "중학교", "고등학교") - 학교급별로 경로가 달라짐
    """
    storage_path = settings.file_storage_path
    
    # school_level이 있으면 학교급 경로에 추가
    if school_level:
        school_path = parse_school_level_to_path(school_level)
        storage_path = os.path.join(storage_path, school_path)
    
    # 상대 경로인 경우 app 디렉토리 기준으로 변환
    if not os.path.isabs(storage_path):
        app_dir = Path(__file__).parent.parent  # app 디렉토리
        storage_path = str(app_dir / storage_path)
    
    # 경로 정규화
    storage_path = os.path.normpath(storage_path)
    
    # 디렉토리가 없으면 생성
    if not os.path.exists(storage_path):
        os.makedirs(storage_path, exist_ok=True)
        logger.info("파일 저장 디렉토리 생성: %s", storage_path)
    
    return storage_path

