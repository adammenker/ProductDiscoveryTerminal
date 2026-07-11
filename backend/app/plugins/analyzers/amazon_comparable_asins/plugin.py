from __future__ import annotations

from statistics import median_high
from typing import Any

from app.schemas.plugin import AnalyzerResult, ProductContext

AMAZON_PLUGIN_NAMES = {
    "amazon_catalog_spapi",
    "amazon_pricing_spapi",
    "amazon_fees_spapi",
}
FEE_DISCLAIMER = "Estimated from comparable ASINs, not guaranteed actual fees."


class AmazonComparableAsinsAnalyzer:
    name = "amazon_comparable_asins"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Models price and fee proxies from comparable Amazon ASIN evidence.",
        "supports": ["market_signals", "cost_models", "insights", "comparable_asins"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        comparable = _comparable_observations(context.observations)
        if not comparable:
            return AnalyzerResult()

        pricing = [row for row in comparable if row["evidence_type"] == "amazon_pricing"]
        fees = [row for row in comparable if row["evidence_type"] == "amazon_fees"]
        modeled_prices = [
            price
            for row in pricing
            if (price := _modeled_price(row["observation"].get("metrics") or {})) is not None
        ]
        modeled_price = round(median_high(modeled_prices), 2) if modeled_prices else None

        cost_models = _cost_models(fees)
        insight = _insight(
            context=context,
            comparable=comparable,
            modeled_prices=modeled_prices,
            modeled_price=modeled_price,
            fees=fees,
        )
        return AnalyzerResult(
            cost_models=cost_models,
            insights=[insight],
        )


def _comparable_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparable: list[dict[str, Any]] = []
    for observation in observations:
        metadata = observation.get("metadata") or {}
        source_plugin = observation.get("source_plugin")
        evidence_type = metadata.get("evidence_type")
        if source_plugin not in AMAZON_PLUGIN_NAMES and evidence_type not in {
            "amazon_catalog",
            "amazon_pricing",
            "amazon_fees",
        }:
            continue
        asin = metadata.get("asin") or metadata.get("comparable_asin")
        if not asin:
            external_id = str(observation.get("external_id") or "")
            asin = external_id.split(":", 1)[0] or None
        if not asin:
            continue
        comparable.append(
            {
                "asin": str(asin),
                "evidence_type": evidence_type or _evidence_type(source_plugin),
                "observation": observation,
            }
        )
    return comparable


def _evidence_type(source_plugin: Any) -> str:
    return {
        "amazon_catalog_spapi": "amazon_catalog",
        "amazon_pricing_spapi": "amazon_pricing",
        "amazon_fees_spapi": "amazon_fees",
    }.get(str(source_plugin), "amazon_catalog")


def _modeled_price(metrics: dict[str, Any]) -> float | None:
    for key in ("featured_offer_price", "competitive_price", "lowest_offer_price", "price"):
        try:
            if metrics.get(key) is not None:
                value = round(float(metrics[key]), 2)
                if value > 0:
                    return value
        except (TypeError, ValueError):
            continue
    return None


def _cost_models(fees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for row in fees:
        observation = row["observation"]
        metrics = observation.get("metrics") or {}
        metadata = observation.get("metadata") or {}
        try:
            selling_price = float(metrics["selling_price"])
        except (KeyError, TypeError, ValueError):
            continue
        models.append(
            {
                "model_name": "amazon_fba_fee_estimate",
                "selling_price": round(selling_price, 2),
                "fulfillment_cost_per_unit": metrics.get("fulfillment_fee_per_unit"),
                "marketplace_fee_per_unit": metrics.get("referral_fee_per_unit"),
                "currency": metadata.get("currency") or "USD",
                "assumptions": {
                    "total_amazon_fees": metrics.get("total_amazon_fees"),
                    "fee_estimate_source": "amazon_spapi_product_fees",
                    "fee_source": metadata.get("fee_source") or "amazon_product_fees",
                    "status": metadata.get("status") or "live_spapi",
                    "confidence": metadata.get("confidence") or "high",
                    "modeled_price_source": metadata.get("modeled_price_source") or "amazon_pricing",
                    "comparable_asin": row["asin"],
                    "fee_estimate_id": metadata.get("fee_estimate_id"),
                    "fee_components": metadata.get("fee_components") or [],
                    "amazon_spapi_env": metadata.get("amazon_spapi_env"),
                    "estimate_confidence": "proxy_asin",
                    "evidence_observation_id": observation.get("id"),
                    "disclaimer": FEE_DISCLAIMER,
                },
            }
        )
    return models


def _insight(
    *,
    context: ProductContext,
    comparable: list[dict[str, Any]],
    modeled_prices: list[float],
    modeled_price: float | None,
    fees: list[dict[str, Any]],
) -> dict[str, Any]:
    asins = list(dict.fromkeys(row["asin"] for row in comparable))
    price_text = (
        f"${modeled_price:.2f}, the median of {len(modeled_prices)} available price proxies"
        if modeled_price is not None
        else "not available because the comparable observations have no usable prices"
    )
    body = (
        f"{context.canonical_name} is associated with {len(asins)} comparable Amazon ASIN"
        f"{'s' if len(asins) != 1 else ''}: {', '.join(asins)}. "
        f"The modeled sale price is {price_text}. {FEE_DISCLAIMER}"
    )
    fee_totals = [
        float(total)
        for row in fees
        if (total := (row["observation"].get("metrics") or {}).get("total_amazon_fees"))
        is not None
    ]
    return {
        "insight_type": "competition_summary",
        "title": "Amazon comparable ASIN proxies",
        "body": body,
        "confidence": 0.78 if modeled_prices and fees else 0.62,
        "evidence_observation_ids": [
            observation_id
            for row in comparable
            if (observation_id := row["observation"].get("id")) is not None
        ],
        "metadata": {
            "comparable_asins": asins,
            "asin_observation_ids": {
                asin: [
                    row["observation"].get("id")
                    for row in comparable
                    if row["asin"] == asin and row["observation"].get("id") is not None
                ]
                for asin in asins
            },
            "modeled_price": modeled_price,
            "modeled_price_method": "median_comparable_price_proxy",
            "price_range": {
                "low": min(modeled_prices) if modeled_prices else None,
                "high": max(modeled_prices) if modeled_prices else None,
            },
            "fee_range": {
                "low": min(fee_totals) if fee_totals else None,
                "high": max(fee_totals) if fee_totals else None,
            },
            "proxy_disclaimer": FEE_DISCLAIMER,
        },
    }
