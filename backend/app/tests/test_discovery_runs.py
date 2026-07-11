from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import CandidateOrigin, ProductCandidate
from app.schemas.discovery import DiscoveryKeywordInput, DiscoveryRunCreate
from app.schemas.plugin import IngestionQuery, PipelineRunResponse, RawObservationDTO
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
    assert first.summary["candidates_created"] == 4
    assert first.summary["candidates_matched"] == 0
    assert first.summary["enrichment_state"] == "preliminary_scored"
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
    assert second.summary["candidates_created"] == 0
    assert second.summary["candidates_matched"] == 4
    assert db_session.scalar(select(func.count()).select_from(ProductCandidate)) == 4
    assert db_session.scalar(select(func.count()).select_from(CandidateOrigin)) == 10
    assert [row.id for row in service.list_runs(limit=2)] == [second.id, first.id]


def test_discovery_enriches_only_top_n_candidates(db_session) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    calls: list[str] = []

    class FakeRefreshPipeline:
        def __init__(self, db) -> None:  # type: ignore[no-untyped-def]
            self.db = db

        def run_product(self, product_id) -> PipelineRunResponse:  # type: ignore[no-untyped-def]
            calls.append(str(product_id))
            return PipelineRunResponse(
                status="success",
                plugin_runs=[],
                products_updated=1,
                scores_updated=1,
                observations_created=3,
                errors=[],
            )

    request = DiscoveryRunCreate(
        keywords=[DiscoveryKeywordInput(keyword="travel organizer")],
        limit_per_keyword=10,
        enrich_top_n=2,
        min_cluster_confidence=0.60,
    )

    run = service.run_discovery(
        request,
        plugin_overrides=[BroadCatalogFixturePlugin()],
        refresh_pipeline_factory=FakeRefreshPipeline,  # type: ignore[arg-type]
    )

    assert run.status == "success"
    assert len(calls) == 2
    assert run.summary["enrichment_top_n"] == 2
    assert run.summary["enrichment_candidates"] == 2
    assert run.summary["enrichment_requested"] == 2
    assert run.summary["enriched_candidates"] == 2
    assert run.summary["enrichment_failed"] == 0
    assert run.summary["enrichment_observations_created"] == 6
    assert run.summary["enrichment_state"] == "enriched"


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
    assert run.summary["keywords_failed"] == 1
    assert run.summary["results_created"] == 4
    assert any("broken keyword" in error for error in run.summary["errors"])
