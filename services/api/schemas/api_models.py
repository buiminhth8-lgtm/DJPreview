"""API 请求 / 响应模型。"""

from pydantic import BaseModel, Field, field_validator

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
