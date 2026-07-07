from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class EtsyApiPlugin:
    name = "etsy_api"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Fetches active Etsy marketplace listings via Etsy Open API v3.",
        "requires_auth": True,
        "supports": ["marketplace_listing", "search_result"],
        "config_schema": {
            "ETSY_API_ENABLED": {"type": "boolean", "required": True},
            "ETSY_API_KEYSTRING": {"type": "string", "required": True},
            "ETSY_SHARED_SECRET": {"type": "string", "required": False},
        },
    }

    @property
    def enabled(self) -> bool:
        settings = get_settings()
        return settings.etsy_api_enabled and bool(settings.etsy_api_keystring)

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        settings = get_settings()
        if not self.enabled:
            raise RuntimeError(
                "etsy_api is disabled. Set ETSY_API_ENABLED=true and ETSY_API_KEYSTRING "
                "after Etsy app approval."
            )
        if not query.query:
            raise RuntimeError("etsy_api requires query.query keywords, for example 'ice roller'.")

        response = self._request_active_listings(settings, query)
        listings = response.get("results") or []
        observed_at = datetime.now(UTC)

        observations: list[RawObservationDTO] = []
        for listing in listings:
            observations.append(self._listing_to_observation(listing, observed_at, query))
        return observations

    def _request_active_listings(self, settings: Any, query: IngestionQuery) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keywords": query.query,
            "limit": max(1, min(query.limit, 100)),
        }
        if query.category:
            params["category"] = query.category

        with httpx.Client(timeout=settings.etsy_request_timeout_seconds) as client:
            response = client.get(
                f"{settings.etsy_api_base_url.rstrip('/')}/listings/active",
                params=params,
                headers={
                    "x-api-key": settings.etsy_api_keystring,
                    "User-Agent": "product-discovery-terminal/0.1.0",
                },
            )
            response.raise_for_status()
            return response.json()

    def _listing_to_observation(
        self,
        listing: dict[str, Any],
        observed_at: datetime,
        query: IngestionQuery,
    ) -> RawObservationDTO:
        listing_id = listing.get("listing_id")
        title = listing.get("title")
        price = _extract_price(listing)
        tags = listing.get("tags") or []
        taxonomy_path = listing.get("taxonomy_path") or []
        category = query.category or (taxonomy_path[0] if taxonomy_path else None)

        return RawObservationDTO(
            source="etsy",
            source_plugin=self.name,
            observed_at=observed_at,
            entity_type="marketplace_listing",
            external_id=str(listing_id) if listing_id is not None else None,
            title=title,
            url=listing.get("url"),
            raw_text=listing.get("description"),
            metrics={
                "price": price,
                "quantity": listing.get("quantity"),
                "num_favorers": listing.get("num_favorers"),
                "views": listing.get("views"),
            },
            metadata={
                "product_name": _infer_product_name(title, query.query),
                "category": category,
                "shop_id": listing.get("shop_id"),
                "state": listing.get("state"),
                "tags": tags,
                "taxonomy_path": taxonomy_path,
                "raw_listing": listing,
            },
            media_urls=_extract_media_urls(listing),
        )


def _extract_price(listing: dict[str, Any]) -> float | None:
    price = listing.get("price")
    if price is None:
        return None
    if isinstance(price, int | float):
        return float(price)
    if isinstance(price, dict):
        amount = price.get("amount")
        divisor = price.get("divisor") or 100
        if amount is not None:
            return round(float(amount) / float(divisor), 2)
    try:
        return float(price)
    except (TypeError, ValueError):
        return None


def _extract_media_urls(listing: dict[str, Any]) -> list[str]:
    images = listing.get("images") or []
    urls = []
    for image in images:
        if not isinstance(image, dict):
            continue
        url = image.get("url_fullxfull") or image.get("url_570xN") or image.get("url_170x135")
        if url:
            urls.append(str(url))
    return urls


def _infer_product_name(title: str | None, query: str | None) -> str | None:
    if query:
        return query.strip().lower()
    if title:
        return title.strip().lower()
    return None

