from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    canonical_name: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class SupplierQuoteCreate(BaseModel):
    source: str = "manual"
    supplier_name: str | None = None
    supplier_url: str | None = None
    quote_date: datetime | None = None
    unit_cost: float = Field(ge=0)
    freight_cost_per_unit: float | None = Field(default=None, ge=0)
    packaging_cost_per_unit: float | None = Field(default=None, ge=0)
    moq: int | None = Field(default=None, ge=1)
    lead_time_days: int | None = Field(default=None, ge=0)
    country: str | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    quote_status: Literal["raw", "parsed", "needs_review", "validated", "rejected", "expired"] = (
        "needs_review"
    )
    confidence: float = Field(default=0.6, ge=0, le=1)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupplierQuoteUpdate(BaseModel):
    supplier_name: str | None = None
    supplier_url: str | None = None
    quote_date: datetime | None = None
    unit_cost: float | None = Field(default=None, ge=0)
    freight_cost_per_unit: float | None = Field(default=None, ge=0)
    packaging_cost_per_unit: float | None = Field(default=None, ge=0)
    moq: int | None = Field(default=None, ge=1)
    lead_time_days: int | None = Field(default=None, ge=0)
    country: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    quote_status: (
        Literal["raw", "parsed", "needs_review", "validated", "rejected", "expired"] | None
    ) = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class SupplierTextImport(BaseModel):
    product_id: str
    source: str = "manual_paste"
    text: str = Field(min_length=3, max_length=10_000)


class RuleProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    is_default: bool = False
    hard_rules: dict[str, Any] = Field(default_factory=dict)
    soft_rules: dict[str, Any] = Field(default_factory=dict)


class RuleProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    is_default: bool | None = None
    hard_rules: dict[str, Any] | None = None
    soft_rules: dict[str, Any] | None = None


class SnapshotCreate(BaseModel):
    snapshot_reason: str = "manual"
    decision: Literal["paper_pursue", "paper_watch", "paper_skip"] | None = None
    hypothesis: str | None = None


class SnapshotTopRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=70, ge=0, le=100)
    decision: Literal["paper_pursue", "paper_watch", "paper_skip"] = "paper_pursue"


class PaperTradeCreate(BaseModel):
    product_id: str
    snapshot_id: str
    decision: Literal["paper_pursue", "paper_watch", "paper_skip"]
    hypothesis: str | None = None
    evaluation_windows: list[int] = Field(default_factory=lambda: [30, 60, 90])


class OutcomeCreate(BaseModel):
    window_days: int = Field(ge=1)
    measured_at: datetime | None = None
    price_change: float | None = None
    review_count_change: float | None = None
    rank_change: float | None = None
    search_interest_change: float | None = None
    seller_count_change: float | None = None
    supplier_cost_change: float | None = None
    constraint_status_change: str | None = None
    outcome_label: Literal[
        "improved",
        "flat",
        "deteriorated",
        "invalidated",
        "insufficient_data",
    ]
    outcome_score: float | None = Field(default=None, ge=-100, le=100)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationProjectCreate(BaseModel):
    product_id: str
    recommendation_snapshot_id: str | None = None
    source_discovery_run_id: str | None = None
    source_discovery_result_id: str | None = None
    title: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ValidationProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    notes: str | None = None


class ValidationTransitionCreate(BaseModel):
    to_status: Literal[
        "draft",
        "marketplace_validation",
        "sourcing",
        "ready_for_decision",
        "approved_for_sample",
        "rejected",
        "archived",
    ]
    reason: str = Field(min_length=2, max_length=2000)
    actor: str = Field(default="local_user", min_length=2, max_length=120)


