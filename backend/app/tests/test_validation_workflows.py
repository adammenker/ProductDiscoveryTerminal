from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.economics.cost_ceiling import calculate_cost_ceiling_v2
from app.models import (
    CostModel,
    MarketSignal,
    MarketSignalType,
    ObservationEntityType,
    PluginRun,
    PluginType,
    ProductCandidate,
    ProductStatus,
    RawObservation,
    RunStatus,
    SupplierQuote,
)
from app.plugins.ingestion.product_opportunity_explorer_manual_csv import (
    ProductOpportunityExplorerManualCsvPlugin,
)
from app.schemas.plugin import IngestionQuery
from app.services.validation_service import ValidationService


def _product(
    db: Session,
    *,
    name: str = "facial ice roller",
    description: str | None = None,
) -> ProductCandidate:
    product = ProductCandidate(
        canonical_name=name,
        category="beauty",
        description=description,
        status=ProductStatus.CANDIDATE,
    )
    db.add(product)
    db.flush()
    db.add(
        MarketSignal(
            product_id=product.id,
            source="manual",
            signal_type=MarketSignalType.PRICE,
            value=29.99,
            unit="USD",
            metadata_={},
        )
    )
    db.commit()
    db.refresh(product)
    return product


def test_cost_ceiling_v2_builds_margin_scenarios_and_sensitivity() -> None:
    result = calculate_cost_ceiling_v2(
        selling_price=29.99,
        amazon_fees=8.25,
        inbound_cost_per_unit=0.75,
        storage_estimate=0.35,
        return_allowance_rate=0.04,
        ad_allowance_rate=0.12,
        supplier_unit_cost=3.2,
        supplier_freight_cost_per_unit=0.7,
        packaging_cost_per_unit=0.4,
    )

    assert [row["target_margin_percent"] for row in result["scenarios"]] == [20, 30, 40, 50]
    assert len(result["sensitivity"]) == 12
    assert result["modeled"]["target_margin_percent"] == 30
    assert result["modeled"]["required_supplier_unit_cost"] is not None
    assert result["modeled"]["decision"] == "quote_at_or_below_ceiling"


def test_cost_ceiling_v2_handles_missing_and_negative_inputs() -> None:
    missing = calculate_cost_ceiling_v2(
        selling_price=None,
        amazon_fees=5,
        inbound_cost_per_unit=1,
        storage_estimate=1,
        return_allowance_rate=0.1,
        ad_allowance_rate=0.1,
    )
    negative = calculate_cost_ceiling_v2(
        selling_price=10,
        amazon_fees=9,
        inbound_cost_per_unit=2,
        storage_estimate=1,
        return_allowance_rate=0.1,
        ad_allowance_rate=0.1,
    )

    assert missing["decision"] == "insufficient_price_data"
    assert negative["modeled"]["decision"] == "invalid_negative_ceiling"


def test_supplier_quote_crud_and_ceiling_validation(client: TestClient, db_session: Session) -> None:
    product = _product(db_session)

    response = client.post(
        f"/products/{product.id}/supplier-quotes",
        json={
            "source": "supplier_alibaba_manual",
            "supplier_name": "Supplier ABC",
            "supplier_url": "https://example.com/supplier",
            "unit_cost": 3.2,
            "freight_cost_per_unit": 0.7,
            "packaging_cost_per_unit": 0.4,
            "moq": 500,
            "lead_time_days": 25,
            "country": "CN",
            "quote_status": "validated",
        },
    )

    assert response.status_code == 201
    quote = response.json()
    assert quote["supplier_landed_cost"] == 4.3
    assert quote["decision"] == "quote_at_or_below_ceiling"
    assert client.get(f"/products/{product.id}/supplier-quotes").json()[0]["moq"] == 500
    detail = client.get(f"/products/{product.id}").json()
    assert detail["economics_validator"]["modeled"]["target_margin_percent"] == 30
    assert detail["supplier_validation"]["viable_quote_count"] == 1
    assert detail["constraint_evaluation"]["eligible"] is True
    assert detail["evidence_matrix"]

    patched = client.patch(
        f"/supplier-quotes/{quote['id']}",
        json={"unit_cost": 50, "quote_status": "needs_review"},
    )
    assert patched.status_code == 200
    assert patched.json()["decision"] == "quote_above_ceiling"
    rescored = client.get(f"/products/{product.id}").json()["latest_score"]
    assert rescored["recommendation"] == "skip"

    deleted = client.delete(f"/supplier-quotes/{quote['id']}")
    assert deleted.status_code == 204


