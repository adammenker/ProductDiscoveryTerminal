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
    alibaba_api_enabled: bool = False
    alibaba_app_key: str | None = None
    alibaba_app_secret: str | None = None
    alibaba_access_token: str | None = None
    alibaba_product_search_url: str | None = None
    alibaba_request_timeout_seconds: float = 20.0
    cost_ceiling_marketplace_fee_rate: float = 0.15
    cost_ceiling_fulfillment_fee_rate: float = 0.13
    cost_ceiling_fulfillment_fee_floor: float = 3.25
    cost_ceiling_supplier_freight_fallback_per_unit: float = 1.0
    cost_ceiling_packaging_cost_per_unit: float = 0.65
    cost_ceiling_inbound_cost_per_unit: float = 0.75
    cost_ceiling_storage_cost_per_unit: float = 0.35
    cost_ceiling_return_allowance_rate: float = 0.04
    cost_ceiling_ad_allowance_rate: float = 0.12
    cost_ceiling_target_profit_rate: float = 0.20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
