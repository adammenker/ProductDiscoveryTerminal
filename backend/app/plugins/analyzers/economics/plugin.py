from __future__ import annotations

from statistics import mean

from app.schemas.plugin import AnalyzerResult, ProductContext


class EconomicsAnalyzer:
    name = "economics_analyzer"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Creates simple FBA-like unit economics estimates from price and supplier signals.",
        "supports": ["cost_models"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        prices = [
            float((observation.get("metrics") or {})["price"])
            for observation in context.observations
            if (observation.get("metrics") or {}).get("price") is not None
        ]
        supplier_costs = [
            float(signal["unit_cost"])
            for signal in context.supplier_signals
            if signal.get("unit_cost") is not None
        ]
        shipping = [
            float(signal["shipping_estimate"])
            for signal in context.supplier_signals
            if signal.get("shipping_estimate") is not None
        ]

        if not prices or not supplier_costs:
            return AnalyzerResult()

        selling_price = round(mean(prices), 2)
        unit_cost = round(min(supplier_costs), 2)
        freight_cost = round(mean(shipping), 2) if shipping else 1.0
        packaging_cost = 0.65
        marketplace_fee = round(selling_price * 0.15, 2)
        fulfillment_cost = round(max(3.25, selling_price * 0.13), 2)
        storage_cost = 0.35
        gross_margin = round(((selling_price - unit_cost) / selling_price) * 100, 2)
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
                    "model_name": "fba_estimate",
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
                        "marketplace_fee_rate": 0.15,
                        "fulfillment_floor": 3.25,
                        "source": "deterministic_mvp_estimate",
                    },
                }
            ]
        )

