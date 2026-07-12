from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import CandidateOrigin, ProductCandidate
from app.schemas.discovery import DiscoveryKeywordInput, DiscoveryRunCreate
from app.schemas.plugin import IngestionQuery, PipelineRunResponse, RawObservationDTO
from app.services.discovery_service import DiscoveryService, _opportunity_group


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


class EmptyCatalogFixturePlugin:
    name = "amazon_catalog_spapi"
    version = "test"
    manifest = {"type": "ingestion"}

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        return []


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
    assert all(result.metadata_["data_readiness_state"] for result in first.results)
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


def test_empty_discovery_run_is_not_marked_success(db_session) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    request = DiscoveryRunCreate(
        keywords=[DiscoveryKeywordInput(keyword="unknown product concept")],
        limit_per_keyword=10,
    )

    run = service.run_discovery(request, plugin_overrides=[EmptyCatalogFixturePlugin()])

    assert run.status == "failed"
    assert run.summary["keywords_succeeded"] == 0
    assert run.summary["results_created"] == 0


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


def test_discovery_run_can_be_queued_and_processed_later(db_session) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    request = DiscoveryRunCreate(
        keywords=[DiscoveryKeywordInput(keyword="travel organizer")],
        limit_per_keyword=10,
    )

    queued = service.enqueue_discovery(request)

    assert queued.status == "queued"
    assert queued.summary["progress_stage"] == "queued"
    assert queued.summary["progress_percent"] == 0
    assert queued.summary["keywords_requested"] == 1

    processed = service.process_queued_run(
        queued.id,
        plugin_overrides=[BroadCatalogFixturePlugin()],
    )

    assert processed.status == "success"
    assert processed.summary["progress_stage"] == "completed"
    assert processed.summary["progress_percent"] == 100
    assert processed.summary["results_created"] == 4


def test_discovery_worker_does_not_process_an_already_claimed_run(db_session) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    queued = service.enqueue_discovery(
        DiscoveryRunCreate(
            keywords=[DiscoveryKeywordInput(keyword="travel organizer")],
            limit_per_keyword=10,
        )
    )
    queued.status = "running"
    db_session.commit()

    class UnexpectedPlugin(BroadCatalogFixturePlugin):
        def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
            raise AssertionError("already-claimed run was executed twice")

    result = service.process_queued_run(queued.id, plugin_overrides=[UnexpectedPlugin()])

    assert result.status == "running"


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


def test_discovery_api_separates_run_summaries_from_details(db_session, client) -> None:  # type: ignore[no-untyped-def]
    run = DiscoveryService(db_session).run_discovery(
        DiscoveryRunCreate(
            keywords=[DiscoveryKeywordInput(keyword="travel organizer")],
            limit_per_keyword=10,
        ),
        plugin_overrides=[BroadCatalogFixturePlugin()],
    )

    summaries = client.get("/discovery/runs", params={"limit": 10})
    detail = client.get(f"/discovery/runs/{run.id}")

    assert summaries.status_code == 200
    summary = next(item for item in summaries.json() if item["id"] == str(run.id))
    assert summary["clusters"] == []
    assert summary["results"] == []
    assert summary["origins"] == []
    assert detail.status_code == 200
    assert len(detail.json()["clusters"]) == 4
    assert len(detail.json()["results"]) == 4
    assert len(detail.json()["origins"]) == 5


def test_listing_variants_collapse_into_one_ranked_opportunity(db_session) -> None:  # type: ignore[no-untyped-def]
    class TowelWarmerFixturePlugin:
        name = "amazon_catalog_spapi"
        version = "test"
        manifest = {"type": "ingestion"}

        def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
            titles = [
                ("B000TOWEL1", "Pureclean Towel Warmer"),
                ("B000TOWEL2", "Powsaf Towel Warmer"),
                ("B000TOWEL3", "Keenray Bucket Towel"),
                ("B000TOWEL4", "Sameat Heated Towel"),
                ("B000TOWEL5", "Flyhit Towel Warmer"),
            ]
            return [
                RawObservationDTO(
                    source="amazon_sp_api",
                    source_plugin=self.name,
                    observed_at=datetime.now(UTC),
                    entity_type="marketplace_listing",
                    external_id=asin,
                    title=title,
                    metrics={},
                    metadata={"asin": asin, "title": title, "source_query": query.query},
                )
                for asin, title in titles
            ]

    run = DiscoveryService(db_session).run_discovery(
        DiscoveryRunCreate(
            keywords=[DiscoveryKeywordInput(keyword="towel warmer")],
            limit_per_keyword=10,
        ),
        plugin_overrides=[TowelWarmerFixturePlugin()],
    )

    assert len(run.results) == 5
    assert run.summary["opportunity_groups_created"] == 1
    assert run.summary["variants_collapsed"] == 4
    representatives = [
        result
        for result in run.results
        if result.metadata_["is_opportunity_representative"]
    ]
    assert len(representatives) == 1
    assert representatives[0].rank_position == 1
    assert representatives[0].metadata_["opportunity_group_member_count"] == 5
    assert all(result.metadata_["opportunity_group_key"] == "towel-warmer" for result in run.results)


def test_opportunity_grouping_normalizes_variants_but_preserves_accessories() -> None:
    assert _opportunity_group("Acme Black Towel Warmers 2pk", "towel warmer") == (
        "towel warmer",
        "towel-warmer",
    )
    accessory_label, accessory_key = _opportunity_group(
        "Acme Towel Warmer Replacement Cover",
        "towel warmer",
    )
    assert accessory_label != "towel warmer"
    assert accessory_key != "towel-warmer"
