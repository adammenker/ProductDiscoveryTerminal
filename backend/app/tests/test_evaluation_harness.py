from __future__ import annotations

import json

import pytest

from app.evaluation.harness import EvaluationHarness, console_summary, markdown_report
from app.models import (
    OpportunityScore,
    ProductCandidate,
    ProductStatus,
    Recommendation,
    RecommendationFeedback,
)
from app.schemas.product import RecommendationFeedbackCreate


def test_feedback_reasons_are_required_and_valid() -> None:
    with pytest.raises(ValueError, match="At least one feedback reason"):
        RecommendationFeedbackCreate(verdict="good_recommendation", reasons=[])

    with pytest.raises(ValueError, match="Unsupported feedback reason"):
        RecommendationFeedbackCreate(verdict="good_recommendation", reasons=["vibes"])

    payload = RecommendationFeedbackCreate(
        verdict="good_recommendation",
        reasons=["actually_interesting"],
    )
    assert payload.reasons == ["actually_interesting"]


def test_evaluation_harness_generates_reports(db_session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    interesting = ProductCandidate(
        canonical_name="travel cable organizer",
        category="travel accessories",
        status=ProductStatus.CANDIDATE,
    )
    unattractive = ProductCandidate(
        canonical_name="passport organizer wallet",
        category="travel accessories",
        status=ProductStatus.CANDIDATE,
    )
    db_session.add_all([interesting, unattractive])
    db_session.flush()
    db_session.add_all(
        [
            OpportunityScore(
                product_id=interesting.id,
                scoring_version="recommendation_v2",
                demand_score=0,
                growth_score=0,
                competition_score=0,
                margin_score=0,
                pain_point_score=0,
                risk_score=0,
                confidence_score=70,
                final_score=72,
                recommendation=Recommendation.INVESTIGATE,
                explanation="fixture",
                score_breakdown={},
            ),
            OpportunityScore(
                product_id=unattractive.id,
                scoring_version="recommendation_v2",
                demand_score=0,
                growth_score=0,
                competition_score=0,
                margin_score=0,
                pain_point_score=0,
                risk_score=0,
                confidence_score=80,
                final_score=88,
                recommendation=Recommendation.PURSUE,
                explanation="fixture",
                score_breakdown={},
            ),
            RecommendationFeedback(
                product_id=interesting.id,
                verdict="good_recommendation",
                reasons=["actually_interesting"],
            ),
            RecommendationFeedback(
                product_id=unattractive.id,
                verdict="bad_recommendation",
                reasons=["actually_unattractive", "wrong_comparables"],
            ),
        ]
    )
    db_session.commit()

    report = EvaluationHarness(db_session).run(k=1)

    assert report["summary"]["products_evaluated"] == 2
    assert report["summary"]["labeled_products"] == 2
    assert report["summary"]["precision_at_k"] == 0
    assert report["summary"]["ranking_agreement"] == 0
    assert report["false_positive_analysis"][0]["canonical_name"] == "passport organizer wallet"
    assert "precision@1=0" in console_summary(report)
    assert "False Positives" in markdown_report(report)

    paths = EvaluationHarness(db_session).write_reports(report, tmp_path)
    assert json.loads((tmp_path / "recommendation_v2_evaluation.json").read_text())["summary"]
    assert paths["markdown"].endswith(".md")
