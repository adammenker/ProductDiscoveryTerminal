from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.enums import MarketSignalType
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin
from app.models.product import enum_values

if TYPE_CHECKING:
    from app.models.product import ProductCandidate


class MarketSignal(CreatedAtMixin, Base):
    __tablename__ = "market_signals"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    signal_type: Mapped[MarketSignalType] = mapped_column(
        SqlEnum(MarketSignalType, values_callable=enum_values, native_enum=False, length=48),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="market_signals")


class SupplierSignal(CreatedAtMixin, Base):
    __tablename__ = "supplier_signals"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    moq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shipping_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="supplier_signals")


class CostModel(CreatedAtMixin, Base):
    __tablename__ = "cost_models"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    freight_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    packaging_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    fulfillment_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    marketplace_fee_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_net_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    assumptions: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="cost_models")
