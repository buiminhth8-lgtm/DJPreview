"""歌曲生成、查询与 MIDI 生成/下载 API。"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.planner.music_planner import generate_music_spec_from_prompt
from services.api.dependencies.config import get_settings
from services.api.schemas.api_models import (
    GenerateMidiResponse,
    GenerateSongRequest,
    GenerateSongResponse,
    GenerateWithMidiResponse,
    GetSongResponse,
    HealthResponse,
    MidiInfo,
    MidiSummary,
)
from services.api.storage.project_store import (
    create_project,
    get_midi_path,
    get_project,
    is_valid_song_id,
    save_midi_file,
)

router = APIRouter()


def _project_dir_for(song_id: str) -> Path:
    """解析项目目录（UUID 校验与 project_store 一致，防止 path traversal）。"""
    if not is_valid_song_id(song_id):
        raise HTTPException(status_code=400, detail="非法 song_id：必须为 UUID 格式")
    return get_settings().projects_dir / song_id


def _generate_midi_for(song_id: str) -> tuple[GenerateMidiResponse, Path]:
    """读取 MusicSpec → 编排 → 写 MIDI → 保存，返回响应与文件路径。"""
    spec = get_project(song_id)
    composition = compose_music(spec)
    midi_path = _project_dir_for(song_id) / "output.mid"
    write_midi(composition, midi_path)
    save_midi_file(song_id, midi_path)
    return (
        GenerateMidiResponse(
            song_id=song_id,
            midi_file="output.mid",
            download_url=f"/api/v1/songs/{song_id}/midi/download",
            summary=MidiSummary(
                tracks=len([t for t in composition.tracks if t.notes]),
                bars=composition.total_bars,
                bpm=composition.bpm,
            ),
        ),
        midi_path,
    )


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


@router.post("/songs/generate-with-midi", response_model=GenerateWithMidiResponse, summary="一步生成 MusicSpec + MIDI")
def generate_song_with_midi(req: GenerateSongRequest) -> GenerateWithMidiResponse:
    try:
        spec = generate_music_spec_from_prompt(req.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"生成失败：{exc}") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 服务错误：{exc}") from None
    song_id = create_project(spec)
    response, _ = _generate_midi_for(song_id)
    return GenerateWithMidiResponse(
        song_id=song_id,
        music_spec=spec,
        midi=MidiInfo(midi_file=response.midi_file, download_url=response.download_url),
    )


@router.get("/songs/{song_id}", response_model=GetSongResponse, summary="获取音乐方案")
def get_song(song_id: str) -> GetSongResponse:
    try:
        spec = get_project(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return GetSongResponse(song_id=song_id, music_spec=spec)


@router.post("/songs/{song_id}/midi/generate", response_model=GenerateMidiResponse, summary="根据 MusicSpec 生成 MIDI")
def generate_midi(song_id: str) -> GenerateMidiResponse:
    try:
        response, _ = _generate_midi_for(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return response


@router.get("/songs/{song_id}/midi/download", summary="下载 MIDI 文件")
def download_midi(song_id: str) -> FileResponse:
    try:
        midi_path = get_midi_path(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"{exc}，请先调用 POST /api/v1/songs/{song_id}/midi/generate",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return FileResponse(midi_path, media_type="audio/midi", filename=f"{song_id}.mid")
