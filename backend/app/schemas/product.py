from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductListItem(BaseModel):
    id: str
    canonical_name: str
    category: str | None = None
    status: str
    latest_score: float | None = None
    recommendation: str | None = None
    demand_score: float | None = None
    growth_score: float | None = None
    competition_score: float | None = None
    margin_score: float | None = None
    pain_point_score: float | None = None
    risk_score: float | None = None
    confidence_score: float | None = None
    explanation: str | None = None
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

    model_config = ConfigDict(from_attributes=True)

