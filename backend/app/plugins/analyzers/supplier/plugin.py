from __future__ import annotations

from app.schemas.plugin import AnalyzerResult, ProductContext


class SupplierAnalyzer:
    name = "supplier_analyzer"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Extracts supplier economics from supplier-like observations.",
        "supports": ["supplier_signals"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        supplier_signals: list[dict] = []
        for observation in context.observations:
            metrics = observation.get("metrics") or {}
            metadata = observation.get("metadata") or {}
            if metrics.get("unit_cost") is None:
                continue
            supplier_signals.append(
                {
                    "source": observation.get("source") or "unknown",
                    "supplier_name": metadata.get("supplier_name"),
                    "supplier_url": observation.get("url"),
                    "unit_cost": float(metrics["unit_cost"]),
                    "moq": int(metrics["moq"]) if metrics.get("moq") is not None else None,
                    "lead_time_days": (
                        int(metrics["lead_time_days"])
                        if metrics.get("lead_time_days") is not None
                        else None
                    ),
                    "shipping_estimate": (
                        float(metrics["shipping_estimate"])
                        if metrics.get("shipping_estimate") is not None
                        else None
                    ),
                    "country": metadata.get("country"),
                    "metadata": {"observation_id": observation["id"]},
                }
            )
        return AnalyzerResult(supplier_signals=supplier_signals)

