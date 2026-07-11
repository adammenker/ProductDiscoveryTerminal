from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import ProductCandidate


class SupplierQuote(TimestampMixin, Base):
    __tablename__ = "supplier_quotes"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(120), default="manual", nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    quote_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    freight_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    packaging_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    moq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    quote_status: Mapped[str] = mapped_column(String(32), default="needs_review", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="supplier_quotes")


class RuleProfile(TimestampMixin, Base):
    __tablename__ = "rule_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    hard_rules: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    soft_rules: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)


class ConstraintEvaluation(CreatedAtMixin, Base):
    __tablename__ = "constraint_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("rule_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hard_failures: Mapped[list] = mapped_column(json_type(), default=list, nullable=False)
    soft_warnings: Mapped[list] = mapped_column(json_type(), default=list, nullable=False)
    risk_flags: Mapped[list] = mapped_column(json_type(), default=list, nullable=False)
    constraint_score: Mapped[float] = mapped_column(Float, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    evaluation_version: Mapped[str] = mapped_column(String(80), default="risk_rules_v1", nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["ProductCandidate"] = relationship(back_populates="constraint_evaluations")
    rule_profile: Mapped[RuleProfile] = relationship()


class OpportunitySnapshot(CreatedAtMixin, Base):
    __tablename__ = "opportunity_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_reason: Mapped[str] = mapped_column(String(255), default="manual", nullable=False)
    discovery_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(48), nullable=True)
    component_scores: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    cost_ceiling: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    supplier_validation: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    constraint_evaluation: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    evidence_matrix: Mapped[list] = mapped_column(json_type(), default=list, nullable=False)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["ProductCandidate"] = relationship(back_populates="opportunity_snapshots")
    paper_trades: Mapped[list["PaperTrade"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )


class PaperTrade(CreatedAtMixin, Base):
    __tablename__ = "paper_trades"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("opportunity_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_windows: Mapped[list] = mapped_column(json_type(), default=lambda: [30, 60, 90], nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)

    product: Mapped["ProductCandidate"] = relationship(back_populates="paper_trades")
    snapshot: Mapped[OpportunitySnapshot] = relationship(back_populates="paper_trades")
    outcomes: Mapped[list["OutcomeMeasurement"]] = relationship(
        back_populates="paper_trade",
        cascade="all, delete-orphan",
    )


class OutcomeMeasurement(CreatedAtMixin, Base):
    __tablename__ = "outcome_measurements"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    paper_trade_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("paper_trades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    search_interest_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    seller_count_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    supplier_cost_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    constraint_status_change: Mapped[str | None] = mapped_column(String(120), nullable=True)
    outcome_label: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    outcome_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    paper_trade: Mapped[PaperTrade] = relationship(back_populates="outcomes")


class BacktestRun(CreatedAtMixin, Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filters: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    metrics: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
