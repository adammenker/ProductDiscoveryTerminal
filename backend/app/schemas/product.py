from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

FEEDBACK_REASONS = {
    "wrong_comparables",
    "demand_overstated",
    "demand_understated",
    "competition_overstated",
    "competition_understated",
    "bad_price_estimate",
    "bad_fee_estimate",
    "missing_risk",
    "missing_data_mishandled",
    "actually_interesting",
    "actually_unattractive",
    "other",
}


class ProductListItem(BaseModel):
    id: str
    canonical_name: str
    category: str | None = None
    status: str
    latest_score: float | None = None
    recommendation: str | None = None
    opportunity_score: float | None = None
    evidence_confidence_score: float | None = None
    validation_readiness_score: float | None = None
    scoring_version: str | None = None
    demand_score: float | None = None
    demand_proxy_score: float | None = None
    growth_score: float | None = None
    competition_score: float | None = None
    margin_score: float | None = None
    pain_point_score: float | None = None
    risk_score: float | None = None
    confidence_score: float | None = None
    explanation: str | None = None
    economics_decision: str | None = None
    supplier_validation_decision: str | None = None
    constraint_eligible: bool | None = None
    cross_source_confidence_score: float | None = None
    validation_decision: str | None = None
    missing_evidence: list[str] = Field(default_factory=list)
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductListItem]
    total: int


class ProductDetailResponse(BaseModel):
    product: dict[str, Any]
    aliases: list[dict[str, Any]] = Field(default_factory=list)
    latest_score: dict[str, Any] | None = None
    market_signals: list[dict[str, Any]] = Field(default_factory=list)
    supplier_signals: list[dict[str, Any]] = Field(default_factory=list)
    cost_models: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    recent_observations: list[dict[str, Any]] = Field(default_factory=list)
    discovery_source: dict[str, Any] = Field(default_factory=dict)
    comparable_asins: list[dict[str, Any]] = Field(default_factory=list)
    effective_comparables: list[dict[str, Any]] = Field(default_factory=list)
    comparable_summary: dict[str, Any] = Field(default_factory=dict)
    historical_summary: dict[str, Any] = Field(default_factory=dict)
    historical_signals: dict[str, Any] = Field(default_factory=dict)
    marketplace_history: list[dict[str, Any]] = Field(default_factory=list)
    economics_validator: dict[str, Any] = Field(default_factory=dict)
    supplier_validation: dict[str, Any] = Field(default_factory=dict)
    constraint_evaluation: dict[str, Any] = Field(default_factory=dict)
    evidence_matrix: list[dict[str, Any]] = Field(default_factory=list)
    cross_source_confidence_score: float = 0
    missing_evidence: list[str] = Field(default_factory=list)
    validation_decision: dict[str, Any] = Field(default_factory=dict)
    recommendation_v2: dict[str, Any] = Field(default_factory=dict)
    paper_trading_history: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ComparableAsinUpdate(BaseModel):
    relevance_status: str
    reason: str | None = None


class RecommendationFeedbackCreate(BaseModel):
    verdict: str
    reasons: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("reasons")
    @classmethod
    def reasons_are_required(cls, value: list[str]) -> list[str]:
        cleaned = [reason.strip() for reason in value if reason.strip()]
        if not cleaned:
            raise ValueError("At least one feedback reason is required.")
        unknown = sorted(set(cleaned) - FEEDBACK_REASONS)
        if unknown:
            raise ValueError(f"Unsupported feedback reason(s): {', '.join(unknown)}")
        return cleaned
