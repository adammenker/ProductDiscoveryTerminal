from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.enums import ProductStatus
from app.models.mixins import CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.insight import ProductInsight
    from app.models.observation import RawObservation
    from app.models.score import OpportunityScore
    from app.models.signal import CostModel, MarketSignal, SupplierSignal
    from app.models.validation import (
        ConstraintEvaluation,
        OpportunitySnapshot,
        PaperTrade,
        SupplierQuote,
    )


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class ProductCandidate(TimestampMixin, Base):
    __tablename__ = "product_candidates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        SqlEnum(ProductStatus, values_callable=enum_values, native_enum=False, length=32),
        default=ProductStatus.CANDIDATE,
        nullable=False,
        index=True,
    )

    aliases: Mapped[list["ProductAlias"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    observations: Mapped[list["RawObservation"]] = relationship(back_populates="product")
    market_signals: Mapped[list["MarketSignal"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    supplier_signals: Mapped[list["SupplierSignal"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    cost_models: Mapped[list["CostModel"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list["ProductInsight"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    opportunity_scores: Mapped[list["OpportunityScore"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    supplier_quotes: Mapped[list["SupplierQuote"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    constraint_evaluations: Mapped[list["ConstraintEvaluation"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    opportunity_snapshots: Mapped[list["OpportunitySnapshot"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    paper_trades: Mapped[list["PaperTrade"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductAlias(CreatedAtMixin, Base):
    __tablename__ = "product_aliases"
    __table_args__ = (
        UniqueConstraint("product_id", "alias", name="uq_product_alias"),
        Index("ix_product_aliases_alias", "alias"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    product: Mapped[ProductCandidate] = relationship(back_populates="aliases")
