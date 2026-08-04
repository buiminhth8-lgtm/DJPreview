"""API 请求 / 响应模型。"""

from pydantic import BaseModel, Field, field_validator

from packages.music_core.mix.mix_models import MixSpec
from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec


class GenerateSongRequest(BaseModel):
    """POST /api/v1/songs/generate 请求体。"""

    prompt: str = Field(min_length=1, description="自然语言音乐描述")

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
    midi: MidiAssetInfo | None = None
    audio: AudioAssetInfo | None = None
    current_version: VersionInfo | None = None


class GenerateWithAudioResponse(BaseModel):
    song_id: str
    music_spec: MusicSpec
    midi: MidiInfo
    audio: RenderAudioResponse


class EditSongRequest(BaseModel):
    instruction: str = Field(min_length=1, description="自然语言修改指令")

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
    edit_spec: MusicEditSpec
    diff: list[dict]
    music_spec: MusicSpec
    assets: AssetsResponse


class VersionsResponse(BaseModel):
    song_id: str
    current_version_id: str
    versions: list[VersionInfo]


class RestoreVersionResponse(BaseModel):
    song_id: str
    version_id: str
    music_spec: MusicSpec
    assets: AssetsResponse


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
