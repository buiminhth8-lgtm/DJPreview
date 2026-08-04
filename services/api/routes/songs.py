"""歌曲生成、查询、MIDI 与音频渲染 API。"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.planner.music_planner import generate_music_spec_from_prompt
from packages.renderer.factory import get_audio_renderer
from services.api.dependencies.config import get_settings
from services.api.schemas.api_models import (
    AssetsResponse,
    AudioAssetInfo,
    AudioMetadata,
    GenerateMidiResponse,
    GenerateSongRequest,
    GenerateSongResponse,
    GenerateWithAudioResponse,
    GenerateWithMidiResponse,
    GetSongResponse,
    HealthResponse,
    MidiAssetInfo,
    MidiInfo,
    MidiSummary,
    RenderAudioResponse,
)
from services.api.storage.project_store import (
    AUDIO_FILENAME,
    AUDIO_GENERATOR_VERSION,
    create_project,
    get_audio_metadata,
    get_midi_path,
    get_project,
    get_project_dir,
    get_wav_path,
    is_valid_song_id,
    save_audio_metadata,
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


def _ensure_midi_for(song_id: str) -> Path:
    """确保项目存在 output.mid；缺失时由 MusicSpec 自动生成。"""
    midi_path = _project_dir_for(song_id) / "output.mid"
    if midi_path.exists():
        return midi_path
    _generate_midi_for(song_id)
    return midi_path


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


@router.post("/songs/generate-with-audio", response_model=GenerateWithAudioResponse, summary="一步生成 MusicSpec + MIDI + WAV")
def generate_song_with_audio(req: GenerateSongRequest) -> GenerateWithAudioResponse:
    try:
        spec = generate_music_spec_from_prompt(req.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"生成失败：{exc}") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 服务错误：{exc}") from None
    song_id = create_project(spec)
    midi_response, _ = _generate_midi_for(song_id)
    audio_response = _render_audio_for(song_id)
    return GenerateWithAudioResponse(
        song_id=song_id,
        music_spec=spec,
        midi=MidiInfo(midi_file=midi_response.midi_file, download_url=midi_response.download_url),
        audio=audio_response,
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


def _render_audio_for(song_id: str) -> RenderAudioResponse:
    """确保 output.mid 存在，调用 AudioRenderer 渲染 WAV 并保存 audio_metadata.json。"""
    settings = get_settings()
    midi_path = _ensure_midi_for(song_id)
    renderer = get_audio_renderer()
    wav_path = _project_dir_for(song_id) / AUDIO_FILENAME
    result = renderer.render_wav(
        midi_path,
        wav_path,
        sample_rate=settings.audio_sample_rate,
        gain=settings.audio_gain,
    )
    metadata = {
        "audio_file": AUDIO_FILENAME,
        "renderer": result.renderer,
        "sample_rate": result.sample_rate,
        "duration_seconds": result.duration_seconds,
        "file_size": result.file_size,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": AUDIO_GENERATOR_VERSION,
        "warnings": result.warnings,
    }
    save_audio_metadata(song_id, metadata)
    return RenderAudioResponse(
        song_id=song_id,
        audio_file=AUDIO_FILENAME,
        stream_url=f"/api/v1/songs/{song_id}/audio/stream",
        download_url=f"/api/v1/songs/{song_id}/audio/download",
        metadata=AudioMetadata.model_validate(metadata),
    )


@router.post("/songs/{song_id}/audio/render", response_model=RenderAudioResponse, summary="渲染 WAV 音频")
def render_audio(song_id: str) -> RenderAudioResponse:
    try:
        get_project(song_id)  # 项目不存在 → 404
        return _render_audio_for(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"音频渲染失败：{exc}") from None


@router.get("/songs/{song_id}/audio/stream", summary="在线播放 WAV")
def stream_audio(song_id: str) -> FileResponse:
    try:
        wav_path = get_wav_path(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"{exc}，请先调用 POST /api/v1/songs/{song_id}/audio/render",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return FileResponse(wav_path, media_type="audio/wav")


@router.get("/songs/{song_id}/audio/download", summary="下载 WAV 文件")
def download_audio(song_id: str) -> FileResponse:
    try:
        wav_path = get_wav_path(song_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"{exc}，请先调用 POST /api/v1/songs/{song_id}/audio/render",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return FileResponse(wav_path, media_type="audio/wav", filename=f"{song_id}.wav")


@router.get("/songs/{song_id}/assets", response_model=AssetsResponse, summary="项目资源状态")
def get_assets(song_id: str) -> AssetsResponse:
    try:
        project_dir = get_project_dir(song_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    if not (project_dir / "music_spec.json").exists():
        raise HTTPException(status_code=404, detail=f"项目不存在：{song_id}")

    has_midi = (project_dir / "output.mid").exists()
    has_audio = (project_dir / "output.wav").exists()
    audio_meta = get_audio_metadata(song_id)
    return AssetsResponse(
        song_id=song_id,
        has_music_spec=True,
        has_midi=has_midi,
        has_audio=has_audio,
        midi=MidiAssetInfo(download_url=f"/api/v1/songs/{song_id}/midi/download") if has_midi else None,
        audio=(
            AudioAssetInfo(
                stream_url=f"/api/v1/songs/{song_id}/audio/stream",
                download_url=f"/api/v1/songs/{song_id}/audio/download",
                metadata=AudioMetadata.model_validate(audio_meta) if audio_meta else None,
            )
            if has_audio
            else None
        ),
    )
