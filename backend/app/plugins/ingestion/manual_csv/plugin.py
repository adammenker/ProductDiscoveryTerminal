from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.plugin import IngestionQuery, RawObservationDTO


class ManualCsvPlugin:
    name = "manual_csv"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "ingestion",
        "description": "Loads product observations from a local CSV file.",
        "requires_auth": False,
        "auto_run": False,
        "supports": ["product", "marketplace_listing", "supplier"],
        "config_schema": {"file_path": {"type": "string", "required": False}},
    }

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        file_path = Path(
            query.metadata.get("file_path")
            or Path(__file__).resolve().parent / "sample.csv"
        )
        if not file_path.exists():
            return []

        observed_at = datetime.now(UTC)
        observations: list[RawObservationDTO] = []
        with file_path.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for index, row in enumerate(reader):
                if query.category and row.get("category", "").lower() != query.category.lower():
                    continue
                if len(observations) >= query.limit:
                    break

                title = row.get("title") or "untitled product"
                metrics = {
                    key: _parse_number(row.get(key))
                    for key in (
                        "price",
                        "review_count",
                        "rating",
                        "unit_cost",
                        "moq",
                        "lead_time_days",
                        "shipping_estimate",
                        "freight_cost_per_unit",
                        "packaging_cost_per_unit",
                    )
                    if row.get(key)
                }
                observations.append(
                    RawObservationDTO(
                        source=row.get("source") or "manual_csv",
                        source_plugin=self.name,
                        observed_at=observed_at,
                        entity_type="product",
                        external_id=f"manual-{index}-{title.lower().replace(' ', '-')}",
                        title=title,
                        url=row.get("url") or None,
                        raw_text=row.get("raw_text") or None,
                        metrics=metrics,
                        metadata={
                            "product_name": title.strip().lower(),
                            "category": row.get("category") or None,
                            "supplier_name": row.get("supplier_name") or None,
                            "supplier_url": row.get("supplier_url") or None,
                            "quote_date": row.get("quote_date") or None,
                            "currency": row.get("currency") or "USD",
                            "supplier_notes": row.get("supplier_notes") or None,
                            "country": row.get("country") or None,
                            "row_index": index,
                        },
                    )
                )
        return observations


def _parse_number(value: str | None) -> float | int | None:
    if value is None or value == "":
        return None
    number = float(value)
    return int(number) if number.is_integer() else number
