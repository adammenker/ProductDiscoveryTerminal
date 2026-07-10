from __future__ import annotations

from datetime import UTC, datetime

from app.plugins.ingestion.mock_data import filter_fixtures
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class GoogleTrendsMockPlugin:
    name = "google_trends_mock"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Simulates search trend growth observations.",
        "requires_auth": False,
        "auto_run": False,
        "supports": ["trend", "search_result"],
    }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        observed_at = datetime.now(UTC)
        observations: list[RawObservationDTO] = []
        for item in filter_fixtures(query.category, query.limit):
            product_name = item["product_name"]
            observations.append(
                RawObservationDTO(
                    source="google_trends_mock",
                    source_plugin=self.name,
                    observed_at=observed_at,
                    entity_type="trend",
                    external_id=f"trend-{product_name.replace(' ', '-')}",
                    title=f"{product_name} trend signal",
                    raw_text=(
                        f"Search interest for {product_name} has a trend score of "
                        f"{item['trend_score']} and 90 day growth of {item['growth_percent']}%."
                    ),
                    metrics={
                        "trend_score": item["trend_score"],
                        "growth_percent": item["growth_percent"],
                        "search_volume_index": item["trend_score"] * 12,
                    },
                    metadata={
                        "product_name": product_name,
                        "category": item["category"],
                        "window": "90d",
                    },
                )
            )
        return observations
