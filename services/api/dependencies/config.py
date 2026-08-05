"""应用配置（基于 pydantic-settings，自动读取 .env）。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Music MVP"
    llm_provider: str = "mock"
    deepseek_api_key: str | None = None
    deepseek_base_url: str | None = None
    deepseek_model: str | None = None
    projects_dir: Path = Path("data/projects")

    # 音频渲染（第三阶段）
    audio_renderer: str = "auto"
    fluidsynth_bin: str = "fluidsynth"
    soundfont_path: str | None = None
    soundfont_dir: str | None = None
    default_soundfont_id: str | None = None
    audio_sample_rate: int = 44100
    audio_gain: float = 0.6


@lru_cache
def get_settings() -> Settings:
    return Settings()
