from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.enums import Recommendation
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin
from app.models.product import enum_values

if TYPE_CHECKING:
    from app.models.product import ProductCandidate


class OpportunityScore(CreatedAtMixin, Base):
    __tablename__ = "opportunity_scores"
    __table_args__ = (
        Index("ix_opportunity_scores_product_created", "product_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    demand_score: Mapped[float] = mapped_column(Float, nullable=False)
    growth_score: Mapped[float] = mapped_column(Float, nullable=False)
    competition_score: Mapped[float] = mapped_column(Float, nullable=False)
    margin_score: Mapped[float] = mapped_column(Float, nullable=False)
    pain_point_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    recommendation: Mapped[Recommendation] = mapped_column(
        SqlEnum(Recommendation, values_callable=enum_values, native_enum=False, length=48),
        nullable=False,
        index=True,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)

    product: Mapped["ProductCandidate"] = relationship(back_populates="opportunity_scores")
