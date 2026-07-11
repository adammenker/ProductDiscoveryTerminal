from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ComparableAsin,
    CostModel,
    MarketplaceAsinSnapshot,
    ObservationEntityType,
    PluginRun,
    PluginType,
    ProductCandidate,
    ProductStatus,
    RawObservation,
    RunStatus,
)
from app.scoring.v2 import data_readiness_state, ranking_priority_score
from app.services.comparable_service import ComparableService
from app.services.scoring_service import ScoringService
from app.services.validation_service import ValidationService


def test_data_readiness_distinguishes_partial_and_amazon_enriched_evidence() -> None:
    partial = data_readiness_state(
        included_comparables=[{"asin": "B000TEST01"}],
        economics={"modeled_price": 24.99, "fee_source": None},
        supplier_validation={"viable_quote_count": 0},
        derived_signals={"windows": {}},
        direct_demand_available=False,
    )
    enriched = data_readiness_state(
        included_comparables=[{"asin": "B000TEST01"}],
        economics={"modeled_price": 24.99, "fee_source": "amazon_spapi_product_fees"},
        supplier_validation={"viable_quote_count": 0},
        derived_signals={"windows": {}},
        direct_demand_available=False,
    )

    assert partial["state"] == "partially_enriched"
    assert enriched["state"] == "amazon_enriched"


def test_research_priority_is_separate_from_opportunity_score() -> None:
    priority = ranking_priority_score(
        opportunity_score=72.0,
        evidence_confidence_score=40.0,
        readiness_state="catalog_only",
    )

    assert priority["opportunity_score"] == 72.0
    assert priority["score"] == 96.0
    assert priority["uncertainty_bonus"] == 9.0
    assert priority["stage_bonus"] == 15.0


def test_recommendation_v2_keeps_missing_components_nullable(db_session: Session) -> None:
    product = ProductCandidate(
        canonical_name="unknown desk gadget",
        category="office",
        status=ProductStatus.CANDIDATE,
    )
    db_session.add(product)
    db_session.commit()

    score = ScoringService(db_session).score_product(product.id)
    breakdown = score.score_breakdown

    assert breakdown["scoring_version"] == "recommendation_v2"
    assert breakdown["opportunity_score"] is None
    assert breakdown["recommendation"] == "insufficient_data"
    assert breakdown["components"]["competition"]["value"] is None
    assert breakdown["components"]["competition"]["status"] == "missing"
    assert breakdown["components"]["demand_proxy"]["value"] is None
    assert "Missing competition evidence" in breakdown["missing_evidence"]


def test_comparable_relevance_filters_irrelevant_and_price_outlier_asins(
    db_session: Session,
) -> None:
    product = _product(db_session)
    _amazon_observation_set(
        db_session,
        product,
        asin="B000GOOD01",
        title="Facial Ice Roller for Puffy Face",
        product_type="facial ice roller",
        category="beauty",
        price=24.99,
        fees=8.25,
        sales_rank=1200,
    )
    _amazon_observation_set(
        db_session,
        product,
        asin="B000BAD001",
        title="Cable Organizer Bag for Travel Chargers",
        product_type="cable organizer",
        category="electronics",
        price=9.99,
        fees=4.0,
        sales_rank=900,
    )
    _amazon_observation_set(
        db_session,
        product,
        asin="B000GOOD02",
        title="Reusable Facial Ice Roller for Puffy Face",
        product_type="facial ice roller",
        category="beauty",
        price=23.99,
        fees=8.0,
        sales_rank=1400,
    )
    _amazon_observation_set(
        db_session,
        product,
        asin="B000OUT001",
        title="Facial Ice Roller Luxury Clinic Pack",
        product_type="facial ice roller",
        category="beauty",
        price=299.99,
        fees=34.0,
        sales_rank=100,
    )

    rows = ComparableService(db_session).sync_product(product.id)
    statuses = {row.asin: row.relevance_status for row in rows}

    assert statuses["B000GOOD01"] == "included"
    assert statuses["B000BAD001"] == "excluded_wrong_product_type"
    assert statuses["B000OUT001"] == "excluded_price_outlier"

    economics = ValidationService(db_session).economics(product.id)
    assert economics["modeled_price"] == 24.99
    assert economics["comparable_asin"] == "B000GOOD01"


