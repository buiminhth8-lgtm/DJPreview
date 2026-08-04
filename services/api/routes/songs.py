"""歌曲生成与查询 API。"""

from fastapi import APIRouter, HTTPException

from packages.music_core.planner.music_planner import generate_music_spec_from_prompt
from services.api.schemas.api_models import (
    GenerateSongRequest,
    GenerateSongResponse,
    GetSongResponse,
    HealthResponse,
)
from services.api.storage.project_store import create_project, get_project

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="健康检查")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/songs/generate", response_model=GenerateSongResponse, summary="生成音乐方案")
def generate_song(req: GenerateSongRequest) -> GenerateSongResponse:
    try:
        spec = generate_music_spec_from_prompt(req.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"生成失败：{exc}") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 服务错误：{exc}") from None
    song_id = create_project(spec)
    return GenerateSongResponse(song_id=song_id, music_spec=spec)


@router.get("/songs/{song_id}", response_model=GetSongResponse, summary="获取音乐方案")
def get_song(song_id: str) -> GetSongResponse:
    try:
        spec = get_project(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return GetSongResponse(song_id=song_id, music_spec=spec)
