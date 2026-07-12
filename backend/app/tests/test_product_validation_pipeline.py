from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    ComparableAsin,
    OpportunityScore,
    ProductCandidate,
    ProductStatus,
    Recommendation,
)


def _scored_product(db: Session) -> tuple[ProductCandidate, OpportunityScore]:
    product = ProductCandidate(
        canonical_name="silicone camping bowl",
        category="camping cookware",
        status=ProductStatus.CANDIDATE,
    )
    db.add(product)
    db.flush()
    score = OpportunityScore(
        product_id=product.id,
        scoring_version="recommendation_v2",
        demand_score=72,
        growth_score=50,
        competition_score=74,
        margin_score=80,
        pain_point_score=60,
        risk_score=10,
        confidence_score=75,
        final_score=81,
        recommendation=Recommendation.INVESTIGATE,
        explanation="Promising validation candidate.",
        score_breakdown={"data_readiness_score": 70, "ranking_priority_score": 84},
        created_at=datetime.now(UTC),
    )
    db.add(score)
    for index in range(3):
        db.add(
            ComparableAsin(
                product_id=product.id,
                asin=f"B000TEST0{index}",
                title=f"Comparable {index}",
                price=29.99,
                relevance_score=90,
                relevance_status="included",
                relevance_reasons=["test"],
                automatic_relevance_version="test_v1",
                discovered_at=datetime.now(UTC),
                last_refreshed_at=datetime.now(UTC),
                catalog_observed_at=datetime.now(UTC),
                price_observed_at=datetime.now(UTC),
                metadata_={},
            )
        )
    db.commit()
    return product, score


def test_project_creation_is_idempotent_and_packet_is_immutable(
    client: TestClient, db_session: Session
) -> None:
    product, score = _scored_product(db_session)
    payload = {"product_id": str(product.id), "recommendation_snapshot_id": str(score.id)}

    first = client.post("/validation-projects", json=payload)
    second = client.post("/validation-projects", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["marketplace_packets"][0]["version"] == 1
    project_id = first.json()["id"]
    rfq_one = client.post(f"/validation-projects/{project_id}/rfqs/generate")
    rfq_two = client.patch(
        f"/validation-projects/{project_id}/rfqs/{rfq_one.json()['id']}",
        json={"title": "Revised camping bowl RFQ"},
    )
    assert rfq_one.status_code == 201
    assert rfq_two.status_code == 201
    assert rfq_two.json()["version"] == 2
    assert "TO BE CONFIRMED" in rfq_one.json()["rendered_markdown"]


def test_poe_percent_validation_and_transition_audit(
    client: TestClient, db_session: Session
) -> None:
    product, _ = _scored_product(db_session)
    project = client.post("/validation-projects", json={"product_id": str(product.id)}).json()
    project_id = project["id"]

    invalid = client.put(
        f"/validation-projects/{project_id}/poe-evidence",
        json={"conversion_rate_percent": 120},
    )
    valid = client.put(
        f"/validation-projects/{project_id}/poe-evidence",
        json={
            "niche_name": "camping bowls",
            "conversion_rate_percent": 12.5,
            "observed_at": datetime.now(UTC).isoformat(),
        },
    )
    invalid_transition = client.post(
        f"/validation-projects/{project_id}/transition",
        json={"to_status": "approved_for_sample", "reason": "Too early"},
    )
    valid_transition = client.post(
        f"/validation-projects/{project_id}/transition",
        json={"to_status": "marketplace_validation", "reason": "Begin review"},
    )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["source_type"] == "manual_poe"
    assert invalid_transition.status_code == 409
    assert valid_transition.status_code == 200
    assert valid_transition.json()["audit_history"][0]["actor"] == "local_user"


def test_quote_tier_economics_and_gate_override(client: TestClient, db_session: Session) -> None:
    product, _ = _scored_product(db_session)
    project_id = client.post("/validation-projects", json={"product_id": str(product.id)}).json()[
        "id"
    ]
    supplier = client.post(
        "/suppliers", json={"name": "Example Factory", "platform": "direct"}
    ).json()
    quote = client.post(
        f"/validation-projects/{project_id}/quotes",
        json={
            "supplier_id": supplier["id"],
            "status": "received",
            "moq": 200,
            "sample_cost": 35,
            "tooling_cost": 100,
            "packaging_cost_per_unit": 0.5,
            "labeling_cost_per_unit": 0.1,
            "production_lead_time_days": 30,
            "tiers": [
                {
                    "quantity": 200,
                    "unit_price": 3,
                    "freight_total": 200,
                    "duty_total": 100,
                    "inspection_total": 100,
                }
            ],
        },
    )
    assert quote.status_code == 201
    tier = quote.json()["tiers"][0]
    assert tier["economics"]["landed_cost_per_unit"] == 6.1
    assert tier["economics"]["inputs"]["expected_sale_price"]["source"].startswith(
        "validation_marketplace_packet_v"
    )
    gates = client.post(f"/validation-projects/{project_id}/gates/evaluate")
    assert gates.status_code == 200
    assert gates.json()["sourcing"]["status"] == "incomplete"
    override = client.post(
        f"/validation-projects/{project_id}/gates/sourcing/override",
        json={"reason": "Single supplier pilot approved"},
    )
    assert override.status_code == 200
    assert override.json()["status"] == "overridden"
    assert override.json()["override_reason"] == "Single supplier pilot approved"
