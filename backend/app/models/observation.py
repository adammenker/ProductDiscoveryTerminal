from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.enums import ObservationEntityType
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin
from app.models.product import enum_values

if TYPE_CHECKING:
    from app.models.plugin_run import PluginRun
    from app.models.product import ProductCandidate


class RawObservation(CreatedAtMixin, Base):
    __tablename__ = "raw_observations"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_raw_observations_content_hash"),
        Index("ix_raw_observations_source_entity", "source", "entity_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    plugin_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("plugin_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_plugin: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entity_type: Mapped[ObservationEntityType] = mapped_column(
        SqlEnum(ObservationEntityType, values_callable=enum_values, native_enum=False, length=48),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)
    media_urls: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    plugin_run: Mapped["PluginRun"] = relationship(back_populates="observations")
    product: Mapped["ProductCandidate | None"] = relationship(back_populates="observations")
