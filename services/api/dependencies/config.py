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


@lru_cache
def get_settings() -> Settings:
    return Settings()
