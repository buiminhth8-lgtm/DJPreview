"""AI Music MVP 后端入口。"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.dependencies.config import get_settings
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


@app.get("/", summary="API 信息")
def root() -> dict:
    return {"message": "AI Music MVP API", "docs": "/docs", "health": "/api/v1/health"}
