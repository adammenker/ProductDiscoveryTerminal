from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import OpportunityScore
from app.scoring.config import SCORING_VERSION, SCORING_WEIGHTS
from app.scoring.formulas import (
    competition_score,
    confidence_score,
    demand_score,
    growth_score,
    margin_score,
    pain_point_score,
    recommendation_for_score,
    risk_score,
    weighted_final_score,
)
from app.services.product_service import ProductService


class ScoringService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.product_service = ProductService(db)

    def score_product(self, product_id: uuid.UUID | str) -> OpportunityScore:
        context = self.product_service.build_context(product_id)
        observations = context.observations
        market_signals = context.market_signals
        supplier_signals = context.supplier_signals
        cost_models = context.cost_models
        insights = context.insights

        components = {
            "demand_score": demand_score(observations, market_signals),
            "growth_score": growth_score(market_signals),
            "competition_score": competition_score(market_signals),
            "margin_score": margin_score(cost_models),
            "pain_point_score": pain_point_score(insights),
            "risk_score": risk_score(insights),
        }
        components["confidence_score"] = confidence_score(
            observations,
            market_signals,
            supplier_signals,
            cost_models,
            insights,
        )
        final_score = weighted_final_score(components)
        recommendation = recommendation_for_score(final_score, components["confidence_score"])
        explanation = self._explanation(context.canonical_name, components, final_score, recommendation.value)
        breakdown: dict[str, Any] = {
            "weights": SCORING_WEIGHTS,
            "signals": {
                "observations": len(observations),
                "sources": sorted({observation["source"] for observation in observations}),
                "market_signals": len(market_signals),
                "supplier_signals": len(supplier_signals),
                "cost_models": len(cost_models),
                "insights": len(insights),
            },
        }

        score = OpportunityScore(
            product_id=uuid.UUID(str(product_id)),
            scoring_version=SCORING_VERSION,
            demand_score=components["demand_score"],
            growth_score=components["growth_score"],
            competition_score=components["competition_score"],
            margin_score=components["margin_score"],
            pain_point_score=components["pain_point_score"],
            risk_score=components["risk_score"],
            confidence_score=components["confidence_score"],
            final_score=final_score,
            recommendation=recommendation,
            explanation=explanation,
            score_breakdown=breakdown,
        )
        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)
        return score

    def score_products(self, product_ids: list[uuid.UUID | str]) -> list[OpportunityScore]:
        return [self.score_product(product_id) for product_id in product_ids]

    @staticmethod
    def _explanation(
        product_name: str,
        components: dict[str, float],
        final_score: float,
        recommendation: str,
    ) -> str:
        risk_phrase = (
            "risk is elevated and needs careful validation"
            if components["risk_score"] >= 60
            else "risk appears manageable for an MVP investigation"
        )
        margin_phrase = (
            "unit economics look attractive"
            if components["margin_score"] >= 70
            else "unit economics need more validation"
        )
        pain_phrase = (
            "customer pain is repeated and suggests a differentiation angle"
            if components["pain_point_score"] >= 75
            else "customer pain evidence is still thin"
        )
        return (
            f"{product_name} scores {final_score:.1f} with a {recommendation} recommendation. "
            f"Demand and growth inputs score {components['demand_score']:.0f}/"
            f"{components['growth_score']:.0f}, {margin_phrase}, and {pain_phrase}. "
            f"Competition attractiveness is {components['competition_score']:.0f}, while {risk_phrase}. "
            f"Confidence is {components['confidence_score']:.0f} based on available source coverage."
        )

