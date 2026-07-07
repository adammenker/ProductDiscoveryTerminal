from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.enums import PluginType, RunStatus
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin
from app.models.product import enum_values

if TYPE_CHECKING:
    from app.models.observation import RawObservation


class PluginRun(CreatedAtMixin, Base):
    __tablename__ = "plugin_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    plugin_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    plugin_type: Mapped[PluginType] = mapped_column(
        SqlEnum(PluginType, values_callable=enum_values, native_enum=False, length=24),
        nullable=False,
        index=True,
    )
    status: Mapped[RunStatus] = mapped_column(
        SqlEnum(RunStatus, values_callable=enum_values, native_enum=False, length=32),
        default=RunStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)

    observations: Mapped[list["RawObservation"]] = relationship(back_populates="plugin_run")
