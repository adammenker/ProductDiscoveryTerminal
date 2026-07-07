from __future__ import annotations

from statistics import mean

from app.schemas.plugin import AnalyzerResult, ProductContext


class CompetitionAnalyzer:
    name = "competition_analyzer"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Extracts competition signals from marketplace-like observations.",
        "supports": ["market_signals", "insights"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        signals: list[dict] = []
        review_counts: list[float] = []
        seller_counts: list[float] = []
        ratings: list[float] = []

        for observation in context.observations:
            metrics = observation.get("metrics") or {}
            source = observation.get("source") or "unknown"
            for key, signal_type in (
                ("review_count", "review_count"),
                ("rating", "rating"),
                ("seller_count", "seller_count"),
                ("price", "price"),
                ("bestseller_rank", "bestseller_rank"),
            ):
                if metrics.get(key) is None:
                    continue
                value = float(metrics[key])
                signals.append(
                    {
                        "source": source,
                        "signal_type": signal_type,
                        "value": value,
                        "unit": "count" if key.endswith("count") else None,
                        "metadata": {"observation_id": observation["id"]},
                    }
                )
                if key == "review_count":
                    review_counts.append(value)
                elif key == "seller_count":
                    seller_counts.append(value)
                elif key == "rating":
                    ratings.append(value)

        if not signals:
            return AnalyzerResult()

        avg_reviews = mean(review_counts) if review_counts else 0
        avg_sellers = mean(seller_counts) if seller_counts else 0
        avg_rating = mean(ratings) if ratings else 0
        body = (
            f"Observed competition averages about {avg_reviews:.0f} reviews, "
            f"{avg_sellers:.0f} sellers, and a {avg_rating:.1f} rating across available listings."
        )
        insight = {
            "insight_type": "competition_summary",
            "title": "Marketplace competition snapshot",
            "body": body,
            "confidence": 0.72,
            "evidence_observation_ids": [
                observation["id"]
                for observation in context.observations
                if (observation.get("metrics") or {}).get("review_count") is not None
            ],
            "metadata": {
                "avg_review_count": avg_reviews,
                "avg_seller_count": avg_sellers,
                "avg_rating": avg_rating,
            },
        }
        return AnalyzerResult(market_signals=signals, insights=[insight])

