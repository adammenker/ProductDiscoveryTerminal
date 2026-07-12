from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import ProductCandidate


class ProductValidationProject(TimestampMixin, Base):
    __tablename__ = "product_validation_projects"
    __table_args__ = (
        Index("ix_validation_projects_product_status", "product_id", "status"),
        Index("ix_validation_projects_recommendation", "source_recommendation_snapshot_id"),
        UniqueConstraint(
            "product_id",
            "source_recommendation_snapshot_id",
            name="uq_validation_project_product_recommendation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("product_candidates.id", ondelete="CASCADE"), nullable=False
    )
    source_discovery_run_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True
    )
    source_discovery_result_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("discovery_run_results.id", ondelete="SET NULL"), nullable=True
    )
    source_recommendation_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("opportunity_scores.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["ProductCandidate"] = relationship()
    packets: Mapped[list["ValidationMarketplacePacket"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    transitions: Mapped[list["ValidationTransition"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    poe_evidence: Mapped["ValidationPoeEvidence | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    rfqs: Mapped[list["ValidationRfq"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    quotes: Mapped[list["ValidationSupplierQuote"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    gates: Mapped[list["ValidationGateEvaluation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ValidationTransition(CreatedAtMixin, Base):
    __tablename__ = "validation_transitions"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_validation_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(120), default="local_user", nullable=False)
    project: Mapped[ProductValidationProject] = relationship(back_populates="transitions")


class ValidationMarketplacePacket(CreatedAtMixin, Base):
    __tablename__ = "validation_marketplace_packets"
    __table_args__ = (
        UniqueConstraint("validation_project_id", "version", name="uq_validation_packet_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_validation_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("opportunity_scores.id", ondelete="RESTRICT"), nullable=False
    )
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    research_priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amazon_fees_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_landed_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    effective_comparable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comparable_asins: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    comparable_details: Mapped[list] = mapped_column(json_type(), default=list, nullable=False)
    demand_summary: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    competition_summary: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    economics_summary: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    risk_summary: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    missing_evidence: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    conflicting_evidence: Mapped[list[str]] = mapped_column(
        json_type(), default=list, nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    project: Mapped[ProductValidationProject] = relationship(back_populates="packets")


class ValidationPoeEvidence(TimestampMixin, Base):
    __tablename__ = "validation_poe_evidence"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_validation_projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    niche_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporting_period: Mapped[str | None] = mapped_column(String(120), nullable=True)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_volume_growth_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    product_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    average_review_count: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    conversion_rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    click_share_top_products_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    unmet_demand_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project: Mapped[ProductValidationProject] = relationship(back_populates="poe_evidence")


class ValidationRfq(TimestampMixin, Base):
    __tablename__ = "validation_rfqs"
    __table_args__ = (
        UniqueConstraint("validation_project_id", "version", name="uq_validation_rfq_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_validation_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    product_specification: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    requested_quantities: Mapped[list[int]] = mapped_column(
        json_type(), default=lambda: [200, 500, 1000], nullable=False
    )
    destination: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    required_certifications: Mapped[list[str]] = mapped_column(
        json_type(), default=list, nullable=False
    )
    questions: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    rendered_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[ProductValidationProject] = relationship(back_populates="rfqs")


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), default="other", nullable=False)
    profile_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_details: Mapped[dict | None] = mapped_column(json_type(), nullable=True)
    verified_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    years_in_business: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ValidationSupplierQuote(TimestampMixin, Base):
    __tablename__ = "validation_supplier_quotes"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_validation_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("validation_rfqs.id", ondelete="SET NULL"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    incoterm: Mapped[str | None] = mapped_column(String(32), nullable=True)
    moq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tooling_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    packaging_cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    labeling_cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    production_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project: Mapped[ProductValidationProject] = relationship(back_populates="quotes")
    supplier: Mapped[Supplier] = relationship()
    rfq: Mapped[ValidationRfq | None] = relationship()
    tiers: Mapped[list["SupplierQuoteTier"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class SupplierQuoteTier(CreatedAtMixin, Base):
    __tablename__ = "supplier_quote_tiers"
    __table_args__ = (
        UniqueConstraint("supplier_quote_id", "quantity", name="uq_supplier_quote_tier_quantity"),
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    supplier_quote_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("validation_supplier_quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    freight_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    duty_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    inspection_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    prep_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    miscellaneous_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    quote: Mapped[ValidationSupplierQuote] = relationship(back_populates="tiers")


class ValidationGateEvaluation(CreatedAtMixin, Base):
    __tablename__ = "validation_gate_evaluations"
    __table_args__ = (
        Index(
            "ix_validation_gate_project_name_created",
            "validation_project_id",
            "gate_name",
            "created_at",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_validation_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    gate_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    missing_inputs: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    rule_version: Mapped[str] = mapped_column(
        String(80), default="validation_gates_v1", nullable=False
    )
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    project: Mapped[ProductValidationProject] = relationship(back_populates="gates")


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
    evaluation_version: Mapped[str] = mapped_column(
        String(80), default="risk_rules_v1", nullable=False
    )
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
    evaluation_windows: Mapped[list] = mapped_column(
        json_type(), default=lambda: [30, 60, 90], nullable=False
    )
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
