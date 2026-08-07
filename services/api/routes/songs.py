"""歌曲生成、查询、MIDI、音频、版本、混音、分析、风格、参考、工程与评估 API。"""

import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse

from packages.llm.factory import get_llm_provider
from packages.llm.structured_call import (
    LLMAPIError,
    LLMConfigurationError,
    LLMOutputError,
)
from packages.llm.trace import api_logger, get_request_id, log_stage
from packages.music_core.audio.soundfont_manager import get_soundfont, resolve_default_soundfont
from packages.music_core.analysis.midi_parser import parse_midi_to_notes
from packages.music_core.analysis.piano_roll import build_piano_roll_data
from packages.music_core.analysis.quality_checker import QualityReport, check_arrangement_quality
from packages.music_core.composer.music_composer import compose_music
from packages.music_core.editing.diff import diff_music_specs
from packages.music_core.editing.edit_engine import apply_music_edit
from packages.music_core.evaluation.eval_fixtures import get_eval_cases
from packages.music_core.evaluation.eval_models import EvalCase, EvalReport
from packages.music_core.evaluation.eval_runner import run_generation_eval
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.mix.mix_engine import (
    apply_mix_to_composition,
    create_default_mix_spec,
    sync_mix_spec_with_music_spec,
    update_track_mix,
)
from packages.music_core.mix.mix_models import MixSpec
from packages.music_core.optimization.arrangement_optimizer import optimize_arrangement
from packages.music_core.planner.music_planner import generate_music_spec_from_prompt
from packages.music_core.project_io.project_bundle import export_project_bundle
from packages.music_core.project_io.project_importer import import_project_bundle
from packages.music_core.reference.reference_analyzer import analyze_reference_midi
from packages.music_core.reference.reference_models import ReferenceMidiAnalysis
from packages.music_core.reference.reference_to_spec import build_music_spec_from_reference
from packages.music_core.regeneration.regeneration_engine import regenerate_music_spec
from packages.music_core.regeneration.regeneration_models import RegenerationRequest, RegenerationResult
from packages.music_core.styles.style_applier import apply_style_template_to_music_spec
from packages.music_core.styles.style_library import get_style_template, list_style_templates
from packages.music_core.styles.style_models import StyleTemplateSpec
from packages.music_core.validation.spec_validator import validate_music_spec_semantics
from packages.music_core.versioning.version_assets import mirror_stems_to_root
from packages.renderer.fallback_renderer import FallbackRenderer
from packages.renderer.fluidsynth_check import detect_fluidsynth, validate_soundfont_file
from packages.renderer.fluidsynth_renderer import FluidSynthRenderer
from packages.renderer.renderer_metadata import (
    REASON_FLUIDSYNTH_RENDER_FAILED,
    REASON_FLUIDSYNTH_UNAVAILABLE,
    REASON_NO_SOUNDFONT_SELECTED,
    REASON_RENDERER_NOT_CONFIGURED,
    REASON_SOUNDFONT_FILE_MISSING,
    REASON_SOUNDFONT_NOT_FOUND,
    build_renderer_metadata,
)
from packages.renderer.stem_renderer import export_stems as export_stems_impl
from services.api.dependencies.config import get_settings
from services.api.tasks.render_task_service import song_render_lock
from services.api.errors import (
    ApiErrorCode,
    api_error,
    asset_not_found,
    internal_error,
    invalid_bundle,
    invalid_request,
    json_parse_error,
    llm_error,
    llm_http_error,
    llm_invalid_response,
    llm_timeout,
    project_not_found,
    render_failed,
    spec_validation_failed,
    unknown_provider,
    version_not_found,
)
from services.api.schemas.api_models import (
    ApplyMixResponse,
    AssetsResponse,
    AudioAssetInfo,
    AudioMetadata,
    EditSongRequest,
    EditSongResponse,
    EvalRunRequest,
    GenerateFromReferenceResponse,
    GenerateMidiResponse,
    GenerateSongRequest,
    GenerateSongResponse,
    GenerateWithAudioResponse,
    GenerateWithMidiResponse,
    GenerationDebug,
    GetSongResponse,
    HealthResponse,
    MidiAssetInfo,
    MidiInfo,
    MidiSummary,
    MixResponse,
    MixUpdateResponse,
    OptimizeRequest,
    OptimizeResponse,
    PianoRollResponse,
    ProjectImportResponse,
    ProjectListResponse,
    ProjectSummaryItem,
    RenderAudioResponse,
    RestoreSummary,
    RestoreVersionResponse,
    StemExportResponse,
    StemInfo,
    UpdateMixRequest,
    VersionAssetInfo,
    VersionDiffResponse,
    VersionDetailResponse,
    VersionInfo,
    VersionsResponse,
    WarningItem,
)
from services.api.storage.project_store import (
    AUDIO_FILENAME,
    AUDIO_GENERATOR_VERSION,
      create_project,
      create_version,
      delete_project,
      get_audio_metadata,
      get_current_version,
      get_midi_path,
      get_mix_spec,
      get_project,
      get_project_dir,
      get_project_soundfont,
      get_project_summary,
      get_quality_report as get_quality_report_store,
      get_stems_dir,
      get_stems_zip_path,
      get_version_detail as get_version_detail_store,
      get_version_diff as get_version_diff_store,
      get_wav_path,
      init_version_if_needed,
      is_valid_song_id,
      list_project_ids,
      list_versions,
    restore_version,
    save_audio_metadata,
    save_midi_file,
    save_mix_spec,
    save_optimize_report,
    save_quality_report,
)
from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


