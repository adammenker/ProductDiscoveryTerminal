from __future__ import annotations

from datetime import datetime
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
    quote_status: Literal["raw", "parsed", "needs_review", "validated", "rejected", "expired"] | None = (
        None
    )
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
