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
    id: int
    small_unit_id: int
    code: str
    content: str
    description: Optional[str] = None


class Passage(BaseModel):
    """지문 모델"""
    id: int
    achievement_standard_id: int
    title: str
    content: str
    description: Optional[str] = None

