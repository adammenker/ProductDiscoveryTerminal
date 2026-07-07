from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AlibabaOpenApiPlugin:
    name = "alibaba_open_api"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Fetches supplier/product evidence from Alibaba.com Open API.",
        "requires_auth": True,
        "supports": ["supplier", "product", "search_result"],
        "config_schema": {
            "ALIBABA_API_ENABLED": {"type": "boolean", "required": True},
            "ALIBABA_APP_KEY": {"type": "string", "required": True},
            "ALIBABA_APP_SECRET": {"type": "string", "required": True},
            "ALIBABA_ACCESS_TOKEN": {"type": "string", "required": True},
            "ALIBABA_PRODUCT_SEARCH_URL": {"type": "string", "required": True},
        },
    }

    @property
    def enabled(self) -> bool:
        settings = get_settings()
        return (
            settings.alibaba_api_enabled
            and bool(settings.alibaba_app_key)
            and bool(settings.alibaba_app_secret)
            and bool(settings.alibaba_access_token)
            and bool(settings.alibaba_product_search_url)
        )

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        settings = get_settings()
        if not self.enabled:
            raise RuntimeError(
                "alibaba_open_api is disabled or incomplete. Set ALIBABA_API_ENABLED=true "
                "and fill Alibaba app credentials, access token, and product search URL after approval."
            )
        if not query.query:
            raise RuntimeError("alibaba_open_api requires query.query keywords, for example 'ice roller'.")

        payload = self._request_supplier_products(settings, query)
        rows = _extract_rows(payload)
        observed_at = datetime.now(UTC)
        return [
            self._row_to_observation(row=row, observed_at=observed_at, query=query, index=index)
            for index, row in enumerate(rows)
        ]

    def _request_supplier_products(self, settings: Any, query: IngestionQuery) -> dict[str, Any]:
        params = {
            "q": query.query,
            "keywords": query.query,
            "limit": max(1, min(query.limit, 100)),
        }
        if query.category:
            params["category"] = query.category

        with httpx.Client(timeout=settings.alibaba_request_timeout_seconds) as client:
            response = client.get(
                settings.alibaba_product_search_url,
                params=params,
                headers={
                    "Authorization": f"Bearer {settings.alibaba_access_token}",
                    "X-App-Key": settings.alibaba_app_key or "",
                    "User-Agent": "product-discovery-terminal/0.1.0",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()

    def _row_to_observation(
        self,
        row: dict[str, Any],
        observed_at: datetime,
        query: IngestionQuery,
        index: int,
    ) -> RawObservationDTO:
        title = _first(row, "title", "productTitle", "product_name", "subject", "name")
        product_name = _clean_product_name(title, query.query)
        supplier_name = _first(row, "supplierName", "supplier_name", "companyName", "company_name")
        unit_cost = _first_number(row, "unitCost", "unit_cost", "price", "fobPrice", "min_price")
        moq = _first_int(row, "moq", "minOrderQuantity", "min_order_quantity")

        return RawObservationDTO(
            source="alibaba",
            source_plugin=self.name,
            observed_at=observed_at,
            entity_type="supplier",
            external_id=str(_first(row, "id", "productId", "offerId", "product_id") or index),
            title=title,
            url=_first(row, "url", "productUrl", "detailUrl", "detail_url"),
            raw_text=_first(row, "description", "summary", "shortDescription"),
            metrics={
                "unit_cost": unit_cost,
                "moq": moq,
                "lead_time_days": _first_int(row, "leadTimeDays", "lead_time_days"),
                "shipping_estimate": _first_number(row, "shippingEstimate", "shipping_estimate"),
                "supplier_rating": _first_number(row, "supplierRating", "rating"),
            },
            metadata={
                "product_name": product_name,
                "category": query.category or _first(row, "category", "categoryName"),
                "supplier_name": supplier_name,
                "country": _first(row, "country", "supplierCountry", "countryName"),
                "raw_supplier_product": row,
            },
            media_urls=_extract_media_urls(row),
        )


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        payload.get("results"),
        payload.get("result"),
        payload.get("products"),
        payload.get("data"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            nested = candidate.get("products") or candidate.get("items") or candidate.get("results")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _first(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return str(value)
    return None


def _first_number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, dict):
            value = value.get("amount") or value.get("value") or value.get("min")
        try:
            return float(str(value).replace("$", "").replace(",", "").strip())
        except (TypeError, ValueError):
            continue
    return None


def _first_int(row: dict[str, Any], *keys: str) -> int | None:
    value = _first_number(row, *keys)
    return int(value) if value is not None else None


def _extract_media_urls(row: dict[str, Any]) -> list[str]:
    raw_images = row.get("images") or row.get("imageUrls") or row.get("image_urls") or []
    if isinstance(raw_images, str):
        return [raw_images]
    if not isinstance(raw_images, list):
        return []

    urls = []
    for image in raw_images:
        if isinstance(image, str):
            urls.append(image)
        elif isinstance(image, dict):
            url = image.get("url") or image.get("imageUrl") or image.get("src")
            if url:
                urls.append(str(url))
    return urls


def _clean_product_name(title: str | None, query: str | None) -> str | None:
    if query:
        return query.strip().lower()
    if title:
        return title.strip().lower()
    return None

