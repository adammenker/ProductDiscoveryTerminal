from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import OpportunityScore, Recommendation
from app.scoring.config import SCORING_VERSION
from app.scoring.formulas import growth_score, pain_point_score
from app.scoring.v2 import build_recommendation_v2
from app.services.comparable_service import ComparableService
from app.services.product_service import ProductService
from app.services.validation_service import ValidationService


class ScoringService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.product_service = ProductService(db)

    def score_product(self, product_id: uuid.UUID | str) -> OpportunityScore:
        comparable_service = ComparableService(self.db)
        comparable_service.sync_product(product_id)
        context = self.product_service.build_context(product_id)
        observations = context.observations
        market_signals = context.market_signals
        supplier_signals = context.supplier_signals
        cost_models = context.cost_models
        insights = context.insights

        validation_service = ValidationService(self.db)
        economics = validation_service.economics(product_id)
        supplier_validation = validation_service.supplier_validation(product_id)
        constraint_evaluation = validation_service.latest_constraint(product_id)
        evidence = validation_service.evidence_matrix(product_id)
        comparable_rows = [
            comparable_service.to_dict(row, economics.get("comparable_asin"))
            for row in comparable_service.list_comparables(product_id, sync=False)
        ]
        derived_signals = comparable_service.derived_signals(product_id)
        recommendation_v2 = build_recommendation_v2(
            product_name=context.canonical_name,
            observations=observations,
            market_signals=market_signals,
            cost_models=cost_models,
            insights=insights,
            economics=economics,
            supplier_validation=supplier_validation,
            constraint_evaluation=constraint_evaluation,
            evidence=evidence,
            comparable_rows=comparable_rows,
            derived_signals=derived_signals,
        )
        components = recommendation_v2["components"]
        final_score = recommendation_v2["opportunity_score"] or 0.0
        recommendation = Recommendation(recommendation_v2["recommendation"])
        explanation = recommendation_v2["explanation"]
        breakdown: dict[str, Any] = {
            **recommendation_v2,
            "signals": {
                "observations": len(observations),
                "sources": sorted({observation["source"] for observation in observations}),
                "market_signals": len(market_signals),
                "supplier_signals": len(supplier_signals),
                "cost_models": len(cost_models),
                "insights": len(insights),
            },
            "validation": {
                "economics_decision": economics.get("decision"),
                "supplier_validation_score": supplier_validation["supplier_validation_score"],
                "constraint_eligible": constraint_evaluation["eligible"],
                "cross_source_confidence_score": evidence["cross_source_confidence_score"],
                "missing_evidence": evidence["missing_evidence"],
            },
        }
        demand_proxy = _component_value(components, "demand_proxy")
        competition = _component_value(components, "competition")
        economics_score = _component_value(components, "economics")
        risk_safety = _component_value(components, "risk")
        confidence = float(recommendation_v2["evidence_confidence_score"])

        score = OpportunityScore(
            product_id=uuid.UUID(str(product_id)),
            scoring_version=SCORING_VERSION,
            demand_score=demand_proxy or 0.0,
            growth_score=growth_score(market_signals),
            competition_score=competition or 0.0,
            margin_score=economics_score or 0.0,
            pain_point_score=pain_point_score(insights),
            risk_score=(100 - risk_safety) if risk_safety is not None else 0.0,
            confidence_score=confidence,
            final_score=final_score,
            recommendation=recommendation,
            explanation=explanation,
            score_breakdown=breakdown,
            created_at=datetime.now(UTC),
        )
        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)
        return score

    def score_products(self, product_ids: list[uuid.UUID | str]) -> list[OpportunityScore]:
        return [self.score_product(product_id) for product_id in product_ids]


def _component_value(components: dict[str, dict[str, Any]], name: str) -> float | None:
    value = (components.get(name) or {}).get("value")
    return float(value) if value is not None else None
