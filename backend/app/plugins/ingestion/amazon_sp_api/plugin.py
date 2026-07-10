from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.integrations.amazon_sp_api import AmazonSpApiClient
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AmazonSpApiPlugin:
    name = "amazon_sp_api"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Fetches Amazon Catalog Items evidence through Selling Partner API.",
        "auto_run": False,
        "requires_auth": True,
        "supports": ["marketplace_listing", "product", "catalog_items"],
        "config_schema": {
            "AMAZON_SP_API_ENABLED": {"type": "boolean", "required": True},
            "AMAZON_SP_API_ENV": {"type": "string", "required": True},
            "AMAZON_LWA_CLIENT_ID": {"type": "string", "required": True},
            "AMAZON_LWA_CLIENT_SECRET": {"type": "string", "required": True},
            "AMAZON_LWA_REFRESH_TOKEN": {"type": "string", "required": True},
            "AMAZON_MARKETPLACE_ID": {"type": "string", "required": True},
        },
    }

    @property
    def enabled(self) -> bool:
        settings = get_settings()
        return (
            settings.amazon_sp_api_enabled
            and bool(settings.amazon_lwa_client_id)
            and bool(settings.amazon_lwa_client_secret)
            and bool(settings.amazon_refresh_token)
            and bool(settings.amazon_marketplace_id)
        )

    def configuration_status(self) -> dict[str, Any]:
        settings = get_settings()
        missing = _missing_credentials(settings)
        return {
            "configured": not missing,
            "environment": settings.amazon_sp_api_environment,
            "missing_credentials": missing,
        }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        settings = get_settings()
        if not self.enabled:
            raise RuntimeError(
                "amazon_sp_api is disabled or incomplete. Set AMAZON_SP_API_ENABLED=true "
                "and fill Amazon LWA credentials plus refresh token."
            )
        if not query.query:
            raise RuntimeError("amazon_sp_api requires query.query keywords, for example 'ice roller'.")

        with AmazonSpApiClient(settings) as client:
            payload = client.get_catalog_items(query.query, page_size=query.limit)
        items = payload.get("items") or []
        observed_at = datetime.now(UTC)
        return [
            self._item_to_observation(item=item, observed_at=observed_at, query=query, index=index)
            for index, item in enumerate(items)
            if isinstance(item, dict)
        ]

    def _item_to_observation(
        self,
        item: dict[str, Any],
        observed_at: datetime,
        query: IngestionQuery,
        index: int,
    ) -> RawObservationDTO:
        asin = item.get("asin")
        summary = _first_dict(item.get("summaries"))
        title = _first_string(summary, "itemName", "item_name", "title")
        brand = _first_string(summary, "brand", "manufacturer")
        category = query.category or _browse_category(summary)
        image_urls = _image_urls(item)
        sales_rank = _best_sales_rank(item)

        return RawObservationDTO(
            source="amazon_sp_api",
            source_plugin=self.name,
            observed_at=observed_at,
            entity_type="marketplace_listing",
            external_id=str(asin) if asin else f"amazon-sp-api-{index}",
            title=title,
            url=f"https://www.amazon.com/dp/{asin}" if asin else None,
            raw_text=None,
            metrics={
                "bestseller_rank": sales_rank,
            },
            metadata={
                "product_name": _infer_product_name(title, query.query),
                "category": category,
                "asin": asin,
                "brand": brand,
                "marketplace_id": get_settings().amazon_marketplace_id,
                "raw_catalog_item": item,
            },
            media_urls=image_urls,
        )


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    if isinstance(value, dict):
        return value
    return {}


def _first_string(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return None


def _browse_category(summary: dict[str, Any]) -> str | None:
    browse = summary.get("browseClassification")
    if isinstance(browse, dict):
        return _first_string(browse, "displayName", "classificationId")
    return None


def _image_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for image_group in item.get("images") or []:
        if not isinstance(image_group, dict):
            continue
        for image in image_group.get("images") or []:
            if isinstance(image, dict) and image.get("link"):
                urls.append(str(image["link"]))
    return urls


def _best_sales_rank(item: dict[str, Any]) -> int | None:
    ranks: list[int] = []
    for rank_group in item.get("salesRanks") or []:
        if not isinstance(rank_group, dict):
            continue
        for rank in rank_group.get("ranks") or []:
            if not isinstance(rank, dict) or rank.get("rank") is None:
                continue
            try:
                ranks.append(int(rank["rank"]))
            except (TypeError, ValueError):
                continue
    return min(ranks) if ranks else None


def _infer_product_name(title: str | None, query: str | None) -> str | None:
    if query:
        return query.strip().lower()
    if title:
        return title.strip().lower()
    return None


def _missing_credentials(settings: Any) -> list[str]:
    required = {
        "AMAZON_LWA_CLIENT_ID": settings.amazon_lwa_client_id,
        "AMAZON_LWA_CLIENT_SECRET": settings.amazon_lwa_client_secret,
        "AMAZON_LWA_REFRESH_TOKEN": settings.amazon_refresh_token,
        "AMAZON_MARKETPLACE_ID": settings.amazon_marketplace_id,
    }
    return [name for name, value in required.items() if not value]
