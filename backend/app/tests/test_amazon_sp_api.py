from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.config import Settings
from app.integrations.amazon_sp_api import AmazonSpApiClient
from app.plugins.ingestion.amazon_sp_api.plugin import AmazonSpApiPlugin
from app.schemas.plugin import IngestionQuery


def test_amazon_sp_api_client_exchanges_refresh_token_and_calls_catalog() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path == "/auth/o2/token":
            assert b"grant_type=refresh_token" in request.content
            return httpx.Response(
                200,
                json={"access_token": "Atza|test-access-token", "token_type": "bearer"},
            )
        assert request.headers["x-amz-access-token"] == "Atza|test-access-token"
        assert request.headers["x-amz-date"]
        if request.url.path == "/sellers/v1/marketplaceParticipations":
            return httpx.Response(200, json={"payload": []})
        if request.url.path == "/products/pricing/v0/competitivePrice":
            return httpx.Response(200, json={"payload": [{"ASIN": "B000TEST01"}]})
        return httpx.Response(
            200,
            json={"items": [{"asin": "B000TEST01", "summaries": [{"itemName": "Ice Roller"}]}]},
        )

    settings = Settings(
        amazon_sp_api_enabled=True,
        amazon_lwa_client_id="client-id",
        amazon_lwa_client_secret="client-secret",
        amazon_refresh_token="refresh-token",
        amazon_marketplace_id="ATVPDKIKX0DER",
    )
    client = AmazonSpApiClient(
        settings,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    payload = client.get_catalog_items("ice roller")

    assert payload["items"][0]["asin"] == "B000TEST01"
    marketplace_payload = client.get_marketplace_participations()
    assert marketplace_payload == {"payload": []}
    pricing_payload = client.get_competitive_pricing_for_asin("B000TEST01")
    assert pricing_payload == {"payload": [{"ASIN": "B000TEST01"}]}
    assert seen == [
        "https://api.amazon.com/auth/o2/token",
        "https://sandbox.sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items?marketplaceIds=ATVPDKIKX0DER&keywords=ice+roller&pageSize=10&includedData=summaries%2Cimages%2CsalesRanks",
        "https://sandbox.sellingpartnerapi-na.amazon.com/sellers/v1/marketplaceParticipations",
        "https://sandbox.sellingpartnerapi-na.amazon.com/products/pricing/v0/competitivePrice?MarketplaceId=ATVPDKIKX0DER&Asins=B000TEST01&ItemType=Asin",
    ]


def test_amazon_sp_api_settings_support_production_aliases(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AMAZON_SP_API_ENV", "production")
    monkeypatch.setenv("AMAZON_LWA_REFRESH_TOKEN", "refresh-token")

    settings = Settings(_env_file=None)

    assert settings.amazon_sp_api_environment == "production"
    assert settings.amazon_refresh_token == "refresh-token"


def test_amazon_sp_api_client_retries_throttled_requests() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == "/auth/o2/token":
            return httpx.Response(200, json={"access_token": "Atza|test-access-token"})
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"payload": [{"ASIN": "B000TEST01"}]})

    settings = Settings(
        _env_file=None,
        amazon_sp_api_enabled=True,
        amazon_lwa_client_id="client-id",
        amazon_lwa_client_secret="client-secret",
        amazon_refresh_token="refresh-token",
        amazon_request_max_attempts=2,
        amazon_request_backoff_seconds=0,
    )
    client = AmazonSpApiClient(
        settings,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    payload = client.get_competitive_pricing_for_asin("B000TEST01")

    assert attempts == 2
    assert payload["payload"][0]["ASIN"] == "B000TEST01"


def test_amazon_sp_api_client_retries_transport_failures() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == "/auth/o2/token":
            return httpx.Response(200, json={"access_token": "Atza|test-access-token"})
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary network failure", request=request)
        return httpx.Response(200, json={"payload": []})

    settings = Settings(
        _env_file=None,
        amazon_sp_api_enabled=True,
        amazon_lwa_client_id="client-id",
        amazon_lwa_client_secret="client-secret",
        amazon_refresh_token="refresh-token",
        amazon_request_max_attempts=2,
        amazon_request_backoff_seconds=0,
        amazon_pricing_request_interval_seconds=0,
    )
    client = AmazonSpApiClient(
        settings,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.get_competitive_pricing_for_asin("B000TEST01") == {"payload": []}
    assert attempts == 2


def test_amazon_sp_api_plugin_maps_catalog_items() -> None:
    plugin = AmazonSpApiPlugin()
    observed_at = datetime.now(UTC)
    observation = plugin._item_to_observation(
        item={
            "asin": "B000TEST01",
            "summaries": [
                {
                    "itemName": "Reusable Facial Ice Roller",
                    "brand": "Glow Tools",
                    "browseClassification": {"displayName": "Beauty"},
                }
            ],
            "images": [{"images": [{"link": "https://example.com/image.jpg"}]}],
            "salesRanks": [{"ranks": [{"rank": 1234}]}],
        },
        observed_at=observed_at,
        query=IngestionQuery(query="ice roller"),
        index=0,
    )

    assert observation.external_id == "B000TEST01"
    assert observation.title == "Reusable Facial Ice Roller"
    assert observation.url == "https://www.amazon.com/dp/B000TEST01"
    assert observation.metrics["bestseller_rank"] == 1234
    assert observation.metadata["asin"] == "B000TEST01"
    assert observation.metadata["brand"] == "Glow Tools"
