"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings with local-safe defaults."""

    app_name: str = "Memoria AI API"
    database_url: str = "sqlite:///./storage/memoria.db"
    data_path: Path = Path("data")
    models_path: Path = Path("models")
    storage_path: Path = Path("storage")
    chroma_path: Path = Path("storage/chroma")
    log_level: str = "INFO"

    # LLM Provider Configuration
    llm_provider: str = "local"
    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_model: str = "local-model"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
