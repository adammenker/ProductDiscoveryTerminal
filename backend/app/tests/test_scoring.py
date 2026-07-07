from __future__ import annotations

from app.models.enums import Recommendation
from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import PipelineRunRequest
from app.scoring.formulas import recommendation_for_score, weighted_final_score
from app.services.product_service import ProductService


def test_weighted_score_formula_penalizes_risk() -> None:
    score = weighted_final_score(
        {
            "demand_score": 80,
            "growth_score": 90,
            "margin_score": 70,
            "pain_point_score": 75,
            "competition_score": 65,
            "risk_score": 60,
        }
    )

    assert score == 57.75


def test_low_confidence_overrides_high_score() -> None:
    assert recommendation_for_score(88, 40) == Recommendation.NEEDS_MORE_DATA


def test_pipeline_scores_explainable_opportunity(db_session) -> None:  # type: ignore[no-untyped-def]
    PipelineRunner(db_session).run(PipelineRunRequest())
    items, total = ProductService(db_session).list_products(ranked=True)

    assert total == 7
    assert items[0]["canonical_name"] == "facial ice roller"
    assert items[0]["recommendation"] == "investigate"
    assert "recommendation" in items[0]["explanation"]

