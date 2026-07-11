from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from time import sleep
from typing import Any

from app.core.config import get_settings
from app.integrations.amazon_sp_api import AmazonSpApiClient
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AmazonFeesSpApiPlugin:
    name = "amazon_fees_spapi"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Retrieves Amazon Product Fees estimates for comparable ASIN proxies.",
        "requires_auth": True,
        "auto_run": False,
        "supports": ["marketplace_listing", "product_fees", "cost_model_evidence"],
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
        requests = _fee_requests(query.metadata, settings)
        if not requests:
            raise RuntimeError(f"{self.name} requires ASINs in query.metadata['asins'].")

        observations: list[RawObservationDTO] = []
        errors: list[dict[str, str]] = []
        observed_at = datetime.now(UTC)
        request_interval = max(
            0.0,
            float(getattr(settings, "amazon_fees_request_interval_seconds", 0.0)),
        )
        with self.client_factory(settings) as client:
            for index, (asin, modeled_price, modeled_price_source) in enumerate(requests[: query.limit]):
                try:
                    if index and request_interval:
                        sleep(request_interval)
                    payload = client.get_fees_estimate_for_asin(asin, modeled_price)
                    observations.append(
                        _fees_observation(
                            asin=asin,
                            modeled_price=modeled_price,
                            modeled_price_source=modeled_price_source,
                            payload=payload,
                            observed_at=observed_at,
                            marketplace_id=settings.amazon_marketplace_id,
                            environment=settings.amazon_sp_api_environment,
                            store_raw_payloads=bool(settings.store_raw_amazon_payloads),
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


def _fees_observation(
    *,
    asin: str,
    modeled_price: float,
    modeled_price_source: str,
    payload: dict[str, Any],
    observed_at: datetime,
    marketplace_id: str,
    environment: str,
    store_raw_payloads: bool,
) -> RawObservationDTO:
    result = _fees_result(payload)
    estimate = _dict_value(result, "FeesEstimate")
    details = estimate.get("FeeDetailList") or result.get("FeeDetailList") or []
    fee_components = [_fee_component(row) for row in details if isinstance(row, dict)]
    fee_components = [component for component in fee_components if component["amount"] is not None]

    referral_fee = _component_total(fee_components, ("referral",))
    fulfillment_fee = _component_total(
        fee_components,
        ("fba", "fulfillment", "pickpack", "weight handling"),
    )
    total_fees = _money_amount(estimate.get("TotalFeesEstimate"))
    if total_fees is None and fee_components:
        component_amounts = [
            float(amount)
            for component in fee_components
            if (amount := component.get("amount")) is not None
        ]
        total_fees = round(sum(component_amounts), 2)
    if total_fees is None:
        errors = payload.get("errors") or []
        message = errors[0].get("message") if errors and isinstance(errors[0], dict) else None
        raise RuntimeError(message or f"Amazon returned no fee estimate for {asin}.")

    identifier = _dict_value(result, "FeesEstimateIdentifier")
    currency = _currency(estimate.get("TotalFeesEstimate"), fee_components) or "USD"
    confidence = "medium" if modeled_price_source == "configured_default" else "high"
    raw_payload = {"raw_fees_response": payload} if store_raw_payloads else {}
    return RawObservationDTO(
        source="amazon_sp_api",
        source_plugin=AmazonFeesSpApiPlugin.name,
        observed_at=observed_at,
        entity_type="marketplace_listing",
        external_id=f"{asin}:fees:{modeled_price:.2f}",
        title=f"Amazon fee estimate for {asin}",
        url=f"https://www.amazon.com/dp/{asin}",
        metrics={
            "selling_price": round(modeled_price, 2),
            "referral_fee_per_unit": referral_fee,
            "fulfillment_fee_per_unit": fulfillment_fee,
            "total_amazon_fees": total_fees,
        },
        metadata={
            "evidence_type": "amazon_fees",
            "schema_version": "amazon_fees_normalized_v2",
            "model_name": "amazon_fba_fee_estimate",
            "fee_estimate_source": "amazon_spapi_product_fees",
            "fee_source": "amazon_product_fees",
            "status": "live_spapi",
            "confidence": confidence,
            "modeled_price_source": modeled_price_source,
            "comparable_asin": asin,
            "asin": asin,
            "fee_estimate_id": identifier.get("Identifier") or identifier.get("identifier"),
            "fee_components": fee_components,
            "marketplace_id": marketplace_id,
            "amazon_spapi_env": environment,
            "estimate_confidence": "proxy_asin",
            "currency": currency,
            "disclaimer": "Estimated from comparable ASINs, not guaranteed actual fees.",
            "retrieved_at": observed_at.isoformat(),
            "raw_payload_stored": store_raw_payloads,
            **raw_payload,
        },
    )


def _fee_requests(metadata: dict[str, Any], settings: Any) -> list[tuple[str, float, str]]:
    raw_asins = metadata.get("asins")
    if raw_asins is None:
        raw_asins = metadata.get("comparable_asins")
    if raw_asins is None and metadata.get("asin"):
        raw_asins = [metadata["asin"]]
    if isinstance(raw_asins, str):
        raw_asins = raw_asins.split(",")
    if not isinstance(raw_asins, list):
        return []

    default_price = metadata.get("modeled_price")
    if default_price is None:
        default_price = getattr(settings, "amazon_fees_default_modeled_price", 24.99)
    modeled_prices = metadata.get("modeled_prices")
    if not isinstance(modeled_prices, dict):
        modeled_prices = {}

    requests: list[tuple[str, float, str]] = []
    for value in raw_asins:
        row_price: Any = None
        row_price_source = "configured_default"
        if isinstance(value, dict):
            row_price = value.get("modeled_price") or value.get("price")
            if row_price is not None:
                row_price_source = str(value.get("modeled_price_source") or "amazon_pricing")
            value = value.get("asin") or value.get("ASIN")
        asin = str(value).strip().upper().split(":", 1)[0] if value else ""
        if not re.fullmatch(r"[A-Z0-9]{10}", asin):
            continue
        if not asin or any(existing_asin == asin for existing_asin, _, _ in requests):
            continue
        if row_price is not None:
            price = row_price
            price_source = row_price_source
        elif asin in modeled_prices:
            price = modeled_prices[asin]
            price_source = "amazon_pricing"
        elif metadata.get("modeled_price") is not None:
            price = default_price
            price_source = str(metadata.get("modeled_price_source") or "manual")
        else:
            price = default_price
            price_source = "configured_default"
        if price is None:
            continue
        try:
            numeric_price = round(float(price), 2)
        except (TypeError, ValueError):
            continue
        if numeric_price > 0:
            requests.append((asin, numeric_price, price_source))
    return requests


def _fees_result(payload: dict[str, Any]) -> dict[str, Any]:
    result: Any = payload.get("payload", payload)
    if isinstance(result, list):
        result = next((row for row in result if isinstance(row, dict)), {})
    if not isinstance(result, dict):
        return {}
    nested = result.get("FeesEstimateResult")
    return nested if isinstance(nested, dict) else result


def _fee_component(row: dict[str, Any]) -> dict[str, Any]:
    amount = _money_amount(row.get("FinalFee"))
    if amount is None:
        amount = _money_amount(row.get("FeeAmount"))
    currency = None
    for key in ("FinalFee", "FeeAmount"):
        value = row.get(key)
        if isinstance(value, dict) and value.get("CurrencyCode"):
            currency = str(value["CurrencyCode"])
            break
    return {
        "fee_type": str(row.get("FeeType") or row.get("feeType") or "unknown"),
        "fee_name": row.get("FeeName") or row.get("feeName"),
        "amount": amount,
        "currency": currency,
        "raw": row,
    }


def _money_amount(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    amount = value.get("Amount")
    if amount is None:
        amount = value.get("amount")
    try:
        return round(float(amount), 2) if amount is not None else None
    except (TypeError, ValueError):
        return None


def _component_total(
    components: list[dict[str, Any]],
    terms: tuple[str, ...],
) -> float | None:
    values = [
        float(component["amount"])
        for component in components
        if any(term in str(component["fee_type"]).lower() for term in terms)
    ]
    return round(sum(values), 2) if values else None


def _currency(total: Any, components: list[dict[str, Any]]) -> str | None:
    if isinstance(total, dict) and total.get("CurrencyCode"):
        return str(total["CurrencyCode"])
    return next(
        (str(component["currency"]) for component in components if component.get("currency")),
        None,
    )


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
