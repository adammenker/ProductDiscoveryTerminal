from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./product_discovery.db"
    backend_cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )
    enable_scheduler: bool = False
    default_pipeline_limit: int = 100
    etsy_api_enabled: bool = False
    etsy_api_keystring: str | None = None
    etsy_shared_secret: str | None = None
    etsy_api_base_url: str = "https://openapi.etsy.com/v3/application"
    etsy_request_timeout_seconds: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
