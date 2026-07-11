from __future__ import annotations

SCORING_VERSION = "recommendation_v2"

RECOMMENDATION_V2_THRESHOLDS = {
    "minimum_opportunity_coverage": 50,
    "minimum_investigate_confidence": 40,
    "minimum_pursue_confidence": 70,
    "minimum_pursue_readiness": 80,
    "investigate_score": 70,
    "watch_score": 45,
}

RECOMMENDATION_V2_WEIGHTS = {
    "demand_proxy": 0.30,
    "competition": 0.30,
    "economics": 0.25,
    "risk": 0.15,
}

EVIDENCE_CONFIDENCE_WEIGHTS = {
    "evidence_coverage": 0.25,
    "comparable_relevance": 0.20,
    "freshness": 0.20,
    "historical_depth": 0.15,
    "source_independence": 0.10,
    "internal_consistency": 0.10,
}

READINESS_WEIGHTS = {
    "relevant_comparables": 0.20,
    "price_data": 0.10,
    "fee_data": 0.10,
    "constraints_evaluated": 0.10,
    "risk_evaluated": 0.10,
    "historical_data": 0.15,
    "direct_demand_data": 0.10,
    "supplier_validation": 0.15,
}

SCORING_WEIGHTS = {
    "demand": 0.25,
    "growth": 0.20,
    "margin": 0.20,
    "pain_point": 0.15,
    "competition": 0.10,
    "risk": -0.20,
}