class PoeEvidenceUpsert(BaseModel):
    niche_name: str | None = None
    reporting_period: str | None = None
    search_volume: int | None = Field(default=None, ge=0)
    search_volume_growth_percent: Decimal | None = Field(default=None, ge=-100, le=10000)
    product_count: int | None = Field(default=None, ge=0)
    average_price: Decimal | None = Field(default=None, ge=0)
    average_review_count: Decimal | None = Field(default=None, ge=0)
    conversion_rate_percent: Decimal | None = Field(default=None, ge=0, le=100)
    click_share_top_products_percent: Decimal | None = Field(default=None, ge=0, le=100)
    unmet_demand_notes: str | None = None
    source_url: str | None = None
    observed_at: datetime | None = None
    notes: str | None = None


class RfqUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    product_specification: dict[str, Any] | None = None
    requested_quantities: list[int] | None = None
    destination: dict[str, Any] | None = None
    required_certifications: list[str] | None = None
    questions: list[str] | None = None
    rendered_markdown: str | None = Field(default=None, min_length=2)


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    platform: Literal[
        "alibaba",
        "global_sources",
        "made_in_china",
        "importyeti",
        "direct",
        "sourcing_agent",
        "other",
    ] = "other"
    profile_url: str | None = None
    location: str | None = None
    contact_name: str | None = None
    contact_details: dict[str, Any] | None = None
    verified_status: str | None = None
    years_in_business: int | None = Field(default=None, ge=0)
    notes: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    platform: (
        Literal[
            "alibaba",
            "global_sources",
            "made_in_china",
            "importyeti",
            "direct",
            "sourcing_agent",
            "other",
        ]
        | None
    ) = None
    profile_url: str | None = None
    location: str | None = None
    contact_name: str | None = None
    contact_details: dict[str, Any] | None = None
    verified_status: str | None = None
    years_in_business: int | None = Field(default=None, ge=0)
    notes: str | None = None


class QuoteTierInput(BaseModel):
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0)
    freight_total: Decimal | None = Field(default=None, ge=0)
    duty_total: Decimal | None = Field(default=None, ge=0)
    inspection_total: Decimal | None = Field(default=None, ge=0)
    prep_total: Decimal | None = Field(default=None, ge=0)
    miscellaneous_total: Decimal | None = Field(default=None, ge=0)


class ValidationQuoteCreate(BaseModel):
    supplier_id: str
    rfq_id: str | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    incoterm: str | None = None
    moq: int | None = Field(default=None, ge=1)
    sample_cost: Decimal | None = Field(default=None, ge=0)
    tooling_cost: Decimal | None = Field(default=None, ge=0)
    packaging_cost_per_unit: Decimal | None = Field(default=None, ge=0)
    labeling_cost_per_unit: Decimal | None = Field(default=None, ge=0)
    production_lead_time_days: int | None = Field(default=None, ge=0)
    sample_lead_time_days: int | None = Field(default=None, ge=0)
    certification_notes: str | None = None
    payment_terms: str | None = None
    quote_valid_until: date | None = None
    status: Literal[
        "draft", "received", "clarification_needed", "shortlisted", "rejected", "expired"
    ] = "draft"
    notes: str | None = None
    tiers: list[QuoteTierInput] = Field(default_factory=list)


class ValidationQuoteUpdate(BaseModel):
    rfq_id: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    incoterm: str | None = None
    moq: int | None = Field(default=None, ge=1)
    sample_cost: Decimal | None = Field(default=None, ge=0)
    tooling_cost: Decimal | None = Field(default=None, ge=0)
    packaging_cost_per_unit: Decimal | None = Field(default=None, ge=0)
    labeling_cost_per_unit: Decimal | None = Field(default=None, ge=0)
    production_lead_time_days: int | None = Field(default=None, ge=0)
    sample_lead_time_days: int | None = Field(default=None, ge=0)
    certification_notes: str | None = None
    payment_terms: str | None = None
    quote_valid_until: date | None = None
    status: (
        Literal["draft", "received", "clarification_needed", "shortlisted", "rejected", "expired"]
        | None
    ) = None
    notes: str | None = None
    tiers: list[QuoteTierInput] | None = None


class GateOverrideCreate(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)
    actor: str = Field(default="local_user", min_length=2, max_length=120)
