"""파일 경로 유틸리티 모듈"""
import os
import re
from pathlib import Path
from typing import List, Optional
from app.core.config import settings


def parse_grade_level_to_path(grade_level: str) -> str:
    """
    grade_level 값을 파일 경로 형식으로 변환
    
    Args:
        grade_level: 학년 정보 (예: "중학교 1학년", "고등학교 2학년")
        
    Returns:
        파일 경로 형식의 문자열 (예: "middle_school_1", "high_school_2")
    """
    if not grade_level:
        return "default"
    
    # 정규화 (공백 제거 등)
    grade_level = grade_level.strip()
    
    # 중학교/고등학교 구분 및 학년 추출
    if "중학교" in grade_level or "중" in grade_level:
        school_type = "middle_school"
    elif "고등학교" in grade_level or "고등" in grade_level or "고" in grade_level:
        school_type = "high_school"
    elif "초등학교" in grade_level or "초등" in grade_level or "초" in grade_level:
        school_type = "elementary_school"
    else:
        # 알 수 없는 경우 grade_level을 그대로 사용 (공백은 언더스코어로 변환)
        return re.sub(r'[^\w가-힣]', '_', grade_level).lower()
    
    # 학년 추출 (1~6 숫자)
    grade_match = re.search(r'(\d+)', grade_level)
    if grade_match:
        grade = grade_match.group(1)
    else:
        grade = "1"  # 기본값
    
    return f"{school_type}_{grade}"


def resolve_file_paths(
    file_paths: Optional[List[str]],
    grade_level: Optional[str] = None,
    base_path: Optional[str] = None
) -> List[str]:
    """
    파일 경로를 실제 경로로 변환
    
    Args:
        file_paths: 파일 경로 리스트 (파일명, 상대 경로, 또는 절대 경로)
        grade_level: 학년 정보 (예: "중학교 1학년") - grade_level에 따라 경로가 달라짐
        base_path: 기본 경로 (None이면 settings.file_storage_path 사용)
        
    Returns:
        실제 파일 경로 리스트 (존재하지 않는 파일은 제외)
    """
    if not file_paths:
        return []
    
    # 기본 경로 설정
    if base_path is None:
        base_path = settings.file_storage_path
    
    # grade_level이 있으면 경로에 추가
    if grade_level:
        grade_path = parse_grade_level_to_path(grade_level)
        base_path = os.path.join(base_path, grade_path)
    
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
            print(f"⚠️ 파일을 찾을 수 없습니다: {resolved_path}")
    
    return resolved_paths


def ensure_storage_directory(grade_level: Optional[str] = None):
    """
    파일 저장 디렉토리가 존재하는지 확인하고, 없으면 생성
    
    Args:
        grade_level: 학년 정보 (예: "중학교 1학년") - grade_level에 따라 경로가 달라짐
    """
    storage_path = settings.file_storage_path
    
    # grade_level이 있으면 경로에 추가
    if grade_level:
        grade_path = parse_grade_level_to_path(grade_level)
        storage_path = os.path.join(storage_path, grade_path)
    
    # 상대 경로인 경우 app 디렉토리 기준으로 변환
    if not os.path.isabs(storage_path):
        app_dir = Path(__file__).parent.parent  # app 디렉토리
        storage_path = str(app_dir / storage_path)
    
    # 경로 정규화
    storage_path = os.path.normpath(storage_path)
    
    # 디렉토리가 없으면 생성
    if not os.path.exists(storage_path):
        os.makedirs(storage_path, exist_ok=True)
        print(f"📁 파일 저장 디렉토리 생성: {storage_path}")
    
    return storage_path

