from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import CandidateOrigin, ProductCandidate
from app.schemas.discovery import DiscoveryKeywordInput, DiscoveryRunCreate
from app.schemas.plugin import IngestionQuery, RawObservationDTO
from app.services.discovery_service import DiscoveryService


class BroadCatalogFixturePlugin:
    name = "amazon_catalog_spapi"
    version = "test"
    manifest = {"type": "ingestion"}

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        if query.query == "broken keyword":
            raise RuntimeError("catalog unavailable")
        titles = [
            ("B000CABLE1", "Travel Cable Organizer Case"),
            ("B000CABLE2", "Travel Cable Organizer Pouch"),
            ("B000TOILET", "Hanging Toiletry Bag Organizer"),
            ("B000PACK01", "Compression Packing Cubes Set"),
            ("B000PASS01", "Passport Organizer Wallet"),
        ]
        return [
            RawObservationDTO(
                source="amazon_sp_api",
                source_plugin=self.name,
                observed_at=datetime.now(UTC),
                entity_type="marketplace_listing",
                external_id=asin,
                title=title,
                metrics={"bestseller_rank": 1000 + index},
                metadata={
                    "evidence_type": "amazon_catalog",
                    "schema_version": "fixture",
                    "product_name": query.query,
                    "source_query": query.query,
                    "asin": asin,
                    "title": title,
                    "amazon_category": "Travel Accessories",
                    "amazon_product_type": "BASE_PRODUCT",
                },
            )
            for index, (asin, title) in enumerate(titles)
        ]


def test_broad_discovery_query_creates_multiple_clusters_and_origins(db_session) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    request = DiscoveryRunCreate(
        keywords=[DiscoveryKeywordInput(keyword="travel organizer")],
        limit_per_keyword=10,
    )

    first = service.run_discovery(request, plugin_overrides=[BroadCatalogFixturePlugin()])

    assert first.status == "success"
    assert first.summary["clusters_created"] == 4
    assert first.summary["products_matched_or_created"] == 4
    assert {cluster.label for cluster in first.clusters} == {
        "travel cable organizer",
        "hanging toiletry bag",
        "compression packing cube",
        "passport organizer wallet",
    }
    assert len(first.results) == 4
    assert db_session.scalar(select(func.count()).select_from(ProductCandidate)) == 4

    second = service.run_discovery(request, plugin_overrides=[BroadCatalogFixturePlugin()])

    assert second.status == "success"
    assert second.summary["clusters_created"] == 4
    assert second.summary["origins_created"] == 5
    assert db_session.scalar(select(func.count()).select_from(ProductCandidate)) == 4
    assert db_session.scalar(select(func.count()).select_from(CandidateOrigin)) == 10


def test_failed_discovery_keyword_does_not_fail_entire_run(db_session) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    request = DiscoveryRunCreate(
        keywords=[
            DiscoveryKeywordInput(keyword="travel organizer"),
            DiscoveryKeywordInput(keyword="broken keyword"),
        ],
        limit_per_keyword=10,
    )

    run = service.run_discovery(request, plugin_overrides=[BroadCatalogFixturePlugin()])

    assert run.status == "partial_success"
    assert run.summary["keywords_requested"] == 2
    assert run.summary["keywords_succeeded"] == 1
    assert run.summary["results_created"] == 4
    assert any("broken keyword" in error for error in run.summary["errors"])
