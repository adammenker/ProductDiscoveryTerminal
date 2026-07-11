from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    ComparableAsin,
    MarketplaceAsinSnapshot,
    ObservationEntityType,
    ProductCandidate,
    ProductStatus,
)
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.plugins.ingestion.amazon_catalog_spapi.plugin import _catalog_observation
from app.plugins.ingestion.amazon_pricing_spapi.plugin import _pricing_observation
from app.schemas.plugin import IngestionQuery, RawObservationDTO
from app.scoring.config import RECOMMENDATION_V2_WEIGHTS
from app.scoring.v2 import build_recommendation_v2
from app.services.comparable_service import ComparableService
from app.services.product_service import ProductService


def test_offer_count_is_not_copied_into_seller_count() -> None:
    observation = _pricing_observation(
        asin="B000TEST01",
        payload={
            "payload": [
                {
                    "ASIN": "B000TEST01",
                    "Product": {
                        "CompetitivePricing": {
                            "CompetitivePrices": [
                                {
                                    "CompetitivePriceId": "1",
                                    "Price": {"ListingPrice": {"Amount": 19.99, "CurrencyCode": "USD"}},
                                }
                            ],
                            "NumberOfOfferListings": [{"Count": 7}],
                        }
                    },
                }
            ]
        },
        observed_at=datetime.now(UTC),
        marketplace_id="ATVPDKIKX0DER",
        environment="production",
        store_raw_payloads=False,
    )

    assert observation.metrics["offer_count"] == 7
    assert observation.metrics["seller_count"] is None
    assert observation.metadata["raw_payload_stored"] is False


def test_seed_category_does_not_replace_amazon_category() -> None:
    observation = _catalog_observation(
        item={
            "asin": "B000TEST02",
            "summaries": [
                {
                    "itemName": "Compact Camping Cookware Pot",
                    "brand": "TrailCo",
                    "productType": "COOKWARE",
                    "browseClassification": {
                        "displayName": "Open Fire Cookware",
                        "classificationId": "123",
                    },
                }
            ],
        },
        query=IngestionQuery(query="camping cookware pot", category="camping gear"),
        observed_at=datetime.now(UTC),
        index=0,
        marketplace_id="ATVPDKIKX0DER",
        environment="production",
        store_raw_payloads=False,
    )

    assert observation.metadata["seed_category"] == "camping gear"
    assert observation.metadata["amazon_category"] == "Open Fire Cookware"
    assert observation.metadata["category"] == "Open Fire Cookware"
    assert observation.metadata["raw_payload_stored"] is False


def test_mixed_bsr_categories_are_conflicting() -> None:
    result = build_recommendation_v2(
        product_name="camping cookware pot",
        observations=[],
        market_signals=[],
        cost_models=[],
        insights=[],
        economics={"modeled_price": 25.0, "amazon_fees": 8.0, "fee_source": "amazon_spapi_product_fees", "modeled": {"max_landed_cost": 4.0}},
        supplier_validation={"viable_quote_count": 0},
        constraint_evaluation={"eligible": True, "evaluation_status": "completed", "risk_flags": []},
        evidence={"missing_evidence": []},
        comparable_rows=[
            _comparable_dict("B000AAA111", 25.0, 100, "Open Fire Cookware"),
            _comparable_dict("B000BBB222", 26.0, 120, "Camp Kitchen"),
        ],
        derived_signals={"windows": {}},
    )

    demand = result["components"]["demand_proxy"]
    assert demand["status"] == "conflicting"
    assert demand["value"] is None
    assert "BSR evidence spans incompatible rank categories." in demand["warnings"]


def test_data_quality_is_not_an_opportunity_weight() -> None:
    assert "data_quality" not in RECOMMENDATION_V2_WEIGHTS


