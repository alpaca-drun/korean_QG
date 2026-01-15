from fastapi import APIRouter
from app.api.v1.endpoints import (
    login,
    large_units,
    small_units,
    achievement_standards,
    passages,
    question_generation,
    result,
    dashboard,
)

api_router = APIRouter()

# 인증 라우터
api_router.include_router(
    login.router,
    prefix="/auth",
    tags=["인증"]
)

# 인증 라우터
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["대시보드"]
)


# 대단원 라우터
api_router.include_router(
    large_units.router,
    prefix="/large-units",
    tags=["메타데이터"]
)

# 소단원 라우터
api_router.include_router(
    small_units.router,
    prefix="/small-units",
    tags=["메타데이터"]
)

# 성취기준 라우터
api_router.include_router(
    achievement_standards.router,
    prefix="/achievement-standards",
    tags=["메타데이터"]
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

# 문항 생성 라우터
api_router.include_router(
    result.router,
    prefix="/result",
    tags=["결과 관리"]
)

