from typing import Optional
from pydantic import BaseModel


class LargeUnit(BaseModel):
    """대단원 모델"""
    id: int
    name: str
    description: Optional[str] = None


class SmallUnit(BaseModel):
    """소단원 모델"""
    id: int
    large_unit_id: int
    name: str
    description: Optional[str] = None


class AchievementStandard(BaseModel):
    """성취기준 모델"""
    code: str
    description: Optional[str] = None
    evaluation_criteria: Optional[str] = None


class Passage(BaseModel):
    """지문 모델"""
    id: int
    achievement_code: Optional[str] = None
    title: str
    content: str
    description: Optional[str] = None

