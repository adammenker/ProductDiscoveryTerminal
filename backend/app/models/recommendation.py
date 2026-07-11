from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import ProductCandidate
    from app.models.score import OpportunityScore


class ComparableAsin(TimestampMixin, Base):
    __tablename__ = "comparable_asins"
    __table_args__ = (
        UniqueConstraint("product_id", "asin", name="uq_comparable_asins_product_asin"),
        Index("ix_comparable_asins_product_status", "product_id", "relevance_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asin: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    seed_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amazon_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amazon_product_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    dimensions: Mapped[dict | None] = mapped_column(json_type(), nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relevance_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relevance_reasons: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    automatic_relevance_version: Mapped[str] = mapped_column(String(80), nullable=False)
    manually_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manual_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_from_query: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="comparable_asins")
    snapshots: Mapped[list["MarketplaceAsinSnapshot"]] = relationship(
        back_populates="comparable_asin",
        cascade="all, delete-orphan",
    )


class MarketplaceAsinSnapshot(CreatedAtMixin, Base):
    __tablename__ = "marketplace_asin_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "comparable_asin_id",
            "snapshot_cohort_id",
            name="uq_marketplace_snapshot_product_comparable_cohort",
        ),
        Index("ix_marketplace_asin_snapshots_product_observed", "product_id", "observed_at"),
        Index("ix_marketplace_asin_snapshots_asin_observed", "asin", "observed_at"),
        Index("ix_marketplace_asin_snapshots_product_cohort", "product_id", "snapshot_cohort_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comparable_asin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("comparable_asins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    snapshot_cohort_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    observation_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    asin: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    featured_offer_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    lowest_offer_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    offer_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    seller_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    bestseller_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
    bestseller_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rank_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    browse_node: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rank_classification: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    fulfillment_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    referral_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_observation_ids: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="marketplace_snapshots")
    comparable_asin: Mapped["ComparableAsin | None"] = relationship(back_populates="snapshots")


class RecommendationFeedback(CreatedAtMixin, Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("opportunity_scores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verdict: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reasons: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["ProductCandidate"] = relationship(back_populates="recommendation_feedback")
    recommendation_snapshot: Mapped["OpportunityScore | None"] = relationship()
