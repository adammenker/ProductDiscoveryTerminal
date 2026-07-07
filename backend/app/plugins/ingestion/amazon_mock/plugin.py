from __future__ import annotations

from datetime import UTC, datetime

from app.plugins.ingestion.mock_data import filter_fixtures
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AmazonMockPlugin:
    name = "amazon_mock"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Simulates marketplace listing observations.",
        "requires_auth": False,
        "supports": ["marketplace_listing", "product"],
    }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        observed_at = datetime.now(UTC)
        observations: list[RawObservationDTO] = []
        for item in filter_fixtures(query.category, query.limit):
            product_name = item["product_name"]
            observations.append(
                RawObservationDTO(
                    source="amazon_mock",
                    source_plugin=self.name,
                    observed_at=observed_at,
                    entity_type="marketplace_listing",
                    external_id=f"amazon-{product_name.replace(' ', '-')}",
                    title=f"{product_name.title()} - best seller style marketplace listing",
                    url=f"https://example.com/amazon/{product_name.replace(' ', '-')}",
                    raw_text=(
                        f"{product_name} listing with {item['review_count']} reviews and "
                        f"{item['seller_count']} competing sellers."
                    ),
                    metrics={
                        "price": item["price"],
                        "review_count": item["review_count"],
                        "rating": item["rating"],
                        "seller_count": item["seller_count"],
                        "bestseller_rank": item["bestseller_rank"],
                    },
                    metadata={
                        "product_name": product_name,
                        "category": item["category"],
                        "listing_quality": "mixed",
                    },
                )
            )
        return observations

