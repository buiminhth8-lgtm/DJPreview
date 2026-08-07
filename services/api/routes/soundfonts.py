"""SoundFont / 音源管理 API（T29 / T39-B）。"""

from __future__ import annotations

from fastapi import APIRouter

from packages.music_core.audio.soundfont_manager import get_soundfont, list_soundfonts, resolve_default_soundfont
from packages.renderer.fluidsynth_check import detect_fluidsynth, validate_soundfont_file
from services.api.errors import invalid_request, project_not_found
from services.api.schemas.api_models import (
    ProjectSoundfontRequest,
    ProjectSoundfontResponse,
    SoundFontInfo as ApiSoundFontInfo,
    SoundfontDiagnosticsFile,
    SoundfontDiagnosticsResponse,
    SoundfontListResponse,
)
from services.api.storage.project_store import (
    get_project,
    get_project_soundfont,
    save_project_soundfont,
)

router = APIRouter()


def _list_response() -> SoundfontListResponse:
    default = resolve_default_soundfont()
    return SoundfontListResponse(
        soundfonts=[ApiSoundFontInfo(**sf.model_dump()) for sf in list_soundfonts()],
        default_soundfont_id=default.id if default else None,
    )


@router.get("/soundfonts", response_model=SoundfontListResponse, summary="获取音源列表")
def list_soundfonts_route() -> SoundfontListResponse:
    return _list_response()


@router.post("/soundfonts/scan", response_model=SoundfontListResponse, summary="重新扫描音源目录")
def scan_soundfonts_route() -> SoundfontListResponse:
    return _list_response()


@router.get("/soundfonts/diagnostics", response_model=SoundfontDiagnosticsResponse, summary="音源与渲染器诊断")
def soundfont_diagnostics_route() -> SoundfontDiagnosticsResponse:
    from packages.music_core.audio.soundfont_manager import _scan_dirs

    fonts = list_soundfonts()
    fluidsynth = detect_fluidsynth()
    files: list[SoundfontDiagnosticsFile] = []
    for sf in fonts:
        status = validate_soundfont_file(sf.path)
        files.append(
            SoundfontDiagnosticsFile(
                id=sf.id,
                name=sf.name,
                path=sf.path,
                exists=status["exists"],
                readable=status["readable"],
                valid=status["valid"],
                format=status["format"],
                size_bytes=status["size_bytes"],
                error=status["error"],
            )
        )
    return SoundfontDiagnosticsResponse(
        soundfont_dirs=[str(d) for d in _scan_dirs()],
        soundfonts_found=len(fonts),
        soundfonts=files,
        fluidsynth=fluidsynth,
        renderer_backends={
            "fallback": True,
            "fluidsynth": bool(fluidsynth["available"]),
        },
    )


@router.get("/songs/{song_id}/soundfont", response_model=ProjectSoundfontResponse, summary="获取项目音源设置")
def get_project_soundfont_route(song_id: str) -> ProjectSoundfontResponse:
    try:
        get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    saved = get_project_soundfont(song_id)
    available = bool(saved and get_soundfont(saved.get("soundfont_id", "")) is not None)
    warning = "本地缺少对应 SoundFont" if saved and not available else None
    return ProjectSoundfontResponse(song_id=song_id, soundfont=saved, available=available, warning=warning)


@router.put("/songs/{song_id}/soundfont", response_model=ProjectSoundfontResponse, summary="设置项目音源")
def set_project_soundfont_route(song_id: str, req: ProjectSoundfontRequest) -> ProjectSoundfontResponse:
    try:
        get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None

    sf = get_soundfont(req.soundfont_id)
    warning = None
    if sf is None:
        warning = f"soundfont_id={req.soundfont_id} 不存在，已保存为 missing 引用（导入工程缺少本地音源时会出现）"
    data = {
        "soundfont_id": req.soundfont_id,
        "soundfont_name": sf.name if sf else None,
        "renderer": req.renderer or "auto",
    }
    save_project_soundfont(song_id, data)
    return ProjectSoundfontResponse(
        song_id=song_id,
        soundfont=data,
        available=sf is not None,
        warning=warning,
    )
