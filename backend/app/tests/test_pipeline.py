from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CostModel,
    MarketSignal,
    ObservationEntityType,
    ProductAlias,
    ProductCandidate,
    ProductInsight,
    ProductStatus,
    PluginRun,
    PluginType,
    RawObservation,
    RunStatus,
)
from app.pipeline.analyzer_runner import AnalyzerRunner
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import IngestionQuery, PipelineRunRequest, RawObservationDTO


def test_pipeline_happy_path_and_observation_deduplication(db_session: Session) -> None:
    runner = PipelineRunner(db_session)

    plugins = [
        "manual_csv",
        "amazon_mock",
        "alibaba_mock",
        "reddit_mock",
        "google_trends_mock",
    ]
    first = runner.run(PipelineRunRequest(plugins=plugins))
    second = runner.run(PipelineRunRequest(plugins=plugins))

    assert first.status == "success"
    assert first.observations_created == 22
    assert first.products_updated == 7
    assert first.scores_updated == 7
    assert second.status == "success"
    assert second.observations_created == 0
    assert second.products_updated == 0
    assert second.scores_updated == 0
    assert "etsy_api" not in {run.plugin_name for run in first.plugin_runs}
    assert "alibaba_open_api" not in {run.plugin_name for run in first.plugin_runs}


