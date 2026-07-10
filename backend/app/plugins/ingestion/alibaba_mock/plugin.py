from __future__ import annotations

from datetime import UTC, datetime

from app.plugins.ingestion.mock_data import filter_fixtures
from app.schemas.plugin import IngestionQuery, RawObservationDTO


class AlibabaMockPlugin:
    name = "alibaba_mock"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Simulates supplier economics observations.",
        "requires_auth": False,
        "auto_run": False,
        "supports": ["supplier"],
    }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        observed_at = datetime.now(UTC)
        observations: list[RawObservationDTO] = []
        for item in filter_fixtures(query.category, query.limit):
            product_name = item["product_name"]
            observations.append(
                RawObservationDTO(
                    source="alibaba_mock",
                    source_plugin=self.name,
                    observed_at=observed_at,
                    entity_type="supplier",
                    external_id=f"supplier-{product_name.replace(' ', '-')}",
                    title=f"{product_name.title()} wholesale supplier estimate",
                    url=f"https://example.com/supplier/{product_name.replace(' ', '-')}",
                    raw_text=(
                        f"{item['supplier_name']} offers {product_name} at an estimated "
                        f"${item['unit_cost']} unit cost with MOQ {item['moq']}."
                    ),
                    metrics={
                        "unit_cost": item["unit_cost"],
                        "moq": item["moq"],
                        "lead_time_days": item["lead_time_days"],
                        "shipping_estimate": item["shipping_estimate"],
                    },
                    metadata={
                        "product_name": product_name,
                        "category": item["category"],
                        "supplier_name": item["supplier_name"],
                        "country": "China",
                    },
                )
            )
        return observations
