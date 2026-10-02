from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    season_id: str = "2025-26"
    database_url: str = "postgresql+psycopg://nba:nba_local_dev@localhost:55432/nba"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3.5:2b"
    ollama_timeout_seconds: float = 45.0
    allowed_origins: str = "http://localhost:4300"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