def test_historical_trends_use_matched_asins_and_report_churn(db_session: Session) -> None:
    product = ProductCandidate(
        canonical_name="camping cookware pot",
        category="cookware",
        status=ProductStatus.CANDIDATE,
    )
    db_session.add(product)
    db_session.commit()

    comparable_a = _comparable(db_session, product, "B000AAA111")
    comparable_b = _comparable(db_session, product, "B000BBB222")
    comparable_c = _comparable(db_session, product, "B000CCC333")
    comparable_d = _comparable(db_session, product, "B000DDD444")
    start_cohort = uuid.uuid4()
    end_cohort = uuid.uuid4()
    start_at = datetime.now(UTC) - timedelta(days=29)
    end_at = datetime.now(UTC)
    db_session.add_all(
        [
            _snapshot(product, comparable_a, start_cohort, start_at, price=10, offer_count=4),
            _snapshot(product, comparable_b, start_cohort, start_at, price=100, offer_count=8),
            _snapshot(product, comparable_d, start_cohort, start_at, price=50, offer_count=6),
            _snapshot(product, comparable_a, end_cohort, end_at, price=12, offer_count=5),
            _snapshot(product, comparable_b, end_cohort, end_at, price=110, offer_count=9),
            _snapshot(product, comparable_c, end_cohort, end_at, price=200, offer_count=9),
        ]
    )
    db_session.commit()

    signal = ComparableService(db_session).derived_signals(product.id)["windows"]["30d"]

    assert signal["status"] == "measured"
    assert signal["matched_asin_change"]["matched_asin_count"] == 2
    assert signal["matched_asin_change"]["price"]["absolute_change"] == 6.0
    assert signal["cohort_change"]["price"]["absolute_change"] != 6.0
    assert signal["comparable_churn"]["added_asin_count"] == 1
    assert signal["comparable_churn"]["removed_asin_count"] == 1


