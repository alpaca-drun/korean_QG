from fastapi import APIRouter
from app.api.v1.endpoints import (
    large_units,
    small_units,
    achievement_standards,
    passages,
    question_generation
)

api_router = APIRouter()

# 대단원 라우터
api_router.include_router(
    large_units.router,
    prefix="/large-units",
    tags=["대단원"]
)

# 소단원 라우터
api_router.include_router(
    small_units.router,
    prefix="/small-units",
    tags=["소단원"]
)

# 성취기준 라우터
api_router.include_router(
    achievement_standards.router,
    prefix="/achievement-standards",
    tags=["성취기준"]
)

# 지문 라우터
api_router.include_router(
    passages.router,
    prefix="/passages",
    tags=["지문"]
)

# 문항 생성 라우터
api_router.include_router(
    question_generation.router,
    prefix="/question-generation",
    tags=["문항 생성"]
)

