"""API 请求 / 响应模型。"""

from pydantic import BaseModel, Field, field_validator

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
