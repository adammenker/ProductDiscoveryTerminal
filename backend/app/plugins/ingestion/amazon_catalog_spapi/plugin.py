from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.integrations.amazon_sp_api import AmazonSpApiClient
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AmazonCatalogSpApiPlugin:
    name = "amazon_catalog_spapi"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Finds comparable Amazon catalog items through Selling Partner API.",
        "requires_auth": True,
        "auto_run": False,
        "supports": ["marketplace_listing", "catalog_items", "comparable_asins"],
    }

    def __init__(
        self,
        settings: Any | None = None,
        client_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.client_factory = client_factory or AmazonSpApiClient

    @property
    def enabled(self) -> bool:
        settings = self._settings()
        return bool(settings.amazon_sp_api_enabled and not _missing_credentials(settings))

    def configuration_status(self) -> dict[str, Any]:
        settings = self._settings()
        missing = _missing_credentials(settings)
        return {
            "configured": not missing,
            "environment": settings.amazon_sp_api_environment,
            "missing_credentials": missing,
        }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        settings = self._settings()
        if not self.enabled:
            raise RuntimeError(
                f"{self.name} is disabled or incomplete. Enable Amazon SP-API and configure "
                "the LWA credentials, refresh token, and marketplace ID."
            )
        keywords = (query.query or "").strip()
        if not keywords:
            raise RuntimeError(f"{self.name} requires query.query keywords.")

        configured_limit = int(getattr(settings, "amazon_catalog_search_limit", 10))
        page_size = min(query.limit, configured_limit) if configured_limit > 0 else query.limit
        with self.client_factory(settings) as client:
            payload = client.get_catalog_items(keywords, page_size=page_size)

        observed_at = datetime.now(UTC)
        items = payload.get("items") or []
        return [
            _catalog_observation(
                item=item,
                query=query,
                observed_at=observed_at,
                index=index,
                marketplace_id=settings.amazon_marketplace_id,
                environment=settings.amazon_sp_api_environment,
                store_raw_payloads=bool(settings.store_raw_amazon_payloads),
            )
            for index, item in enumerate(items)
            if isinstance(item, dict)
        ]

    def _settings(self) -> Any:
        return self.settings or get_settings()


def _catalog_observation(
    *,
    item: dict[str, Any],
    query: IngestionQuery,
    observed_at: datetime,
    index: int,
    marketplace_id: str,
    environment: str,
    store_raw_payloads: bool,
) -> RawObservationDTO:
    asin_value = item.get("asin")
    asin = str(asin_value) if asin_value else None
    summary = _first_dict(item.get("summaries"))
    title = _first_string(summary, "itemName", "item_name", "title")
    brand = _first_string(summary, "brand", "manufacturer")
    product_type = _product_type(item, summary)
    amazon_category = _browse_category(summary) or product_type
    seed_category = query.category
    image_urls = _image_urls(item)
    source_url = f"https://www.amazon.com/dp/{asin}" if asin else None
    sales_ranks = _sales_rank_observations(item)
    best_rank = sales_ranks[0] if sales_ranks else {}
    sales_rank = best_rank.get("rank")
    dimensions = _dimensions(item, summary)
    raw_payload = {"raw_catalog_item": item} if store_raw_payloads else {}

    return RawObservationDTO(
        source="amazon_sp_api",
        source_plugin=AmazonCatalogSpApiPlugin.name,
        observed_at=observed_at,
        entity_type="marketplace_listing",
        external_id=asin or f"amazon-catalog-{index}",
        title=title,
        url=source_url,
        metrics={
            "bestseller_rank": sales_rank,
            "sales_rank": sales_rank,
            "rank_category": best_rank.get("rank_category"),
        },
        metadata={
            "evidence_type": "amazon_catalog",
            "schema_version": "amazon_catalog_normalized_v2",
            "product_name": (query.query or title or "").strip().lower() or None,
            "asin": asin,
            "title": title,
            "brand": brand,
            "seed_category": seed_category,
            "amazon_category": amazon_category,
            "amazon_product_type": product_type,
            "category": amazon_category,
            "product_type": product_type,
            "dimensions": dimensions,
            "image_url": image_urls[0] if image_urls else None,
            "sales_rank": sales_rank,
            "sales_ranks": sales_ranks,
            "rank_category": best_rank.get("rank_category"),
            "browse_node": best_rank.get("browse_node"),
            "rank_classification": best_rank.get("classification"),
            "source_url": source_url,
            "marketplace_id": marketplace_id,
            "amazon_spapi_env": environment,
            "retrieved_at": observed_at.isoformat(),
            "raw_payload_stored": store_raw_payloads,
            **raw_payload,
        },
        media_urls=image_urls,
    )


def _missing_credentials(settings: Any) -> list[str]:
    required = {
        "AMAZON_LWA_CLIENT_ID": settings.amazon_lwa_client_id,
        "AMAZON_LWA_CLIENT_SECRET": settings.amazon_lwa_client_secret,
        "AMAZON_LWA_REFRESH_TOKEN": settings.amazon_refresh_token,
        "AMAZON_MARKETPLACE_ID": settings.amazon_marketplace_id,
    }
    return [name for name, value in required.items() if not value]


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return {}


def _first_string(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _browse_category(summary: dict[str, Any]) -> str | None:
    classification = summary.get("browseClassification")
    if not isinstance(classification, dict):
        return None
    return _first_string(classification, "displayName", "classificationId")


def _product_type(item: dict[str, Any], summary: dict[str, Any]) -> str | None:
    direct = _first_string(summary, "productType", "itemClassification")
    if direct:
        return direct
    product_types = item.get("productTypes")
    row = _first_dict(product_types)
    return _first_string(row, "productType", "displayName")


def _dimensions(item: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any] | None:
    for value in (
        summary.get("itemDimensions"),
        summary.get("packageDimensions"),
        item.get("dimensions"),
    ):
        if isinstance(value, dict) and value:
            return value
    attributes = item.get("attributes")
    if isinstance(attributes, dict):
        selected = {
            key: value
            for key, value in attributes.items()
            if "dimension" in key.lower() or key.lower() in {"item_weight", "package_weight"}
        }
        return selected or None
    return None


def _image_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for image_group in item.get("images") or []:
        if not isinstance(image_group, dict):
            continue
        for image in image_group.get("images") or []:
            if isinstance(image, dict) and image.get("link"):
                url = str(image["link"])
                if url not in urls:
                    urls.append(url)
    return urls


def _best_sales_rank(item: dict[str, Any]) -> int | None:
    ranks = [
        row["rank"]
        for row in _sales_rank_observations(item)
        if row.get("rank") is not None
    ]
    return min(ranks) if ranks else None


def _sales_rank_observations(item: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank_group in item.get("salesRanks") or []:
        if not isinstance(rank_group, dict):
            continue
        browse_node = _first_string(rank_group, "marketplaceId", "displayGroupRanksTitle")
        for source_key, classification in (
            ("ranks", "rank"),
            ("classificationRanks", "classification"),
        ):
            for rank in rank_group.get(source_key) or []:
                if not isinstance(rank, dict):
                    continue
                try:
                    rank_value = int(rank["rank"])
                except (KeyError, TypeError, ValueError):
                    continue
                category = _first_string(rank, "title", "displayName", "category", "classificationId")
                rows.append(
                    {
                        "rank": rank_value,
                        "rank_category": category,
                        "browse_node": _first_string(rank, "link", "classificationId") or browse_node,
                        "classification": classification,
                    }
                )
    return sorted(rows, key=lambda row: row["rank"])