def test_pasted_supplier_quote_parser(client: TestClient, db_session: Session) -> None:
    product = _product(db_session)

    response = client.post(
        "/supplier-quotes/import-text",
        json={
            "product_id": str(product.id),
            "source": "manual_paste",
            "text": "Supplier ABC: $2.80/unit, MOQ 500, freight $0.70/unit, packaging $0.40",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["unit_cost"] == 2.8
    assert body["freight_cost_per_unit"] == 0.7
    assert body["packaging_cost_per_unit"] == 0.4
    assert body["moq"] == 500


def test_old_supplier_quote_is_expired(db_session: Session) -> None:
    product = _product(db_session)
    quote = SupplierQuote(
        product_id=product.id,
        source="manual",
        unit_cost=3,
        quote_date=datetime.now(UTC) - timedelta(days=91),
        quote_status="validated",
    )
    db_session.add(quote)
    db_session.commit()

    row = ValidationService(db_session).supplier_validation(product.id)["quotes"][0]

    assert row["quote_status"] == "expired"
    assert row["age_days"] == 91


def test_battery_product_fails_default_constraints(client: TestClient, db_session: Session) -> None:
    product = _product(
        db_session,
        name="rechargeable facial tool",
        description="Includes a lithium battery and USB charger.",
    )

    response = client.post(f"/products/{product.id}/evaluate-constraints")

    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert any(item["risk_type"] == "battery" for item in body["hard_failures"])
    listed = client.get("/products", params={"eligible": "false"}).json()
    assert any(row["id"] == str(product.id) for row in listed["items"])


def test_constraint_scan_ignores_metadata_and_image_filename_fragments(
    db_session: Session,
) -> None:
    product = _product(db_session, description="A reusable cooling facial roller.")
    now = datetime.now(UTC)
    run = PluginRun(
        plugin_name="amazon_catalog_spapi",
        plugin_type=PluginType.INGESTION,
        status=RunStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        parameters={},
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        RawObservation(
            plugin_run_id=run.id,
            product_id=product.id,
            source="amazon_sp_api",
            source_plugin="amazon_catalog_spapi",
            observed_at=now,
            entity_type=ObservationEntityType.MARKETPLACE_LISTING,
            external_id="B000TEST01",
            title="Unbreakable steel cooling roller",
            metrics={},
            metadata_={"image_url": "https://example.com/611g7kzooil-71zi3h4ugel.jpg"},
            media_urls=[],
            content_hash="metadata-risk-regression",
        )
    )
    db_session.commit()

    result = ValidationService(db_session).evaluate_constraints(product.id, persist=False)

    assert result["eligible"] is True
    assert not any(flag["risk_type"] == "liquid" for flag in result["risk_flags"])


def test_economics_pairs_fees_with_nearest_modeled_price(db_session: Session) -> None:
    product = _product(db_session)
    db_session.add_all(
        [
            CostModel(
                product_id=product.id,
                model_name="amazon_fba_fee_estimate",
                selling_price=5.59,
                marketplace_fee_per_unit=3.46,
                assumptions={
                    "total_amazon_fees": 3.46,
                    "comparable_asin": "B000LOW001",
                },
            ),
            CostModel(
                product_id=product.id,
                model_name="amazon_fba_fee_estimate",
                selling_price=29.99,
                marketplace_fee_per_unit=8.25,
                assumptions={
                    "total_amazon_fees": 8.25,
                    "comparable_asin": "B000MATCH1",
                },
            ),
        ]
    )
    db_session.commit()

    economics = ValidationService(db_session).economics(product.id)

    assert economics["modeled_price"] == 29.99
    assert economics["amazon_fees"] == 8.25
    assert economics["comparable_asin"] == "B000MATCH1"


def test_evidence_matrix_marks_missing_evidence(db_session: Session) -> None:
    product = _product(db_session)

    evidence = ValidationService(db_session).evidence_matrix(product.id)

    assert evidence["cross_source_confidence_score"] < 70
    assert "Need supplier quote" in evidence["missing_evidence"]
    assert {row["area"] for row in evidence["rows"]} >= {
        "Amazon Pricing",
        "Supplier Quotes",
        "Constraint Fit",
    }


def test_snapshot_trade_outcome_and_backtest_metrics(
    client: TestClient,
    db_session: Session,
) -> None:
    product = _product(db_session)
    db_session.add(
        SupplierQuote(
            product_id=product.id,
            source="manual",
            unit_cost=3,
            freight_cost_per_unit=0.5,
            packaging_cost_per_unit=0.4,
            quote_status="validated",
        )
    )
    db_session.commit()

    created = client.post(
        f"/products/{product.id}/snapshots",
        json={
            "snapshot_reason": "test",
            "decision": "paper_pursue",
            "hypothesis": "Economics remain viable.",
        },
    )

    assert created.status_code == 201
    trade = created.json()["paper_trade"]
    frozen_name = created.json()["snapshot"]["canonical_name"]
    product.canonical_name = "changed after snapshot"
    db_session.commit()

    outcome = client.post(
        f"/paper-trades/{trade['id']}/outcomes",
        json={
            "window_days": 30,
            "outcome_label": "improved",
            "outcome_score": 75,
            "price_change": 5,
        },
    )
    assert outcome.status_code == 201

    trades = client.get("/paper-trades").json()
    assert trades[0]["snapshot"]["canonical_name"] == frozen_name
    summary = client.get("/backtests/summary").json()
    assert summary["top_picks_improved_rate"] == 100


def test_manual_poe_csv_import(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "poe.csv"
    path.write_text(
        "niche,search_volume,search_volume_growth,purchase_growth,average_price,"
        "average_review_count,return_rate,top_clicked_asins,notes\n"
        'facial ice roller,12000,18,9,24.99,320,4.2,"B000TEST01,B000TEST02",Promising\n'
    )

    rows = ProductOpportunityExplorerManualCsvPlugin().fetch(
        IngestionQuery(metadata={"file_path": str(path)})
    )

    assert len(rows) == 1
    assert rows[0].source == "amazon_product_opportunity_explorer_manual"
    assert rows[0].metrics["price"] == 24.99
    assert rows[0].metadata["top_clicked_asins"] == ["B000TEST01", "B000TEST02"]
