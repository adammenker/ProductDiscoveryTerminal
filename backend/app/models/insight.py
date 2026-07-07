from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.enums import InsightType
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin
from app.models.product import enum_values

if TYPE_CHECKING:
    from app.models.product import ProductCandidate


class ProductInsight(CreatedAtMixin, Base):
    __tablename__ = "product_insights"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_type: Mapped[InsightType] = mapped_column(
        SqlEnum(InsightType, values_callable=enum_values, native_enum=False, length=48),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    evidence_observation_ids: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="insights")
