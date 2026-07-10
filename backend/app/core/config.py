from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
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
    allow_public_unauthenticated: bool = False
    public_app_url: str | None = None
    compliance_docs_path: str = "../compliance"
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
    amazon_sp_api_enabled: bool = False
    amazon_sp_api_environment: str = Field(
        default="sandbox",
        validation_alias=AliasChoices("AMAZON_SP_API_ENV", "AMAZON_SP_API_ENVIRONMENT"),
    )
    amazon_sp_api_endpoint: str | None = None
    amazon_sp_api_endpoint_sandbox: str = "https://sandbox.sellingpartnerapi-na.amazon.com"
    amazon_sp_api_endpoint_production: str = "https://sellingpartnerapi-na.amazon.com"
    amazon_marketplace_id: str = "ATVPDKIKX0DER"
    amazon_lwa_client_id: str | None = None
    amazon_lwa_client_secret: str | None = None
    amazon_refresh_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AMAZON_LWA_REFRESH_TOKEN", "AMAZON_REFRESH_TOKEN"),
    )
    amazon_lwa_token_url: str = "https://api.amazon.com/auth/o2/token"
    amazon_user_agent: str = "ProductDiscoveryTerminal/0.1.0 (Language=Python)"
    amazon_request_timeout_seconds: float = 20.0
    amazon_request_max_attempts: int = 3
    amazon_request_backoff_seconds: float = 0.5
    amazon_catalog_search_limit: int = 10
    amazon_fees_default_modeled_price: float = 24.99
    amazon_refresh_catalog_limit: int = 10
    amazon_refresh_pricing_limit: int = 10
    amazon_refresh_fee_limit: int = 5
    amazon_fees_cache_ttl_hours: float = 24.0
    amazon_fees_request_interval_seconds: float = 1.1
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