def test_pipeline_captures_plugin_failure(db_session: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class BrokenPlugin:
        name = "broken_mock"
        version = "0.1.0"
        manifest = {"name": name, "type": "ingestion", "description": "Broken plugin"}

        def fetch(self, query: IngestionQuery):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    monkeypatch.setattr("app.pipeline.runner.get_ingestion_plugins", lambda names=None: [BrokenPlugin()])

    result = PipelineRunner(db_session).run(PipelineRunRequest(plugins=["broken_mock"]))

    assert result.status == "failed"
    assert result.plugin_runs[0].status == "failed"
    assert "boom" in result.errors[0]


def test_pipeline_surfaces_partial_ingestion_and_strips_transient_errors(
    db_session: Session,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    class PartialPlugin:
        name = "partial_mock"
        version = "0.1.0"
        manifest = {"name": name, "type": "ingestion", "description": "Partial plugin"}

        def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
            return [
                RawObservationDTO(
                    source="test",
                    source_plugin=self.name,
                    observed_at=datetime.now(UTC),
                    entity_type="marketplace_listing",
                    external_id="B000TEST01",
                    title="Test product",
                    metadata={
                        "request_errors": [
                            {"asin": "B000FAIL02", "error": "HTTP 429"}
                        ]
                    },
                )
            ]

    monkeypatch.setattr(
        "app.pipeline.runner.get_ingestion_plugins",
        lambda names=None: [PartialPlugin()],
    )

    result = PipelineRunner(db_session).run(
        PipelineRunRequest(
            plugins=["partial_mock"],
            run_analyzers=False,
            score=False,
        )
    )

    assert result.status == "partial_success"
    assert result.plugin_runs[0].status == "partial_success"
    assert result.errors == ["partial_mock: B000FAIL02: HTTP 429"]
    observation = db_session.query(RawObservation).one()
    assert "request_errors" not in observation.metadata_


def test_pipeline_attaches_targeted_observations_to_selected_product(
    db_session: Session,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    product = ProductCandidate(
        canonical_name="silicone sink strainer",
        category="kitchen",
        status=ProductStatus.CANDIDATE,
    )
    db_session.add(product)
    db_session.commit()

    class TargetedPlugin:
        name = "targeted_mock"
        version = "0.1.0"
        manifest = {"name": name, "type": "ingestion", "description": "Targeted plugin"}

        def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
            return [
                RawObservationDTO(
                    source="amazon_sp_api",
                    source_plugin=self.name,
                    observed_at=datetime.now(UTC),
                    entity_type="marketplace_listing",
                    external_id="B000TARGET",
                    title="OXO Good Grips Silicone Sink Drain Strainer",
                    metadata={
                        "product_name": "silicone sink strainer",
                        "asin": "B000TARGET",
                        "category": "kitchen",
                    },
                ),
                RawObservationDTO(
                    source="amazon_sp_api",
                    source_plugin=self.name,
                    observed_at=datetime.now(UTC),
                    entity_type="marketplace_listing",
                    external_id="B000TARGET:pricing",
                    title="Amazon pricing for B000TARGET",
                    metadata={"asin": "B000TARGET"},
                )
            ]

    monkeypatch.setattr(
        "app.pipeline.runner.get_ingestion_plugins",
        lambda names=None: [TargetedPlugin()],
    )

    result = PipelineRunner(db_session).run(
        PipelineRunRequest(
            plugins=["targeted_mock"],
            query=IngestionQuery(
                query=product.canonical_name,
                category=product.category,
                metadata={"product_id": str(product.id)},
            ),
            run_analyzers=False,
            score=False,
        )
    )

    observations = db_session.scalars(select(RawObservation)).all()
    aliases = db_session.scalars(select(ProductAlias.alias)).all()

    assert result.status == "success"
    assert result.products_updated == 1
    assert len(observations) == 2
    assert {observation.product_id for observation in observations} == {product.id}
    assert aliases == ["silicone sink strainer"]
    assert db_session.scalar(select(func.count()).select_from(ProductCandidate)) == 1


def test_amazon_refresh_reuses_fresh_fee_estimates(db_session: Session) -> None:
    product = ProductCandidate(
        canonical_name="silicone sink strainer",
        category="kitchen",
        status=ProductStatus.CANDIDATE,
    )
    now = datetime.now(UTC)
    run = PluginRun(
        plugin_name="amazon_pricing_spapi",
        plugin_type=PluginType.INGESTION,
        status=RunStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        parameters={},
    )
    db_session.add_all([product, run])
    db_session.flush()
    db_session.add_all(
        [
            RawObservation(
                plugin_run_id=run.id,
                product_id=product.id,
                source="amazon_sp_api",
                source_plugin="amazon_pricing_spapi",
                observed_at=now,
                entity_type=ObservationEntityType.MARKETPLACE_LISTING,
                external_id="B000TEST01:pricing",
                title="Amazon pricing for B000TEST01",
                metrics={"price": 11.99},
                metadata_={"asin": "B000TEST01"},
                media_urls=[],
                content_hash="pricing-b000test01",
            ),
            RawObservation(
                plugin_run_id=run.id,
                product_id=product.id,
                source="amazon_sp_api",
                source_plugin="amazon_pricing_spapi",
                observed_at=now,
                entity_type=ObservationEntityType.MARKETPLACE_LISTING,
                external_id="B000TEST02:pricing",
                title="Amazon pricing for B000TEST02",
                metrics={"price": 12.99},
                metadata_={"asin": "B000TEST02"},
                media_urls=[],
                content_hash="pricing-b000test02",
            ),
            RawObservation(
                plugin_run_id=run.id,
                product_id=product.id,
                source="amazon_sp_api",
                source_plugin="amazon_fees_spapi",
                observed_at=now,
                entity_type=ObservationEntityType.MARKETPLACE_LISTING,
                external_id="B000TEST01:fees:11.99",
                title="Amazon fee estimate for B000TEST01",
                metrics={"selling_price": 11.99, "total_amazon_fees": 5.50},
                metadata_={"asin": "B000TEST01"},
                media_urls=[],
                content_hash="fees-b000test01",
            ),
        ]
    )
    db_session.commit()

    pipeline = AmazonRefreshPipeline(db_session)
    pipeline.settings.amazon_refresh_fee_limit = 5
    pipeline.settings.amazon_fees_cache_ttl_hours = 24

    assert pipeline._fee_inputs(product.id, ["B000TEST01", "B000TEST02"]) == [
        {"asin": "B000TEST02", "modeled_price": 12.99}
    ]


def test_analyzer_refresh_replaces_derived_snapshot(db_session: Session) -> None:
    PipelineRunner(db_session).run(PipelineRunRequest(plugins=["amazon_mock"]))
    observation = db_session.scalar(select(RawObservation).limit(1))
    assert observation is not None
    product = observation.product
    assert product is not None

    def counts() -> tuple[int, int, int]:
        return (
            db_session.scalar(
                select(func.count()).select_from(MarketSignal).where(
                    MarketSignal.product_id == product.id
                )
            )
            or 0,
            db_session.scalar(
                select(func.count()).select_from(CostModel).where(
                    CostModel.product_id == product.id
                )
            )
            or 0,
            db_session.scalar(
                select(func.count()).select_from(ProductInsight).where(
                    ProductInsight.product_id == product.id
                )
            )
            or 0,
        )

    before = counts()
    AnalyzerRunner(db_session).run([product.id])
    after = counts()

    assert before == after