def _map_llm_exception(exc: Exception, provider: str | None = None) -> HTTPException:
    """把 LLM 层异常映射为带 stage / code 的统一 HTTP 错误。"""
    if isinstance(exc, LLMConfigurationError):
        return llm_error("模型配置错误", details={"reason": str(exc)}, stage="provider_selection", provider=provider)
    if isinstance(exc, LLMAPIError):
        if exc.status_code in (400, 401, 403, 404, 429, 500, 502, 503):
            return llm_http_error(
                str(exc),
                details={"provider": provider, "upstream_status": exc.status_code},
                status_code=502,
                provider=provider,
            )
        if "超时" in str(exc):
            return llm_timeout(str(exc), details={"provider": provider}, provider=provider)
        return llm_error(str(exc), details={"provider": provider}, provider=provider)
    if isinstance(exc, LLMOutputError):
        details: dict = {"task_name": exc.task_name, "provider": provider}
        # 透传调试元数据（仅本地路径 / finish_reason / content_chars / hint，不含完整 content）
        if getattr(exc, "debug_info", None):
            for key in (
                "finish_reason",
                "content_chars",
                "raw_response_path",
                "message_content_path",
                "hint",
                "provider",
                "model",
            ):
                value = exc.debug_info.get(key)
                if value is not None:
                    details[key] = value
        return llm_invalid_response(
            f"模型输出解析失败：{exc}",
            details=details,
            provider=provider,
        )
    return llm_error(str(exc), details={"provider": provider}, provider=provider)


def _run_generate_llm(req: GenerateSongRequest) -> tuple[MusicSpec, StyleTemplateSpec | None, float, str, str | None]:
    """执行生成 LLM 链路并记录阶段日志；返回 (spec, style_template, llm_duration_ms, provider, model)。"""
    provider = get_llm_provider()
    log_stage(api_logger, "generate_music_spec.start", provider=provider.name)
    started = time.monotonic()
    spec = generate_music_spec_from_prompt(req.prompt)
    duration_ms = int((time.monotonic() - started) * 1000)
    style_template = None
    if req.style_template_id:
        style_template = get_style_template(req.style_template_id)
        spec = apply_style_template_to_music_spec(spec, style_template, req.style_strength)
    return spec, style_template, duration_ms, provider.name, getattr(provider, "model", None)


def _validation_warnings(validation) -> list[WarningItem]:
    """把 ValidationResult.warnings 转为结构化 WarningItem。"""
    if validation is None:
        return []
    return [
        WarningItem(code=item.code, message=item.message, stage="music_spec_validation", severity="warning")
        for item in validation.warnings
    ]


def _project_dir_for(song_id: str) -> Path:
    """解析项目目录（UUID 校验与 project_store 一致，防止 path traversal）。"""
    if not is_valid_song_id(song_id):
        raise invalid_request("非法 song_id：必须为 UUID 格式")
    return get_settings().projects_dir / song_id


