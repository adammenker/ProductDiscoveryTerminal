from __future__ import annotations

from statistics import mean

from app.core.config import Settings, get_settings
from app.economics.cost_ceiling import (
    CostCeilingInputs,
    calculate_cost_ceiling,
    calculate_cost_ceiling_v2,
)
from app.schemas.plugin import AnalyzerResult, ProductContext


class EconomicsAnalyzer:
    name = "economics_analyzer"
    version = "0.2.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Creates FBA-style unit economics and max landed-cost ceilings.",
        "supports": ["cost_models", "cost_ceiling", "insights"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        prices = [
            float((observation.get("metrics") or {})["price"])
            for observation in context.observations
            if (observation.get("metrics") or {}).get("price") is not None
        ]

        if not prices:
            return AnalyzerResult()

        supplier_quote = self._best_supplier_quote(context)
        selling_price = round(mean(prices), 2)
        unit_cost = supplier_quote["unit_cost"] if supplier_quote else None
        freight_cost = supplier_quote["freight_cost_per_unit"] if supplier_quote else None
        packaging_cost = round(self.settings.cost_ceiling_packaging_cost_per_unit, 2)
        marketplace_fee = round(selling_price * self.settings.cost_ceiling_marketplace_fee_rate, 2)
        fulfillment_cost = round(
            max(
                self.settings.cost_ceiling_fulfillment_fee_floor,
                selling_price * self.settings.cost_ceiling_fulfillment_fee_rate,
            ),
            2,
        )
        storage_cost = round(self.settings.cost_ceiling_storage_cost_per_unit, 2)
        inbound_cost = round(self.settings.cost_ceiling_inbound_cost_per_unit, 2)
        return_allowance = round(selling_price * self.settings.cost_ceiling_return_allowance_rate, 2)
        ad_allowance = round(selling_price * self.settings.cost_ceiling_ad_allowance_rate, 2)
        target_profit = round(selling_price * self.settings.cost_ceiling_target_profit_rate, 2)

        cost_ceiling = calculate_cost_ceiling(
            CostCeilingInputs(
                selling_price=selling_price,
                referral_fee_per_unit=marketplace_fee,
                fulfillment_fee_per_unit=fulfillment_cost,
                inbound_cost_per_unit=inbound_cost,
                storage_estimate=storage_cost,
                return_allowance=return_allowance,
                ad_allowance=ad_allowance,
                target_profit=target_profit,
                supplier_unit_cost=unit_cost,
                supplier_freight_cost_per_unit=freight_cost,
                packaging_cost_per_unit=packaging_cost,
            )
        )
        cost_ceiling_v2 = calculate_cost_ceiling_v2(
            selling_price=selling_price,
            amazon_fees=marketplace_fee + fulfillment_cost,
            inbound_cost_per_unit=inbound_cost,
            storage_estimate=storage_cost,
            return_allowance_rate=self.settings.cost_ceiling_return_allowance_rate,
            ad_allowance_rate=self.settings.cost_ceiling_ad_allowance_rate,
            supplier_unit_cost=unit_cost,
            supplier_freight_cost_per_unit=freight_cost,
            packaging_cost_per_unit=packaging_cost,
        )

        gross_margin = (
            round(((selling_price - unit_cost) / selling_price) * 100, 2)
            if unit_cost is not None
            else None
        )
        net_margin = None
        if unit_cost is not None and freight_cost is not None:
            total_cost = (
                unit_cost
                + freight_cost
                + packaging_cost
                + marketplace_fee
                + fulfillment_cost
                + storage_cost
            )
            net_margin = round(((selling_price - total_cost) / selling_price) * 100, 2)

        return AnalyzerResult(
            cost_models=[
                {
                    "model_name": "fba_cost_ceiling",
                    "selling_price": selling_price,
                    "unit_cost": unit_cost,
                    "freight_cost_per_unit": freight_cost,
                    "packaging_cost_per_unit": packaging_cost,
                    "fulfillment_cost_per_unit": fulfillment_cost,
                    "marketplace_fee_per_unit": marketplace_fee,
                    "storage_cost_per_unit": storage_cost,
                    "estimated_gross_margin": gross_margin,
                    "estimated_net_margin": net_margin,
                    "currency": "USD",
                    "assumptions": {
                        "marketplace_fee_rate": self.settings.cost_ceiling_marketplace_fee_rate,
                        "fulfillment_fee_rate": self.settings.cost_ceiling_fulfillment_fee_rate,
                        "fulfillment_fee_floor": self.settings.cost_ceiling_fulfillment_fee_floor,
                        "inbound_cost_per_unit": inbound_cost,
                        "return_allowance_rate": self.settings.cost_ceiling_return_allowance_rate,
                        "ad_allowance_rate": self.settings.cost_ceiling_ad_allowance_rate,
                        "target_profit_rate": self.settings.cost_ceiling_target_profit_rate,
                        "cost_ceiling": cost_ceiling.as_dict(),
                        "cost_ceiling_v2": cost_ceiling_v2,
                        "fee_source": "heuristic_until_amazon_sp_api_product_fees_is_configured",
                        "fee_source_confidence": "low",
                        "source_priority": [
                            "amazon_spapi_product_fees",
                            "manual_amazon_fee_estimate",
                            "third_party_fee_estimate",
                            "configurable_defaults",
                        ],
                        "source": "deterministic_mvp_estimate",
                    },
                }
            ],
            insights=[self._cost_ceiling_insight(cost_ceiling.as_dict(), context)],
        )

    def _best_supplier_quote(self, context: ProductContext) -> dict[str, float] | None:
        quotes: list[dict[str, float]] = []
        for signal in context.supplier_signals:
            if signal.get("unit_cost") is None:
                continue
            unit_cost = round(float(signal["unit_cost"]), 2)
            shipping_estimate = signal.get("shipping_estimate")
            freight_source = (
                float(shipping_estimate)
                if shipping_estimate is not None
                else self.settings.cost_ceiling_supplier_freight_fallback_per_unit
            )
            freight_cost = round(freight_source, 2)
            quotes.append(
                {
                    "unit_cost": unit_cost,
                    "freight_cost_per_unit": freight_cost,
                    "landed_cost": unit_cost
                    + freight_cost
                    + self.settings.cost_ceiling_packaging_cost_per_unit,
                }
            )
        if not quotes:
            return None
        return min(quotes, key=lambda quote: quote["landed_cost"])

    def _cost_ceiling_insight(
        self,
        cost_ceiling: dict[str, float | str | None],
        context: ProductContext,
    ) -> dict:
        max_landed_cost = cost_ceiling["max_landed_cost"]
        target_profit = cost_ceiling["target_profit"]
        supplier_landed_cost = cost_ceiling["supplier_landed_cost"]
        margin_of_safety = cost_ceiling["margin_of_safety"]
        if supplier_landed_cost is None:
            title = "Supplier quote needed"
            body = (
                f"Target landed cost ceiling is ${max_landed_cost:.2f} per unit "
                f"to preserve about ${target_profit:.2f} target profit."
            )
            confidence = 0.55
        elif cost_ceiling["decision"] == "quote_at_or_below_ceiling":
            title = "Supplier quote clears cost ceiling"
            body = (
                f"Estimated supplier landed cost is ${supplier_landed_cost:.2f}, "
                f"which is ${margin_of_safety:.2f} below the ${max_landed_cost:.2f} ceiling."
            )
            confidence = 0.74
        else:
            title = "Supplier quote exceeds cost ceiling"
            body = (
                f"Estimated supplier landed cost is ${supplier_landed_cost:.2f}, "
                f"which is ${abs(float(margin_of_safety or 0)):.2f} above the "
                f"${max_landed_cost:.2f} ceiling."
            )
            confidence = 0.74

        return {
            "insight_type": "cost_ceiling",
            "title": title,
            "body": body,
            "confidence": confidence,
            "evidence_observation_ids": [observation["id"] for observation in context.observations],
            "metadata": cost_ceiling,
        }
