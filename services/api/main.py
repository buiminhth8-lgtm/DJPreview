"""AI Music MVP 后端入口。"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.api.dependencies.config import get_settings
from services.api.routes.soundfonts import router as soundfonts_router
from services.api.routes.songs import router as songs_router

load_dotenv()

settings = get_settings()
settings.projects_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="AI Music MVP",
    description="自然语言生成音乐（MusicSpec v0.1）MVP 后端",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(songs_router, prefix="/api/v1")
app.include_router(soundfonts_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """统一错误响应：结构化 dict 直接透出；字符串 detail 包装为 HTTP_ERROR。"""
    detail = exc.detail
    if isinstance(detail, dict) and {"error_code", "message", "details"} <= set(detail):
        return JSONResponse(status_code=exc.status_code, content=detail)
    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": str(detail.get("detail", detail)),
                "details": {"detail": detail},
            },
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": str(detail),
            "details": {},
        },
    )


@app.get("/", summary="API 信息")
def root() -> dict:
    return {"message": "AI Music MVP API", "docs": "/docs", "health": "/api/v1/health"}
