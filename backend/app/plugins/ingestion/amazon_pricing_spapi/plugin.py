from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import sleep
from typing import Any

from app.core.config import get_settings
from app.integrations.amazon_sp_api import AmazonSpApiClient
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AmazonPricingSpApiPlugin:
    name = "amazon_pricing_spapi"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Retrieves competitive pricing evidence for comparable Amazon ASINs.",
        "requires_auth": True,
        "auto_run": False,
        "supports": ["marketplace_listing", "pricing", "offers"],
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
        asins = _asins_from_metadata(query.metadata)
        if not asins:
            raise RuntimeError(f"{self.name} requires ASINs in query.metadata['asins'].")

        observations: list[RawObservationDTO] = []
        errors: list[dict[str, str]] = []
        observed_at = datetime.now(UTC)
        request_interval = max(
            0.0,
            float(getattr(settings, "amazon_pricing_request_interval_seconds", 0.0)),
        )
        with self.client_factory(settings) as client:
            for index, asin in enumerate(asins[: query.limit]):
                try:
                    if index and request_interval:
                        sleep(request_interval)
                    payload = client.get_competitive_pricing_for_asin(asin)
                    observations.append(
                        _pricing_observation(
                            asin=asin,
                            payload=payload,
                            observed_at=observed_at,
                            marketplace_id=settings.amazon_marketplace_id,
                            environment=settings.amazon_sp_api_environment,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append({"asin": asin, "error": str(exc)})

        if errors:
            if not observations:
                details = "; ".join(f"{item['asin']}: {item['error']}" for item in errors)
                raise RuntimeError(details)
            for observation in observations:
                observation.metadata["request_errors"] = errors
        return observations

    def _settings(self) -> Any:
        return self.settings or get_settings()


def _pricing_observation(
    *,
    asin: str,
    payload: dict[str, Any],
    observed_at: datetime,
    marketplace_id: str,
    environment: str,
) -> RawObservationDTO:
    result = _pricing_result(payload, asin)
    product = _dict_value(result, "Product")
    competitive = _dict_value(product, "CompetitivePricing")
    prices = competitive.get("CompetitivePrices") or []
    offer_listings = competitive.get("NumberOfOfferListings") or []

    competitive_prices: list[float] = []
    featured_prices: list[float] = []
    for price_row in prices:
        if not isinstance(price_row, dict):
            continue
        amount = _first_amount(price_row.get("Price"), price_row)
        if amount is None:
            continue
        competitive_prices.append(amount)
        price_id = str(price_row.get("CompetitivePriceId") or "").lower()
        belongs_to_requester = price_row.get("belongsToRequester")
        if price_id in {"1", "featuredoffer", "featured_offer"} or belongs_to_requester is True:
            featured_prices.append(amount)

    offer_prices: list[float] = []
    offers = product.get("Offers") or result.get("Offers") or []
    for offer in offers:
        if isinstance(offer, dict):
            amount = _first_amount(offer.get("BuyingPrice"), offer)
            if amount is not None:
                offer_prices.append(amount)

    offer_count = _offer_count(offer_listings)
    competitive_price = min(competitive_prices) if competitive_prices else None
    featured_offer_price = min(featured_prices) if featured_prices else competitive_price
    lowest_offer_price = min(offer_prices or competitive_prices) if (offer_prices or competitive_prices) else None
    modeled_price = featured_offer_price or competitive_price or lowest_offer_price

    return RawObservationDTO(
        source="amazon_sp_api",
        source_plugin=AmazonPricingSpApiPlugin.name,
        observed_at=observed_at,
        entity_type="marketplace_listing",
        external_id=f"{asin}:pricing",
        title=f"Amazon pricing for {asin}",
        url=f"https://www.amazon.com/dp/{asin}",
        metrics={
            "price": modeled_price,
            "offer_count": offer_count,
            "seller_count": offer_count,
            "featured_offer_price": featured_offer_price,
            "competitive_price": competitive_price,
            "lowest_offer_price": lowest_offer_price,
        },
        metadata={
            "evidence_type": "amazon_pricing",
            "asin": asin,
            "marketplace_id": marketplace_id,
            "amazon_spapi_env": environment,
            "currency": _currency_code(result) or "USD",
            "raw_pricing_response": payload,
        },
    )


def _asins_from_metadata(metadata: dict[str, Any]) -> list[str]:
    raw = metadata.get("asins")
    if raw is None:
        raw = metadata.get("comparable_asins")
    if raw is None and metadata.get("asin"):
        raw = [metadata["asin"]]
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, list):
        return []

    asins: list[str] = []
    for value in raw:
        if isinstance(value, dict):
            value = value.get("asin") or value.get("ASIN")
        asin = str(value).strip().upper() if value else ""
        if asin and asin not in asins:
            asins.append(asin)
    return asins


def _pricing_result(payload: dict[str, Any], asin: str) -> dict[str, Any]:
    rows = payload.get("payload")
    if isinstance(rows, dict):
        rows = [rows]
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and str(row.get("ASIN") or row.get("asin") or asin) == asin:
                return row
        return next((row for row in rows if isinstance(row, dict)), {})
    return payload


def _first_amount(*values: Any) -> float | None:
    for value in values:
        if not isinstance(value, dict):
            continue
        for candidate in (
            value.get("LandedPrice"),
            value.get("ListingPrice"),
            value.get("Shipping"),
            value,
        ):
            if not isinstance(candidate, dict):
                continue
            amount = candidate.get("Amount")
            if amount is None:
                amount = candidate.get("amount")
            try:
                if amount is not None:
                    return round(float(amount), 2)
            except (TypeError, ValueError):
                continue
    return None


def _offer_count(rows: Any) -> int | None:
    if not isinstance(rows, list):
        return None
    count = 0
    found = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("Count")
        if value is None:
            value = row.get("count")
        if value is None:
            continue
        try:
            count += int(value)
            found = True
        except (TypeError, ValueError):
            continue
    return count if found else None


def _currency_code(result: dict[str, Any]) -> str | None:
    product = _dict_value(result, "Product")
    competitive = _dict_value(product, "CompetitivePricing")
    for row in competitive.get("CompetitivePrices") or []:
        if not isinstance(row, dict):
            continue
        price = row.get("Price")
        if not isinstance(price, dict):
            continue
        for field in ("LandedPrice", "ListingPrice"):
            money = price.get(field)
            if isinstance(money, dict) and money.get("CurrencyCode"):
                return str(money["CurrencyCode"])
    return None


def _dict_value(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    return value if isinstance(value, dict) else {}


def _missing_credentials(settings: Any) -> list[str]:
    required = {
        "AMAZON_LWA_CLIENT_ID": settings.amazon_lwa_client_id,
        "AMAZON_LWA_CLIENT_SECRET": settings.amazon_lwa_client_secret,
        "AMAZON_LWA_REFRESH_TOKEN": settings.amazon_refresh_token,
        "AMAZON_MARKETPLACE_ID": settings.amazon_marketplace_id,
    }
    return [name for name, value in required.items() if not value]