def _generate_midi_for(song_id: str) -> tuple[GenerateMidiResponse, Path]:
    """读取 MusicSpec → 编排 → 写 MIDI → 保存，返回响应与文件路径。"""
    with song_render_lock(song_id):
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
    """确保 output.mid 存在，调用 AudioRenderer 渲染 WAV 并保存 audio_metadata.json。

    渲染决策：
    - 有已选择的 SoundFont 且文件有效、FluidSynth 可用 → 优先 FluidSynth renderer；
    - 否则回退 FallbackRenderer，并写入结构化 fallback_reason。
    """
    with song_render_lock(song_id):
        settings = get_settings()
        midi_path = _ensure_midi_for(song_id)
        wav_path = _project_dir_for(song_id) / AUDIO_FILENAME
        fluidsynth_status = detect_fluidsynth()
        renderer_cfg = (settings.audio_renderer or "auto").strip().lower()

        # 解析音源：项目级设置 > 默认策略
        soundfont = None
        fallback_reason: str | None = None
        soundfont_warnings: list[str] = []
        if renderer_cfg == "fallback":
            fallback_reason = REASON_RENDERER_NOT_CONFIGURED
        else:
            project_sf = get_project_soundfont(song_id)
            if project_sf and project_sf.get("soundfont_id"):
                soundfont = get_soundfont(project_sf["soundfont_id"])
                if soundfont is None:
                    fallback_reason = REASON_SOUNDFONT_NOT_FOUND
                    soundfont_warnings.append(
                        f"项目指定的音源 {project_sf['soundfont_id']} 本地缺失，使用默认渲染策略"
                    )
            if soundfont is None and fallback_reason is None:
                soundfont = resolve_default_soundfont()
            if soundfont is None and fallback_reason is None:
                fallback_reason = REASON_NO_SOUNDFONT_SELECTED

        # 决定是否使用 FluidSynth
        result = None
        is_fallback = True
        if fallback_reason is None and soundfont is not None:
            sf_status = validate_soundfont_file(soundfont.path)
            if not sf_status["valid"]:
                fallback_reason = REASON_SOUNDFONT_FILE_MISSING
                soundfont_warnings.append(f"SoundFont 文件校验失败：{sf_status.get('error') or 'unknown'}")
            elif not fluidsynth_status["available"]:
                fallback_reason = REASON_FLUIDSYNTH_UNAVAILABLE
            else:
                try:
                    result = FluidSynthRenderer().render_wav(
                        midi_path,
                        wav_path,
                        sample_rate=settings.audio_sample_rate,
                        gain=settings.audio_gain,
                        soundfont_path=soundfont.path,
                    )
                    is_fallback = False
                except Exception as exc:  # noqa: BLE001 - 单个渲染失败回退，不中断服务
                    logger.warning("FluidSynth 渲染失败，回退 fallback：%s", exc)
                    fallback_reason = REASON_FLUIDSYNTH_RENDER_FAILED

        # 回退渲染
        if result is None:
            result = FallbackRenderer().render_wav(
                midi_path,
                wav_path,
                sample_rate=settings.audio_sample_rate,
                gain=settings.audio_gain,
            )

        renderer_meta = build_renderer_metadata(
            renderer=result.renderer,
            soundfont_id=soundfont.id if soundfont else None,
            soundfont_name=soundfont.name if soundfont else None,
            soundfont_path=Path(soundfont.path).name if soundfont else None,
            is_fallback=is_fallback,
            fallback_reason=fallback_reason,
        )
        metadata = {
            "audio_file": AUDIO_FILENAME,
            "renderer": result.renderer,
            "sample_rate": result.sample_rate,
            "duration_seconds": result.duration_seconds,
            "file_size": result.file_size,
            "soundfont_id": soundfont.id if soundfont else None,
            "soundfont_name": soundfont.name if soundfont else None,
            "soundfont_path": Path(soundfont.path).name if soundfont else None,
            "fluidsynth": fluidsynth_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator_version": AUDIO_GENERATOR_VERSION,
            "warnings": [*result.warnings, *soundfont_warnings],
            **renderer_meta,
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
    """版本修改/恢复/重生成后重新生成 MIDI 与 WAV（不应用混音）。"""
    _generate_midi_for(song_id)
    try:
        _render_audio_for(song_id)
    except Exception as exc:  # noqa: BLE001 - 音频渲染失败不影响版本保存
        logger.warning("版本更新后音频重新渲染失败：%s", exc)


def _regenerate_with_mix(song_id: str, mix_spec: MixSpec) -> list[str]:
    """按 MixSpec 重新 compose、应用混音、写 MIDI 并渲染 WAV，返回 warning。"""
    spec = get_project(song_id)
    composition = compose_music(spec)
    composition = apply_mix_to_composition(composition, mix_spec)
    midi_path = _project_dir_for(song_id) / "output.mid"
    write_midi(composition, midi_path)
    save_midi_file(song_id, midi_path)
    warnings = list(composition.warnings)
    try:
        _render_audio_for(song_id)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"音频渲染失败：{exc}")
        logger.warning("mix apply 音频渲染失败：%s", exc)
    return warnings