def test_manual_comparable_overrides_persist_and_feed_economics(db_session: Session) -> None:
    product = _product(db_session)
    _amazon_observation_set(
        db_session,
        product,
        asin="B000GOOD01",
        title="Facial Ice Roller for Puffy Face",
        product_type="facial ice roller",
        category="beauty",
        price=24.99,
        fees=8.25,
        sales_rank=1200,
    )
    _amazon_observation_set(
        db_session,
        product,
        asin="B000OUT001",
        title="Facial Ice Roller Luxury Clinic Pack",
        product_type="facial ice roller",
        category="beauty",
        price=299.99,
        fees=34.0,
        sales_rank=100,
    )
    service = ComparableService(db_session)
    service.sync_product(product.id)

    included = service.update_relevance(
        product.id,
        "B000OUT001",
        relevance_status="included",
        reason="Analyst confirms premium pack is relevant.",
    )
    assert included.relevance_status == "manually_included"

    economics = ValidationService(db_session).economics(product.id)
    assert economics["modeled_price"] == 299.99

    excluded = service.update_relevance(
        product.id,
        "B000GOOD01",
        relevance_status="excluded_irrelevant",
        reason="Temporary manual exclusion.",
    )
    assert excluded.relevance_status == "manually_excluded"

    service.sync_product(product.id)
    persisted = db_session.scalar(
        select(ComparableAsin).where(
            ComparableAsin.product_id == product.id,
            ComparableAsin.asin == "B000GOOD01",
        )
    )
    assert persisted is not None
    assert persisted.relevance_status == "manually_excluded"
    assert persisted.manually_overridden is True


def test_snapshot_cohorts_are_idempotent_and_scoring_is_read_only(db_session: Session) -> None:
    product = _product(db_session)
    _amazon_observation_set(
        db_session,
        product,
        asin="B000GOOD01",
        title="Facial Ice Roller for Puffy Face",
        product_type="facial ice roller",
        category="beauty",
        price=24.99,
        fees=8.25,
        sales_rank=1200,
    )

    service = ComparableService(db_session)
    service.sync_product(product.id)
    assert db_session.scalar(select(func.count()).select_from(MarketplaceAsinSnapshot)) == 0

    first = service.create_snapshot_cohort(product.id)
    assert first["snapshots_created"] == 1
    assert db_session.scalar(select(func.count()).select_from(MarketplaceAsinSnapshot)) == 1

    retry = service.create_snapshot_cohort(product.id)
    assert retry["snapshot_cohort_id"] == first["snapshot_cohort_id"]
    assert retry["snapshots_created"] == 0

    ScoringService(db_session).score_product(product.id)
    assert db_session.scalar(select(func.count()).select_from(MarketplaceAsinSnapshot)) == 1

    _amazon_observation_set(
        db_session,
        product,
        asin="B000GOOD01",
        title="Facial Ice Roller for Puffy Face",
        product_type="facial ice roller",
        category="beauty",
        price=26.99,
        fees=8.75,
        sales_rank=900,
        content_suffix="-refresh-2",
    )
    service.sync_product(product.id)
    second = service.create_snapshot_cohort(product.id)
    assert second["snapshot_cohort_id"] != first["snapshot_cohort_id"]
    assert second["snapshots_created"] == 1


