from __future__ import annotations

from datetime import UTC, datetime

from app.plugins.ingestion.mock_data import filter_fixtures
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class RedditMockPlugin:
    name = "reddit_mock"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Simulates customer discussion and pain point observations.",
        "requires_auth": False,
        "auto_run": False,
        "supports": ["social_post", "review"],
    }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        observed_at = datetime.now(UTC)
        observations: list[RawObservationDTO] = []
        for index, item in enumerate(filter_fixtures(query.category, query.limit), start=1):
            product_name = item["product_name"]
            observations.append(
                RawObservationDTO(
                    source="reddit_mock",
                    source_plugin=self.name,
                    observed_at=observed_at,
                    entity_type="social_post",
                    external_id=f"reddit-{product_name.replace(' ', '-')}",
                    title=f"What is a better {product_name}?",
                    url=f"https://example.com/reddit/{product_name.replace(' ', '-')}",
                    raw_text=item["pain_text"],
                    metrics={
                        "upvotes": 180 - index * 12,
                        "comments": 44 - index * 3,
                        "mentions": 18 - index,
                    },
                    metadata={
                        "product_name": product_name,
                        "category": item["category"],
                        "sentiment": "frustrated",
                    },
                )
            )
        return observations
