"""歌曲生成、查询、MIDI、音频渲染与版本管理 API。"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from packages.llm.factory import get_llm_provider
from packages.music_core.composer.music_composer import compose_music
from packages.music_core.editing.diff import diff_music_specs
from packages.music_core.editing.edit_engine import apply_music_edit
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.planner.music_planner import generate_music_spec_from_prompt
from packages.renderer.factory import get_audio_renderer
from services.api.dependencies.config import get_settings
from services.api.schemas.api_models import (
    AssetsResponse,
    AudioAssetInfo,
    AudioMetadata,
    EditSongRequest,
    EditSongResponse,
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
    RestoreVersionResponse,
    VersionInfo,
    VersionsResponse,
)
from services.api.storage.project_store import (
    AUDIO_FILENAME,
    AUDIO_GENERATOR_VERSION,
    create_project,
    create_version,
    get_audio_metadata,
    get_current_version,
    get_midi_path,
    get_project,
    get_project_dir,
    get_version,
    get_wav_path,
    init_version_if_needed,
    is_valid_song_id,
    list_versions,
    restore_version,
    save_audio_metadata,
    save_midi_file,
)

logger = logging.getLogger(__name__)

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


def _regenerate_audio_for(song_id: str) -> None:
    """版本修改/恢复后重新生成 MIDI 与 WAV，保证根目录资源与当前版本一致。"""
    _generate_midi_for(song_id)
    try:
        _render_audio_for(song_id)
    except Exception as exc:  # noqa: BLE001 - 音频渲染失败不影响版本保存
        logger.warning("版本更新后音频重新渲染失败：%s", exc)


def _assets_response(song_id: str) -> AssetsResponse:
    """构建资源状态响应（含当前版本指针）。"""
    project_dir = get_project_dir(song_id)
    has_midi = (project_dir / "output.mid").exists()
    has_audio = (project_dir / "output.wav").exists()
    audio_meta = get_audio_metadata(song_id)
    current = get_current_version(song_id)
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
        current_version=VersionInfo.model_validate(current) if current else None,
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
    init_version_if_needed(song_id)  # 旧项目自动初始化 v1
    return _assets_response(song_id)


@router.post("/songs/{song_id}/edit", response_model=EditSongResponse, summary="自然语言修改音乐")
def edit_song(song_id: str, req: EditSongRequest) -> EditSongResponse:
    try:
        spec = get_project(song_id)
        provider = get_llm_provider()
        edit_spec = provider.generate_music_edit(req.instruction, spec)
        new_spec = apply_music_edit(spec, edit_spec)
        diff = diff_music_specs(spec, new_spec)
        version = create_version(
            song_id,
            new_spec,
            req.instruction,
            edit_spec.model_dump(mode="json"),
        )
        _regenerate_audio_for(song_id)
        return EditSongResponse(
            song_id=song_id,
            version_id=version["version_id"],
            edit_spec=edit_spec,
            diff=diff,
            music_spec=new_spec,
            assets=_assets_response(song_id),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"修改失败：{exc}") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 服务错误：{exc}") from None


@router.get("/songs/{song_id}/versions", response_model=VersionsResponse, summary="版本列表")
def get_versions(song_id: str) -> VersionsResponse:
    try:
        get_project(song_id)
        index = init_version_if_needed(song_id)
        versions = list_versions(song_id)
        return VersionsResponse(
            song_id=song_id,
            current_version_id=index["current_version_id"],
            versions=[VersionInfo.model_validate(v) for v in versions],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/songs/{song_id}/versions/{version_id}/restore", response_model=RestoreVersionResponse, summary="恢复历史版本")
def restore_version_route(song_id: str, version_id: str) -> RestoreVersionResponse:
    try:
        get_project(song_id)
        spec = restore_version(song_id, version_id)
        _regenerate_audio_for(song_id)
        return RestoreVersionResponse(
            song_id=song_id,
            version_id=version_id,
            music_spec=spec,
            assets=_assets_response(song_id),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