def test_catalog_refresh_does_not_refresh_carried_forward_price(db_session: Session) -> None:
    product = _product(db_session)
    _amazon_observation_set(
        db_session,
        product,
        asin="B000GOOD01",
        title="Facial Ice Roller for Puffy Face",
        product_type="facial ice roller",
        category="beauty",
        price=24.99,
        fees=8.25,
        sales_rank=1200,
    )
    service = ComparableService(db_session)
    comparable = service.sync_product(product.id)[0]
    first = service.create_snapshot_cohort(product.id)
    first_snapshot = db_session.scalar(
        select(MarketplaceAsinSnapshot).where(
            MarketplaceAsinSnapshot.snapshot_cohort_id == first["snapshot_cohort_id"]
        )
    )
    assert first_snapshot is not None
    original_price_at = first_snapshot.price_observed_at

    refreshed_at = datetime.now(UTC) + timedelta(days=6)
    run = _run(db_session)
    db_session.add(
        RawObservation(
            plugin_run_id=run.id,
            product_id=product.id,
            source="amazon_sp_api",
            source_plugin="amazon_catalog_spapi",
            observed_at=refreshed_at,
            entity_type=ObservationEntityType.MARKETPLACE_LISTING,
            external_id="B000GOOD01",
            title="Facial Ice Roller for Puffy Face",
            metrics={"bestseller_rank": 900},
            metadata_={
                "evidence_type": "amazon_catalog",
                "asin": "B000GOOD01",
                "title": "Facial Ice Roller for Puffy Face",
                "product_type": "facial ice roller",
                "category": "beauty",
            },
            media_urls=[],
            content_hash="B000GOOD01-catalog-only-refresh",
        )
    )
    db_session.commit()

    comparable = service.sync_product(product.id)[0]
    second = service.create_snapshot_cohort(product.id)
    second_snapshot = db_session.scalar(
        select(MarketplaceAsinSnapshot).where(
            MarketplaceAsinSnapshot.snapshot_cohort_id == second["snapshot_cohort_id"]
        )
    )
    assert second_snapshot is not None
    assert comparable.catalog_observed_at is not None
    assert comparable.rank_observed_at is not None
    assert comparable.catalog_observed_at.replace(tzinfo=UTC) == refreshed_at
    assert comparable.rank_observed_at.replace(tzinfo=UTC) == refreshed_at
    assert comparable.price_observed_at == original_price_at
    assert second_snapshot.price == 24.99
    assert second_snapshot.price_observed_at == original_price_at
    assert second_snapshot.catalog_observed_at is not None
    assert second_snapshot.catalog_observed_at.replace(tzinfo=UTC) == refreshed_at

    signal = service.derived_signals(product.id)["windows"]["7d"]
    assert signal["matched_asin_change"]["price"]["absolute_change"] is None
    assert signal["matched_asin_change"]["price"]["fresh_measurement"] is False


def _product(db_session: Session) -> ProductCandidate:
    product = ProductCandidate(
        canonical_name="facial ice roller",
        category="beauty",
        status=ProductStatus.CANDIDATE,
    )
    db_session.add(product)
    db_session.commit()
    return product


def _run(db_session: Session) -> PluginRun:
    now = datetime.now(UTC)
    run = PluginRun(
        plugin_name="fixture",
        plugin_type=PluginType.INGESTION,
        status=RunStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        parameters={},
    )
    db_session.add(run)
    db_session.flush()
    return run


def _amazon_observation_set(
    db_session: Session,
    product: ProductCandidate,
    *,
    asin: str,
    title: str,
    product_type: str,
    category: str,
    price: float,
    fees: float,
    sales_rank: int,
    content_suffix: str = "",
) -> None:
    run = _run(db_session)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            RawObservation(
                plugin_run_id=run.id,
                product_id=product.id,
                source="amazon_sp_api",
                source_plugin="amazon_catalog_spapi",
                observed_at=now,
                entity_type=ObservationEntityType.MARKETPLACE_LISTING,
                external_id=asin,
                title=title,
                metrics={"bestseller_rank": sales_rank, "sales_rank": sales_rank},
                metadata_={
                    "evidence_type": "amazon_catalog",
                    "asin": asin,
                    "title": title,
                    "brand": title.split()[0],
                    "product_type": product_type,
                    "category": category,
                },
                media_urls=[],
                content_hash=f"{asin}-catalog{content_suffix}",
            ),
            RawObservation(
                plugin_run_id=run.id,
                product_id=product.id,
                source="amazon_sp_api",
                source_plugin="amazon_pricing_spapi",
                observed_at=now,
                entity_type=ObservationEntityType.MARKETPLACE_LISTING,
                external_id=f"{asin}:pricing",
                title=f"Amazon pricing for {asin}",
                metrics={"price": price, "seller_count": 12, "offer_count": 12},
                metadata_={"evidence_type": "amazon_pricing", "asin": asin, "currency": "USD"},
                media_urls=[],
                content_hash=f"{asin}-pricing{content_suffix}",
            ),
        ]
    )
    db_session.add(
        CostModel(
            product_id=product.id,
            model_name="amazon_fba_fee_estimate",
            selling_price=price,
            marketplace_fee_per_unit=fees,
            fulfillment_cost_per_unit=0,
            currency="USD",
            assumptions={
                "total_amazon_fees": fees,
                "fee_estimate_source": "amazon_spapi_product_fees",
                "comparable_asin": asin,
            },
        )
    )
    db_session.commit()
