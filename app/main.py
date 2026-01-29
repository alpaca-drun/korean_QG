from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from json.decoder import JSONDecodeError
from app.core.config import settings
from app.api.v1.api import api_router




app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="교육과정 관리 API - 대단원, 소단원, 성취기준, 지문 조회",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS 설정 (환경변수에서 origins 가져오기)
# 프로덕션: CORS_ORIGINS="https://korean.chunjae-it-edu.com"
# 개발: CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

# 개발 모드일 때만 localhost 허용
if settings.debug:
    localhost_origins = ["http://localhost", "http://localhost:3000", "http://localhost:8000", "http://localhost:5173"]
    cors_origins = list(set(cors_origins + localhost_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")


# JSON 파싱 오류 핸들러
@app.exception_handler(JSONDecodeError)
async def json_decode_exception_handler(request: Request, exc: JSONDecodeError):
    """JSON 파싱 오류 핸들러"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "success": False,
            "error": {
                "code": "JSON_PARSE_ERROR",
                "message": "JSON 형식이 올바르지 않습니다.",
                "details": f"JSON 파싱 오류: {str(exc)}",
                "hint": "요청 본문이 유효한 JSON 형식인지 확인해주세요. 모든 속성 이름은 큰따옴표로 둘러싸여 있어야 합니다."
            }
        }),
    )


# 요청 검증 오류 핸들러 개선
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 핸들러"""
    errors = exc.errors()
    
    # JSON 파싱 오류인 경우
    for error in errors:
        if error["type"] == "json_invalid":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=jsonable_encoder({
                    "success": False,
                    "error": {
                        "code": "JSON_PARSE_ERROR",
                        "message": "JSON 형식이 올바르지 않습니다.",
                        "details": error.get("ctx", {}).get("error", str(error.get("msg", ""))),
                        "location": error.get("loc", []),
                        "hint": "요청 본문이 유효한 JSON 형식인지 확인해주세요. 모든 속성 이름은 큰따옴표로 둘러싸여 있어야 합니다."
                    }
                }),
            )
    
    # 일반적인 검증 오류
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "요청 데이터 검증에 실패했습니다.",
                "details": errors
            }
        }),
    )


@app.get("/", tags=["기본"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "교육과정 관리 API에 오신 것을 환영합니다.",
        "docs": "/docs",
        "version": settings.app_version
    }


@app.get("/health", tags=["기본"])
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

