"""AI Music MVP 后端入口。"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.music_core.config.env_loader import load_env
from services.api.dependencies.config import get_settings
from services.api.logging_config import setup_logging
from services.api.middleware.request_id import RequestIdMiddleware
from services.api.routes.render_tasks import router as render_tasks_router
from services.api.routes.soundfonts import router as soundfonts_router
from services.api.routes.songs import router as songs_router

# 尽早加载 env：.env -> profile（.mock.env/.lmstudio.env/.gemini.env/.deepseek.env）-> LLM_ENV_FILE
# 系统环境变量最高优先级，不会被文件覆盖。
env_info = load_env(env_dir=Path(__file__).resolve().parents[2])
setup_logging()
logger = logging.getLogger("aimusic")
logger.info(env_info.summary())

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
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)

app.include_router(songs_router, prefix="/api/v1")
app.include_router(soundfonts_router, prefix="/api/v1")
app.include_router(render_tasks_router, prefix="/api/v1")


def _request_id(request: Request) -> str:
    state = getattr(request, "state", None)
    return getattr(state, "request_id", "") if state is not None else ""


def _error_body(request: Request, exc: HTTPException, code: str, message: str, details: dict) -> dict:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    stage = detail.get("stage", "unknown")
    provider = detail.get("provider")
    status = detail.get("status", exc.status_code)
    request_id = _request_id(request)
    return {
        "success": False,
        "request_id": request_id,
        "error_code": code,
        "message": message,
        "details": details,
        "error": {
            "code": code,
            "message": message,
            "stage": stage,
            "provider": provider,
            "status_code": status,
            "details": details,
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一错误响应：结构化 dict 展开为 T35 错误结构，同时保留旧字段兼容。"""
    detail = exc.detail
    if isinstance(detail, dict) and {"error_code", "message", "details"} <= set(detail):
        body = _error_body(
            request,
            exc,
            detail["error_code"],
            detail["message"],
            detail.get("details", {}),
        )
        return JSONResponse(status_code=exc.status_code, content=body)
    if isinstance(detail, dict):
        body = _error_body(
            request,
            exc,
            "HTTP_ERROR",
            str(detail.get("detail", detail)),
            {"detail": detail},
        )
        return JSONResponse(status_code=exc.status_code, content=body)
    body = _error_body(request, exc, "HTTP_ERROR", str(detail), {})
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底 500：记录 traceback（不返回给前端），返回结构化错误。"""
    request_id = _request_id(request)
    logger.exception("[request_id=%s] unhandled error: %s", request_id, exc)
    body = _error_body(
        request,
        HTTPException(status_code=500, detail="服务器内部错误"),
        "INTERNAL_ERROR",
        "服务器内部错误",
        {"request_id": request_id},
    )
    return JSONResponse(status_code=500, content=body)


@app.get("/", summary="API 信息")
def root() -> dict:
    return {"message": "AI Music MVP API", "docs": "/docs", "health": "/api/v1/health"}
