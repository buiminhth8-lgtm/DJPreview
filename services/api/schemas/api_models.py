"""API 请求 / 响应模型。"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from packages.music_core.evaluation.eval_models import EvalReport
from packages.music_core.mix.mix_models import MixSpec
from packages.music_core.reference.reference_models import ReferenceMidiAnalysis
from packages.music_core.regeneration.regeneration_models import RegenerationRequest, RegenerationResult
from packages.music_core.styles.style_models import StyleTemplateSpec
from packages.music_core.validation.spec_validator import ValidationResult
from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec


class ErrorResponse(BaseModel):
    """统一错误响应结构。"""

    error_code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: dict[str, Any] = Field(default_factory=dict)


class GenerateSongRequest(BaseModel):
    """POST /api/v1/songs/generate 请求体（兼容无风格模板的旧请求）。"""

    prompt: str = Field(min_length=1, description="自然语言音乐描述")
    style_template_id: str | None = Field(default=None, description="可选风格模板 id")
    style_strength: float = Field(default=0.7, ge=0.0, le=1.0, description="风格影响强度")

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("prompt 不能为空")
        return stripped


class GenerateSongResponse(BaseModel):
    song_id: str
    music_spec: MusicSpec
    style_template: StyleTemplateSpec | None = None
    validation: ValidationResult | None = None


class GetSongResponse(BaseModel):
    song_id: str
    music_spec: MusicSpec


class HealthResponse(BaseModel):
    status: str


class MidiSummary(BaseModel):
    tracks: int
    bars: int
    bpm: int


class GenerateMidiResponse(BaseModel):
    song_id: str
    midi_file: str
    download_url: str
    summary: MidiSummary


class MidiInfo(BaseModel):
    midi_file: str
    download_url: str


class GenerateWithMidiResponse(BaseModel):
    song_id: str
    music_spec: MusicSpec
    midi: MidiInfo
    validation: ValidationResult | None = None


class AudioMetadata(BaseModel):
    audio_file: str = "output.wav"
    renderer: str
    sample_rate: int
    duration_seconds: float | None = None
    file_size: int
    generated_at: str | None = None
    generator_version: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RenderAudioResponse(BaseModel):
    song_id: str
    audio_file: str
    stream_url: str
    download_url: str
    metadata: AudioMetadata


class PianoRollResponse(BaseModel):
    """钢琴卷帘数据响应。"""

    song_id: str
    ticks_per_beat: int
    bpm: int | None = None
    beats_per_bar: int = 4
    total_bars: float = 0.0
    total_notes: int = 0
    truncated: bool = False
    sections: list[dict[str, Any]] = Field(default_factory=list)
    tracks: list[dict[str, Any]] = Field(default_factory=list)


class MidiAssetInfo(BaseModel):
    download_url: str


class AudioAssetInfo(BaseModel):
    stream_url: str
    download_url: str
    metadata: AudioMetadata | None = None


class VersionInfo(BaseModel):
    version_id: str
    version_number: int
    created_at: str
    instruction: str | None = None
    parent_version_id: str | None = None


class VersionDetail(VersionInfo):
    music_spec: MusicSpec
    edit_spec: MusicEditSpec | None = None


class AssetsResponse(BaseModel):
    song_id: str
    has_music_spec: bool
    has_midi: bool
    has_audio: bool
    has_mix: bool = False
    has_quality_report: bool = False
    has_stems: bool = False
    midi: MidiAssetInfo | None = None
    audio: AudioAssetInfo | None = None
    current_version: VersionInfo | None = None


class VersionAssetInfo(BaseModel):
    """版本详情中的资产链接与存在状态。

    注意：旧版本结构（根目录 output.mid / output.wav）下返回的是当前根目录资产，
    并非历史版本的资产快照。
    """

    has_midi: bool = False
    has_audio: bool = False
    midi_download_url: str | None = None
    audio_stream_url: str | None = None
    audio_download_url: str | None = None


class VersionDetailResponse(BaseModel):
    """版本详情：metadata + music_spec + edit_spec + diff(相对父版本) + is_current + assets。"""

    song_id: str
    version_id: str
    is_current: bool = False
    metadata: dict
    music_spec: MusicSpec
    edit_spec: MusicEditSpec | None = None
    diff: list[dict] | None = None
    assets: VersionAssetInfo


class VersionDiffResponse(BaseModel):
    """指定版本相对父版本的字段级 diff。"""

    song_id: str
    version_id: str
    parent_version_id: str | None = None
    is_current: bool = False
    diff: list[dict] | None = None
    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class GenerateWithAudioResponse(BaseModel):
    song_id: str
    music_spec: MusicSpec
    midi: MidiInfo
    audio: RenderAudioResponse
    validation: ValidationResult | None = None


class EditSongRequest(BaseModel):
    instruction: str = Field(min_length=1, description="自然语言修改指令")
    auto_render: bool = Field(
        default=True,
        description="Whether to render audio automatically after applying the edit.",
    )

    @field_validator("instruction")
    @classmethod
    def _instruction_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("instruction 不能为空")
        return stripped


class EditSongResponse(BaseModel):
    song_id: str
    version_id: str
    auto_render: bool = True
    audio_rendered: bool = False
    edit_spec: MusicEditSpec
    diff: list[dict]
    music_spec: MusicSpec
    assets: AssetsResponse


class VersionsResponse(BaseModel):
    song_id: str
    current_version_id: str
    versions: list[VersionInfo]


class RestoreSummary(BaseModel):
    """恢复版本时的资产操作摘要。"""

    restored: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)


class RestoreVersionResponse(BaseModel):
    """恢复版本响应：兼容旧字段 version_id / music_spec / assets。"""

    song_id: str
    version_id: str
    restored_version_id: str
    current_version_id: str
    music_spec: MusicSpec
    assets: AssetsResponse
    restore_summary: RestoreSummary | None = None


# ---------- T29：SoundFont / 音源管理 ----------

class SoundFontInfo(BaseModel):
    """单个 SoundFont 音源信息。"""

    id: str
    name: str
    path: str
    format: str
    size_bytes: int
    is_default: bool = False
    tags: list[str] = Field(default_factory=list)


class SoundfontListResponse(BaseModel):
    """音源列表响应。"""

    soundfonts: list[SoundFontInfo] = Field(default_factory=list)
    default_soundfont_id: str | None = None


class ProjectSoundfontRequest(BaseModel):
    """项目级音源选择请求。"""

    soundfont_id: str = Field(min_length=1)
    renderer: str | None = None


class ProjectSoundfontResponse(BaseModel):
    """项目级音源响应（含本地可用性提示）。"""

    song_id: str
    soundfont: dict | None = None
    available: bool = False
    warning: str | None = None


# ---------- T30：异步渲染任务 ----------

class RenderAudioTaskRequest(BaseModel):
    """异步音频渲染任务可选参数。"""

    soundfont_id: str | None = None


# ---------- 第五阶段：混音 / 质量 / stems ----------

class TrackMixPatch(BaseModel):
    track_id: str
    role: str | None = None
    volume: float | None = Field(default=None, ge=0.0, le=1.5)
    pan: float | None = Field(default=None, ge=-1.0, le=1.0)
    mute: bool | None = None
    solo: bool | None = None
    enabled: bool | None = None
    velocity_scale: float | None = Field(default=None, ge=0.1, le=2.0)
    program: int | None = None
    instrument: str | None = None


class UpdateMixRequest(BaseModel):
    master_volume: float | None = Field(default=None, ge=0.0, le=1.5)
    tracks: list[TrackMixPatch] = Field(default_factory=list)
    notes: str | None = None


class MixResponse(BaseModel):
    song_id: str
    version_id: str | None = None
    mix_spec: MixSpec


class MixUpdateResponse(BaseModel):
    song_id: str
    version_id: str | None = None
    mix_spec: MixSpec
    assets: AssetsResponse | None = None


class ApplyMixResponse(BaseModel):
    song_id: str
    mix_spec: MixSpec
    assets: AssetsResponse
    warnings: list[str]


class OptimizeRequest(BaseModel):
    auto_render: bool = True


class OptimizeResponse(BaseModel):
    song_id: str
    version_id: str
    music_spec: MusicSpec
    quality_report_before: dict
    optimize_report: dict
    assets: AssetsResponse


class StemInfo(BaseModel):
    track_id: str
    midi_download_url: str
    wav_download_url: str


class StemExportResponse(BaseModel):
    song_id: str
    stems: list[StemInfo]
    zip_download_url: str
    warnings: list[str]


# ---------- 第六阶段：风格 / 参考 / 重生成 / 工程 / 评估 ----------

class GenerateFromReferenceResponse(BaseModel):
    song_id: str
    music_spec: MusicSpec
    reference_analysis: ReferenceMidiAnalysis
    style_template: StyleTemplateSpec | None = None


class EvalRunRequest(BaseModel):
    case_ids: list[str] = Field(default_factory=list)
    render_audio: bool = False


class ProjectImportResponse(BaseModel):
    song_id: str
    imported: bool
    summary: dict
    source_song_id: str | None = None
    current_version_id: str | None = None
    version_count: int = 0
    assets: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# 复用外部模型
RegenerationRequest = RegenerationRequest
RegenerationResult = RegenerationResult
ReferenceMidiAnalysis = ReferenceMidiAnalysis
EvalReport = EvalReport
StyleTemplateSpec = StyleTemplateSpec
