from __future__ import annotations

from app.schemas.plugin import AnalyzerResult, ProductContext


class DemandAnalyzer:
    name = "demand_analyzer"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Creates demand and trend market signals from raw observations.",
        "supports": ["market_signals"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        signals: list[dict] = []
        for observation in context.observations:
            metrics = observation.get("metrics") or {}
            source = observation.get("source") or "unknown"
            if metrics.get("trend_score") is not None:
                signals.append(
                    {
                        "source": source,
                        "signal_type": "trend_score",
                        "value": float(metrics["trend_score"]),
                        "unit": "index",
                        "metadata": {"observation_id": observation["id"]},
                    }
                )
            if metrics.get("growth_percent") is not None:
                signals.append(
                    {
                        "source": source,
                        "signal_type": "search_growth",
                        "value": float(metrics["growth_percent"]),
                        "unit": "percent_90d",
                        "metadata": {"observation_id": observation["id"]},
                    }
                )
            if metrics.get("search_volume_index") is not None:
                signals.append(
                    {
                        "source": source,
                        "signal_type": "search_volume",
                        "value": float(metrics["search_volume_index"]),
                        "unit": "index",
                        "metadata": {"observation_id": observation["id"]},
                    }
                )
            social_value = metrics.get("mentions") or metrics.get("comments")
            if social_value is not None:
                signals.append(
                    {
                        "source": source,
                        "signal_type": "social_mentions",
                        "value": float(social_value),
                        "unit": "count",
                        "metadata": {"observation_id": observation["id"]},
                    }
                )
        return AnalyzerResult(market_signals=signals)