def test_fixture_amazon_research_flow_creates_one_snapshot_cohort(
    db_session: Session,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    product = ProductCandidate(
        canonical_name="camping cookware pot",
        category="cookware",
        status=ProductStatus.CANDIDATE,
    )
    db_session.add(product)
    db_session.commit()

    plugins = {
        "amazon_catalog_spapi": _CatalogFixture(),
        "amazon_pricing_spapi": _PricingFixture(),
        "amazon_fees_spapi": _FeesFixture(),
    }
    monkeypatch.setattr(
        "app.pipeline.runner.get_ingestion_plugins",
        lambda names=None: [plugins[name] for name in (names or []) if name in plugins],
    )

    result = AmazonRefreshPipeline(db_session).run_product(product.id)
    detail = ProductService(db_session).get_detail(product.id)
    cohort_ids = {
        row.snapshot_cohort_id
        for row in db_session.query(MarketplaceAsinSnapshot).all()
    }

    assert result.status == "success"
    assert result.observations_created == 6
    assert len(cohort_ids) == 1
    assert len(detail["effective_comparables"]) == 2
    assert detail["recommendation_v2"]["scoring_version"] == "recommendation_v2"
    assert detail["economics_validator"]["fee_provenance"]["status"] == "live_spapi"


def _comparable_dict(asin: str, price: float, bsr: int, rank_category: str) -> dict:
    return {
        "asin": asin,
        "price": price,
        "brand": asin,
        "relevance_score": 80,
        "relevance_status": "included",
        "metadata": {
            "bestseller_rank": bsr,
            "rank_category": rank_category,
            "offer_count": 4,
        },
    }


def _comparable(db_session: Session, product: ProductCandidate, asin: str) -> ComparableAsin:
    row = ComparableAsin(
        product_id=product.id,
        asin=asin,
        title=f"{asin} camping cookware",
        relevance_score=80,
        relevance_status="included",
        relevance_reasons=[],
        automatic_relevance_version="test",
        manually_overridden=False,
        discovered_at=datetime.now(UTC),
        last_refreshed_at=datetime.now(UTC),
        metadata_={},
    )
    db_session.add(row)
    db_session.flush()
    return row


def _snapshot(
    product: ProductCandidate,
    comparable: ComparableAsin,
    cohort_id: uuid.UUID,
    observed_at: datetime,
    *,
    price: float,
    offer_count: float,
) -> MarketplaceAsinSnapshot:
    return MarketplaceAsinSnapshot(
        product_id=product.id,
        comparable_asin_id=comparable.id,
        snapshot_cohort_id=cohort_id,
        observation_fingerprint=f"{cohort_id}:{comparable.asin}",
        asin=comparable.asin,
        observed_at=observed_at,
        price=price,
        featured_offer_price=price,
        offer_count=offer_count,
        source_observation_ids=[],
        metadata_={},
    )


class _CatalogFixture:
    name = "amazon_catalog_spapi"
    version = "fixture"
    manifest = {"name": name, "type": "ingestion"}

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        now = datetime.now(UTC)
        return [
            _dto(
                now,
                asin="B000POT001",
                title="Compact Camping Cookware Pot Set",
                metrics={"bestseller_rank": 500},
                metadata={
                    "evidence_type": "amazon_catalog",
                    "asin": "B000POT001",
                    "title": "Compact Camping Cookware Pot Set",
                    "brand": "TrailCo",
                    "amazon_category": "Pots, Pans & Griddles",
                    "amazon_product_type": "camping cookware pot",
                    "rank_category": "Open Fire Cookware",
                    "product_name": query.query,
                },
            ),
            _dto(
                now,
                asin="B000POT002",
                title="Lightweight Camping Cookware Pot with Lid",
                metrics={"bestseller_rank": 750},
                metadata={
                    "evidence_type": "amazon_catalog",
                    "asin": "B000POT002",
                    "title": "Lightweight Camping Cookware Pot with Lid",
                    "brand": "Campware",
                    "amazon_category": "Pots, Pans & Griddles",
                    "amazon_product_type": "camping cookware pot",
                    "rank_category": "Open Fire Cookware",
                    "product_name": query.query,
                },
            ),
        ]


class _PricingFixture:
    name = "amazon_pricing_spapi"
    version = "fixture"
    manifest = {"name": name, "type": "ingestion"}

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        now = datetime.now(UTC)
        prices = {"B000POT001": 24.99, "B000POT002": 27.99}
        return [
            _dto(
                now,
                asin=asin,
                external_id=f"{asin}:pricing",
                title=f"Amazon pricing for {asin}",
                metrics={
                    "price": price,
                    "featured_offer_price": price,
                    "offer_count": 4,
                    "seller_count": None,
                },
                metadata={"evidence_type": "amazon_pricing", "asin": asin, "currency": "USD"},
            )
            for asin, price in prices.items()
            if asin in set(query.metadata.get("asins") or [])
        ]


class _FeesFixture:
    name = "amazon_fees_spapi"
    version = "fixture"
    manifest = {"name": name, "type": "ingestion"}

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        now = datetime.now(UTC)
        rows = []
        for item in query.metadata.get("asins") or []:
            asin = item["asin"]
            price = float(item["modeled_price"])
            fee = 8.25 if asin == "B000POT001" else 9.25
            rows.append(
                _dto(
                    now,
                    asin=asin,
                    external_id=f"{asin}:fees:{price:.2f}",
                    title=f"Amazon fee estimate for {asin}",
                    metrics={
                        "selling_price": price,
                        "total_amazon_fees": fee,
                        "referral_fee_per_unit": round(price * 0.15, 2),
                        "fulfillment_fee_per_unit": round(fee - price * 0.15, 2),
                    },
                    metadata={
                        "evidence_type": "amazon_fees",
                        "asin": asin,
                        "comparable_asin": asin,
                        "fee_estimate_source": "amazon_spapi_product_fees",
                        "fee_source": "amazon_product_fees",
                        "status": "live_spapi",
                        "confidence": "high",
                        "modeled_price_source": "amazon_pricing",
                        "currency": "USD",
                    },
                )
            )
        return rows


def _dto(
    observed_at: datetime,
    *,
    asin: str,
    title: str,
    metrics: dict,
    metadata: dict,
    external_id: str | None = None,
) -> RawObservationDTO:
    return RawObservationDTO(
        source="amazon_sp_api",
        source_plugin=str(metadata["evidence_type"]).replace("amazon_", "amazon_") + "_spapi",
        observed_at=observed_at,
        entity_type=ObservationEntityType.MARKETPLACE_LISTING.value,
        external_id=external_id or asin,
        title=title,
        url=f"https://www.amazon.com/dp/{asin}",
        metrics=metrics,
        metadata=metadata,
    )
