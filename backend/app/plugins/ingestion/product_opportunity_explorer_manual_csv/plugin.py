from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.plugin import IngestionQuery, RawObservationDTO


class ProductOpportunityExplorerManualCsvPlugin:
    name = "product_opportunity_explorer_manual_csv"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Imports user-provided Product Opportunity Explorer CSV data without scraping.",
        "requires_auth": False,
        "supports": ["product", "manual_poe", "discovery"],
    }

    @property
    def enabled(self) -> bool:
        return False

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        raw_path = query.metadata.get("file_path")
        if not raw_path:
            return []
        path = Path(str(raw_path)).expanduser()
        if not path.exists():
            return []
        observations: list[RawObservationDTO] = []
        with path.open(newline="", encoding="utf-8") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                if len(observations) >= query.limit:
                    break
                niche = (row.get("niche") or "").strip()
                if not niche:
                    continue
                metrics = {
                    key: _number(row.get(key))
                    for key in (
                        "search_volume",
                        "search_volume_growth",
                        "purchase_growth",
                        "average_price",
                        "average_review_count",
                        "return_rate",
                    )
                    if row.get(key)
                }
                if metrics.get("average_price") is not None:
                    metrics["price"] = metrics["average_price"]
                observations.append(
                    RawObservationDTO(
                        source="amazon_product_opportunity_explorer_manual",
                        source_plugin=self.name,
                        observed_at=datetime.now(UTC),
                        entity_type="product",
                        external_id=f"poe-{index}-{niche.lower().replace(' ', '-')}",
                        title=niche,
                        raw_text=row.get("notes") or None,
                        metrics=metrics,
                        metadata={
                            "product_name": niche.lower(),
                            "top_clicked_asins": [
                                value.strip()
                                for value in (row.get("top_clicked_asins") or "").split(",")
                                if value.strip()
                            ],
                            "manual_import": True,
                        },
                    )
                )
        return observations


def _number(value: str | None) -> float | int | None:
    if not value:
        return None
    number = float(value.replace(",", "").replace("%", ""))
    return int(number) if number.is_integer() else number