def _assets_response(song_id: str) -> AssetsResponse:
    """构建资源状态响应（含当前版本指针）。"""
    project_dir = get_project_dir(song_id)
    has_midi = (project_dir / "output.mid").exists()
    has_audio = (project_dir / "output.wav").exists()
    has_mix = (project_dir / "mix_spec.json").exists()
    has_quality_report = (project_dir / "quality_report.json").exists()
    has_stems = (project_dir / "stems").exists()
    audio_meta = get_audio_metadata(song_id)
    current = get_current_version(song_id)
    return AssetsResponse(
        song_id=song_id,
        has_music_spec=True,
        has_midi=has_midi,
        has_audio=has_audio,
        has_mix=has_mix,
        has_quality_report=has_quality_report,
        has_stems=has_stems,
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


def _load_or_create_mix(song_id: str) -> tuple[MixSpec, str | None]:
    """读取或创建当前版本 MixSpec，并自动同步 MusicSpec 轨道变化。"""
    spec = get_project(song_id)
    init_version_if_needed(song_id)
    current = get_current_version(song_id)
    version_id = current["version_id"] if current else None
    mix = get_mix_spec(song_id, version_id)
    if mix is None:
        mix = create_default_mix_spec(spec, song_id=song_id, version_id=version_id)
    else:
        mix = sync_mix_spec_with_music_spec(mix, spec)
        mix = mix.model_copy(update={"song_id": song_id, "version_id": version_id})
    save_mix_spec(song_id, mix, version_id)
    return mix, version_id


def _save_upload(file: UploadFile, suffixes: tuple[str, ...]) -> str:
    """校验上传文件并保存到临时目录，返回临时路径。"""
    name = file.filename or ""
    if not name.lower().endswith(suffixes):
        raise invalid_request(f"仅支持 {suffixes} 文件")
    data = file.file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise invalid_request("文件超过大小限制（10MB）")
    suffix = Path(name).suffix or suffixes[0]
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


@router.get("/health", response_model=HealthResponse, summary="健康检查")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# ---------- 生成 ----------

@router.post("/songs/generate", response_model=GenerateSongResponse, summary="生成音乐方案（支持风格模板）")
def generate_song(req: GenerateSongRequest, request: Request) -> GenerateSongResponse:
    request_id = getattr(request.state, "request_id", "") or get_request_id()
    try:
        spec, style_template, llm_duration_ms, provider_name, provider_model = _run_generate_llm(req)
    except LLMOutputError as exc:
        log_stage(api_logger, "generate_music_spec.failed", error_stage="llm_response_parse", error=str(exc))
        raise _map_llm_exception(exc) from None
    except (LLMConfigurationError, LLMAPIError) as exc:
        log_stage(api_logger, "generate_music_spec.failed", error_stage="llm_call", error=str(exc))
        raise _map_llm_exception(exc) from None
    except ValueError as exc:
        log_stage(api_logger, "generate_music_spec.failed", error_stage="music_spec_validation", error=str(exc))
        raise spec_validation_failed(f"生成失败：{exc}", stage="music_spec_validation") from None
    except RuntimeError as exc:
        log_stage(api_logger, "generate_music_spec.failed", error_stage="llm_call", error=str(exc))
        raise llm_error(f"LLM 服务错误：{exc}") from None
    validation = validate_music_spec_semantics(spec)
    log_stage(api_logger, "music_spec.validation.warning", count=len(validation.warnings))
    song_id = create_project(spec)
    log_stage(api_logger, "generate_music_spec.success", song_id=song_id)
    debug = GenerationDebug(
        provider=provider_name,
        model=provider_model,
        llm_duration_ms=llm_duration_ms,
        validation_warning_count=len(validation.warnings),
        request_id=request_id,
    )
    return GenerateSongResponse(
        song_id=song_id,
        music_spec=spec,
        style_template=style_template,
        validation=validation,
        request_id=request_id,
        warnings=_validation_warnings(validation),
        debug=debug,
    )


@router.post("/songs/generate-with-midi", response_model=GenerateWithMidiResponse, summary="一步生成 MusicSpec + MIDI")
def generate_song_with_midi(req: GenerateSongRequest) -> GenerateWithMidiResponse:
    try:
        spec = generate_music_spec_from_prompt(req.prompt)
        if req.style_template_id:
            template = get_style_template(req.style_template_id)
            spec = apply_style_template_to_music_spec(spec, template, req.style_strength)
    except LLMOutputError as exc:
        raise llm_error("模型输出解析失败", details={"task_name": exc.task_name}) from None
    except (LLMConfigurationError, LLMAPIError) as exc:
        raise llm_error("模型调用失败", details={"reason": str(exc)}) from None
    except ValueError as exc:
        raise spec_validation_failed(f"生成失败：{exc}") from None
    except RuntimeError as exc:
        raise llm_error(f"LLM 服务错误：{exc}") from None
    validation = validate_music_spec_semantics(spec)
    song_id = create_project(spec)
    response, _ = _generate_midi_for(song_id)
    return GenerateWithMidiResponse(
        song_id=song_id,
        music_spec=spec,
        midi=MidiInfo(midi_file=response.midi_file, download_url=response.download_url),
        validation=validation,
    )


@router.post("/songs/generate-with-audio", response_model=GenerateWithAudioResponse, summary="一步生成 MusicSpec + MIDI + WAV")
def generate_song_with_audio(req: GenerateSongRequest) -> GenerateWithAudioResponse:
    try:
        spec = generate_music_spec_from_prompt(req.prompt)
        if req.style_template_id:
            template = get_style_template(req.style_template_id)
            spec = apply_style_template_to_music_spec(spec, template, req.style_strength)
    except LLMOutputError as exc:
        raise llm_error("模型输出解析失败", details={"task_name": exc.task_name}) from None
    except (LLMConfigurationError, LLMAPIError) as exc:
        raise llm_error("模型调用失败", details={"reason": str(exc)}) from None
    except ValueError as exc:
        raise spec_validation_failed(f"生成失败：{exc}") from None
    except RuntimeError as exc:
        raise llm_error(f"LLM 服务错误：{exc}") from None
    validation = validate_music_spec_semantics(spec)
    song_id = create_project(spec)
    midi_response, _ = _generate_midi_for(song_id)
    audio_response = _render_audio_for(song_id)
    return GenerateWithAudioResponse(
        song_id=song_id,
        music_spec=spec,
        midi=MidiInfo(midi_file=midi_response.midi_file, download_url=midi_response.download_url),
        audio=audio_response,
        validation=validation,
    )


@router.post("/songs/generate-from-reference", response_model=GenerateFromReferenceResponse, summary="基于参考 MIDI 高层特征生成")
async def generate_from_reference(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    style_template_id: str | None = Form(default=None),
    style_strength: float = Form(default=0.7),
) -> GenerateFromReferenceResponse:
    temp_path = _save_upload(file, (".mid", ".midi"))
    try:
        analysis = analyze_reference_midi(Path(temp_path))
        # 先应用风格模板补齐轨道/风格，再融合参考特征（参考 tempo/长度/能量优先）
        base = generate_music_spec_from_prompt(prompt)
        style_template = None
        if style_template_id:
            style_template = get_style_template(style_template_id)
            base = apply_style_template_to_music_spec(base, style_template, style_strength)
        spec = build_music_spec_from_reference(prompt, analysis, base_spec=base)
        song_id = create_project(spec)
        return GenerateFromReferenceResponse(
            song_id=song_id,
            music_spec=spec,
            reference_analysis=analysis,
            style_template=style_template,
        )
    except LLMOutputError as exc:
        raise llm_error("模型输出解析失败", details={"task_name": exc.task_name}) from None
    except (LLMConfigurationError, LLMAPIError) as exc:
        raise llm_error("模型调用失败", details={"reason": str(exc)}) from None
    except ValueError as exc:
        raise spec_validation_failed(f"生成失败：{exc}") from None
    finally:
        os.unlink(temp_path)


@router.get("/songs/{song_id}", response_model=GetSongResponse, summary="获取音乐方案")
def get_song(song_id: str) -> GetSongResponse:
    try:
        spec = get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return GetSongResponse(song_id=song_id, music_spec=spec)


@router.get("/projects", response_model=ProjectListResponse, summary="工程列表（T33.2）")
def list_projects_route() -> ProjectListResponse:
    """列出 data/projects 下所有工程摘要（倒序）。"""
    items = []
    for song_id in list_project_ids():
        summary = get_project_summary(song_id)
        if summary is not None:
            items.append(ProjectSummaryItem(**summary))
    return ProjectListResponse(projects=items, total=len(items))


@router.delete("/songs/{song_id}", response_model=dict, summary="删除工程（T33.2）")
def delete_song_route(song_id: str) -> dict:
    """删除工程目录（含资产）。不存在返回 404。"""
    if not is_valid_song_id(song_id):
        raise invalid_request("非法 song_id：必须为 UUID 格式")
    try:
        deleted = delete_project(song_id)
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    if not deleted:
        raise project_not_found(song_id)
    return {"song_id": song_id, "deleted": True}


# ---------- MIDI ----------

@router.post("/songs/{song_id}/midi/generate", response_model=GenerateMidiResponse, summary="根据 MusicSpec 生成 MIDI")
def generate_midi(song_id: str) -> GenerateMidiResponse:
    try:
        spec = get_project(song_id)
        result = validate_music_spec_semantics(spec)
        if not result.valid:
            raise api_error(
                400,
                ApiErrorCode.MUSIC_SPEC_VALIDATION_FAILED,
                "MusicSpec 语义校验失败",
                details={
                    "errors": [i.model_dump(mode="json") for i in result.errors],
                    "warnings": [i.model_dump(mode="json") for i in result.warnings],
                },
            )
        response, _ = _generate_midi_for(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return response


@router.get("/songs/{song_id}/midi/download", summary="下载 MIDI 文件")
def download_midi(song_id: str) -> FileResponse:
    try:
        midi_path = get_midi_path(song_id)
    except FileNotFoundError as exc:
        raise asset_not_found("output.mid", message=str(exc)) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return FileResponse(midi_path, media_type="audio/midi", filename=f"{song_id}.mid")


# ---------- 音频 ----------

@router.post("/songs/{song_id}/audio/render", response_model=RenderAudioResponse, summary="渲染 WAV 音频")
def render_audio(song_id: str) -> RenderAudioResponse:
    try:
        get_project(song_id)
        return _render_audio_for(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    except Exception as exc:
        raise render_failed(f"音频渲染失败：{exc}") from None


@router.get("/songs/{song_id}/audio/stream", summary="在线播放 WAV")
def stream_audio(song_id: str) -> FileResponse:
    try:
        wav_path = get_wav_path(song_id)
    except FileNotFoundError as exc:
        raise asset_not_found("output.wav", message=str(exc)) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return FileResponse(wav_path, media_type="audio/wav")


@router.get("/songs/{song_id}/audio/download", summary="下载 WAV 文件")
def download_audio(song_id: str) -> FileResponse:
    try:
        wav_path = get_wav_path(song_id)
    except FileNotFoundError as exc:
        raise asset_not_found("output.wav", message=str(exc)) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return FileResponse(wav_path, media_type="audio/wav", filename=f"{song_id}.wav")


@router.get("/songs/{song_id}/assets", response_model=AssetsResponse, summary="项目资源状态")
def get_assets(song_id: str) -> AssetsResponse:
    try:
        project_dir = get_project_dir(song_id)
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    if not (project_dir / "music_spec.json").exists():
        raise project_not_found(song_id)
    init_version_if_needed(song_id)
    return _assets_response(song_id)


# ---------- 编辑与版本 ----------

@router.post("/songs/{song_id}/edit", response_model=EditSongResponse, summary="自然语言修改音乐")
def edit_song(song_id: str, req: EditSongRequest) -> EditSongResponse:
    try:
        spec = get_project(song_id)
        provider = get_llm_provider()
        edit_spec = provider.generate_music_edit(req.instruction, spec, project_id=song_id)
        new_spec = apply_music_edit(spec, edit_spec)
        diff = diff_music_specs(spec, new_spec)
        version = create_version(song_id, new_spec, req.instruction, edit_spec.model_dump(mode="json"))
        # MIDI 始终重新生成（作为编辑后的基础资产）
        _generate_midi_for(song_id)
        audio_rendered = False
        if req.auto_render:
            try:
                _render_audio_for(song_id)
                audio_rendered = True
            except Exception as exc:  # noqa: BLE001 - 保持旧逻辑：渲染失败不阻断编辑
                logger.warning("编辑后音频渲染失败：%s", exc)
        return EditSongResponse(
            song_id=song_id,
            version_id=version["version_id"],
            auto_render=req.auto_render,
            audio_rendered=audio_rendered,
            edit_spec=edit_spec,
            diff=diff,
            music_spec=new_spec,
            assets=_assets_response(song_id),
        )
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except LLMOutputError as exc:
        raise llm_error("模型输出解析失败", details={"task_name": exc.task_name}) from None
    except (LLMConfigurationError, LLMAPIError) as exc:
        raise llm_error("模型调用失败", details={"reason": str(exc)}) from None
    except ValueError as exc:
        raise spec_validation_failed(f"修改失败：{exc}") from None
    except RuntimeError as exc:
        raise llm_error(f"LLM 服务错误：{exc}") from None


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
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.post("/songs/{song_id}/versions/{version_id}/restore", response_model=RestoreVersionResponse, summary="恢复历史版本")
def restore_version_route(song_id: str, version_id: str) -> RestoreVersionResponse:
    try:
        get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    try:
        spec, restore_summary = restore_version(song_id, version_id)
    except FileNotFoundError as exc:
        raise version_not_found(song_id, version_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return RestoreVersionResponse(
        song_id=song_id,
        version_id=version_id,
        restored_version_id=version_id,
        current_version_id=version_id,
        music_spec=spec,
        assets=_assets_response(song_id),
        restore_summary=RestoreSummary.model_validate(restore_summary),
    )


@router.get("/songs/{song_id}/versions/{version_id}", response_model=VersionDetailResponse, summary="版本详情")
def get_version_detail(song_id: str, version_id: str) -> VersionDetailResponse:
    """返回版本 metadata、music_spec、edit_spec、diff、is_current 与 assets（兼容 vN.json 存储）。"""
    try:
        get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    try:
        detail = get_version_detail_store(song_id, version_id)
    except FileNotFoundError as exc:
        raise version_not_found(song_id, version_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    edit_spec = (
        MusicEditSpec.model_validate(detail["edit_spec"]) if detail.get("edit_spec") else None
    )
    return VersionDetailResponse(
        song_id=song_id,
        version_id=detail["version_id"],
        is_current=detail["is_current"],
        metadata=detail["metadata"],
        music_spec=detail["music_spec"],
        edit_spec=edit_spec,
        diff=detail["diff"],
        assets=_version_asset_info(song_id),
    )


def _version_asset_info(song_id: str) -> VersionAssetInfo:
    """版本详情用资产信息：旧结构下返回当前根目录资产状态（并非历史版本资产快照）。"""
    project_dir = get_project_dir(song_id)
    has_midi = (project_dir / "output.mid").exists()
    has_audio = (project_dir / "output.wav").exists()
    return VersionAssetInfo(
        has_midi=has_midi,
        has_audio=has_audio,
        midi_download_url=f"/api/v1/songs/{song_id}/midi/download" if has_midi else None,
        audio_stream_url=f"/api/v1/songs/{song_id}/audio/stream" if has_audio else None,
        audio_download_url=f"/api/v1/songs/{song_id}/audio/download" if has_audio else None,
    )


@router.get("/songs/{song_id}/versions/{version_id}/diff", response_model=VersionDiffResponse, summary="版本 diff")
def get_version_diff(song_id: str, version_id: str) -> VersionDiffResponse:
    """返回指定版本相对父版本的字段级 diff（与版本详情接口的 diff 保持一致）。"""
    try:
        get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    try:
        detail = get_version_diff_store(song_id, version_id)
    except FileNotFoundError as exc:
        raise version_not_found(song_id, version_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    return VersionDiffResponse(
        song_id=song_id,
        version_id=detail["version_id"],
        parent_version_id=detail["parent_version_id"],
        is_current=detail["is_current"],
        diff=detail["diff"],
        metadata=detail["metadata"],
        warnings=detail["warnings"],
    )


# ---------- 混音 ----------

@router.get("/songs/{song_id}/mix", response_model=MixResponse, summary="获取 MixSpec")
def get_mix(song_id: str) -> MixResponse:
    try:
        get_project(song_id)
        mix, version_id = _load_or_create_mix(song_id)
        return MixResponse(song_id=song_id, version_id=version_id, mix_spec=mix)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.patch("/songs/{song_id}/mix", response_model=MixUpdateResponse, summary="更新 MixSpec")
def update_mix(song_id: str, req: UpdateMixRequest, apply: bool = Query(default=False)) -> MixUpdateResponse:
    try:
        get_project(song_id)
        mix, version_id = _load_or_create_mix(song_id)
        if req.master_volume is not None:
            mix = mix.model_copy(update={"master_volume": req.master_volume})
        if req.notes is not None:
            mix = mix.model_copy(update={"notes": req.notes})
        for patch in req.tracks:
            mix = update_track_mix(mix, patch.track_id, patch.model_dump(exclude_none=True))
        mix = mix.model_copy(update={"song_id": song_id, "version_id": version_id})
        save_mix_spec(song_id, mix, version_id)
        assets = None
        if apply:
            _regenerate_with_mix(song_id, mix)
            assets = _assets_response(song_id)
        return MixUpdateResponse(song_id=song_id, version_id=version_id, mix_spec=mix, assets=assets)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.post("/songs/{song_id}/mix/apply", response_model=ApplyMixResponse, summary="应用混音并重新渲染")
def apply_mix(song_id: str) -> ApplyMixResponse:
    try:
        get_project(song_id)
        mix, _ = _load_or_create_mix(song_id)
        warnings = _regenerate_with_mix(song_id, mix)
        return ApplyMixResponse(song_id=song_id, mix_spec=mix, assets=_assets_response(song_id), warnings=warnings)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


# ---------- Piano Roll / 质量 / 优化 / stems ----------

@router.get("/songs/{song_id}/piano-roll", response_model=PianoRollResponse, summary="获取钢琴卷帘数据")
def get_piano_roll(
    song_id: str,
    track_id: str | None = Query(default=None),
    max_notes: int = Query(default=5000, ge=1, le=100000),
) -> PianoRollResponse:
    try:
        spec = get_project(song_id)
        midi_path = _ensure_midi_for(song_id)
        parsed = parse_midi_to_notes(midi_path)
        data = build_piano_roll_data(parsed, spec, max_notes=max_notes, track_id=track_id)
        data["song_id"] = song_id
        return data
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.post("/songs/{song_id}/quality/check", response_model=QualityReport, summary="生成编曲质量报告")
def check_quality(song_id: str) -> QualityReport:
    try:
        spec = get_project(song_id)
        midi_path = _ensure_midi_for(song_id)
        parsed = parse_midi_to_notes(midi_path)
        report = check_arrangement_quality(spec, parsed_midi=parsed)
        save_quality_report(song_id, report.model_dump(mode="json"))
        return report
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.get("/songs/{song_id}/quality/report", response_model=QualityReport, summary="获取质量报告")
def get_quality_report(song_id: str) -> QualityReport:
    try:
        get_project(song_id)
        saved = get_quality_report_store(song_id)
        if saved is not None:
            return QualityReport.model_validate(saved)
        return check_quality(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.post("/songs/{song_id}/quality/optimize", response_model=OptimizeResponse, summary="自动优化编曲")
def optimize_song(song_id: str, req: OptimizeRequest) -> OptimizeResponse:
    try:
        spec = get_project(song_id)
        midi_path = _ensure_midi_for(song_id)
        parsed = parse_midi_to_notes(midi_path)
        report = check_arrangement_quality(spec, parsed_midi=parsed)
        save_quality_report(song_id, report.model_dump(mode="json"))

        new_spec, optimize_report = optimize_arrangement(spec, report)
        version = create_version(song_id, new_spec, "自动优化编曲", None)
        _generate_midi_for(song_id)
        if req.auto_render:
            try:
                _render_audio_for(song_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("优化后音频渲染失败：%s", exc)
        save_optimize_report(song_id, optimize_report)
        return OptimizeResponse(
            song_id=song_id,
            version_id=version["version_id"],
            music_spec=new_spec,
            quality_report_before=report.model_dump(mode="json"),
            optimize_report=optimize_report,
            assets=_assets_response(song_id),
        )
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise spec_validation_failed(f"优化失败：{exc}") from None


@router.post("/songs/{song_id}/stems/export", response_model=StemExportResponse, summary="导出分轨 stems")
def export_stems(song_id: str) -> StemExportResponse:
    try:
        spec = get_project(song_id)
        mix, version_id = _load_or_create_mix(song_id)
        settings = get_settings()
        stems_dir = get_stems_dir(song_id, version_id)
        result = export_stems_impl(
            song_id,
            spec,
            mix,
            stems_dir,
            sample_rate=settings.audio_sample_rate,
            gain=settings.audio_gain,
        )
        # 根目录兼容镜像：版本目录 stems/ → 项目根 stems/
        mirror_stems_to_root(stems_dir, get_project_dir(song_id) / "stems")
        stems = [
            StemInfo(
                track_id=item["track_id"],
                midi_download_url=f"/api/v1/songs/{song_id}/stems/{item['track_id']}/midi/download",
                wav_download_url=f"/api/v1/songs/{song_id}/stems/{item['track_id']}/wav/download",
            )
            for item in result.tracks
        ]
        return StemExportResponse(
            song_id=song_id,
            stems=stems,
            zip_download_url=f"/api/v1/songs/{song_id}/stems/download",
            warnings=result.warnings,
        )
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None
    except Exception as exc:
        raise internal_error(f"stems 导出失败：{exc}") from None


@router.get("/songs/{song_id}/stems/download", summary="下载 stems.zip")
def download_stems_zip(song_id: str) -> FileResponse:
    try:
        zip_path = get_stems_zip_path(song_id)
        if not zip_path.exists():
            raise FileNotFoundError(f"项目 {song_id} 尚未导出 stems")
        return FileResponse(zip_path, media_type="application/zip", filename=f"{song_id}_stems.zip")
    except FileNotFoundError as exc:
        raise asset_not_found("stems.zip", message=str(exc)) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.get("/songs/{song_id}/stems/{track_id}/{kind}/download", summary="下载单轨 stem")
def download_stem(song_id: str, track_id: str, kind: str) -> FileResponse:
    if kind not in ("midi", "wav"):
        raise invalid_request("kind 只能是 midi 或 wav")
    try:
        stems_dir = get_stems_dir(song_id)
        if kind == "midi":
            path = stems_dir / "midi" / f"{track_id}.mid"
        else:
            path = stems_dir / "wav" / f"{track_id}.wav"
        if not path.exists():
            raise FileNotFoundError(f"轨道 {track_id} 的 {kind} stem 不存在")
        media_type = "audio/midi" if kind == "midi" else "audio/wav"
        return FileResponse(path, media_type=media_type, filename=f"{track_id}.{kind}")
    except FileNotFoundError as exc:
        raise asset_not_found(f"{track_id}.{kind}", message=str(exc)) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


# ---------- 第六阶段：风格 / 参考 / 重生成 / 工程 / 评估 ----------

@router.get("/styles", summary="获取全部风格模板")
def get_styles() -> list[StyleTemplateSpec]:
    return list_style_templates()


@router.get("/styles/{style_template_id}", response_model=StyleTemplateSpec, summary="获取指定风格模板")
def get_style(style_template_id: str) -> StyleTemplateSpec:
    try:
        return get_style_template(style_template_id)
    except ValueError as exc:
        raise api_error(404, ApiErrorCode.INVALID_REQUEST, str(exc)) from None


@router.post("/reference/analyze", response_model=ReferenceMidiAnalysis, summary="分析参考 MIDI")
async def analyze_reference(file: UploadFile = File(...)) -> ReferenceMidiAnalysis:
    temp_path = _save_upload(file, (".mid", ".midi"))
    try:
        return analyze_reference_midi(Path(temp_path))
    except Exception as exc:  # noqa: BLE001
        raise invalid_request(f"参考 MIDI 解析失败：{exc}") from None
    finally:
        os.unlink(temp_path)


@router.post("/songs/{song_id}/regenerate", response_model=RegenerationResult, summary="局部重生成")
def regenerate_song(song_id: str, req: RegenerationRequest) -> RegenerationResult:
    try:
        spec = get_project(song_id)
        parent = get_current_version(song_id)
        parent_id = parent["version_id"] if parent else ""
        new_spec, report = regenerate_music_spec(spec, req)
        version = create_version(song_id, new_spec, req.instruction or f"局部重生成（{req.scope}）", None)
        _regenerate_audio_for(song_id)
        return RegenerationResult(
            song_id=song_id,
            version_id=version["version_id"],
            parent_version_id=parent_id,
            music_spec=new_spec,
            changed_targets=report["changes"],
            warnings=report["warnings"],
            assets=_assets_response(song_id).model_dump(mode="json"),
        )
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise spec_validation_failed(f"重生成失败：{exc}") from None


@router.get("/songs/{song_id}/project/export", summary="导出工程 .aimusic.zip")
def export_project(song_id: str) -> FileResponse:
    try:
        project_dir = get_project_dir(song_id)
        if not (project_dir / "music_spec.json").exists():
            raise FileNotFoundError(f"项目不存在：{song_id}")
        output_dir = get_settings().projects_dir / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = export_project_bundle(song_id, project_dir, output_dir / f"{song_id}.aimusic.zip")
        return FileResponse(output, media_type="application/zip", filename=f"{song_id}.aimusic.zip")
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.post("/projects/import", response_model=ProjectImportResponse, summary="导入工程 .aimusic.zip")
async def import_project(file: UploadFile = File(...)) -> ProjectImportResponse:
    if not (file.filename or "").lower().endswith(".zip"):
        raise invalid_bundle("仅支持 .aimusic.zip 文件")
    temp_path = _save_upload(file, (".zip",))
    try:
        result = import_project_bundle(Path(temp_path), get_settings().projects_dir)
        return ProjectImportResponse(
            song_id=result["song_id"],
            imported=result["imported"],
            summary=result["summary"],
            source_song_id=result.get("source_song_id"),
            current_version_id=result.get("current_version_id"),
            version_count=result.get("version_count", 0),
            assets=result.get("assets", {}),
            warnings=result.get("warnings", []),
        )
    except ValueError as exc:
        raise invalid_bundle(str(exc)) from None
    finally:
        os.unlink(temp_path)


@router.get("/evaluation/cases", response_model=list[EvalCase], summary="获取内置评估用例")
def eval_cases():
    return get_eval_cases()


@router.post("/evaluation/run", response_model=EvalReport, summary="运行批量评估")
def eval_run(req: EvalRunRequest) -> EvalReport:
    cases = get_eval_cases()
    if req.case_ids:
        cases = [c for c in cases if c.id in req.case_ids]
    if not cases:
        raise invalid_request("未选择有效的评估用例")
    return run_generation_eval(cases, render_audio=req.render_audio)
