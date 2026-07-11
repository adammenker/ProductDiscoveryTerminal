from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID
from app.models.json import json_type
from app.models.mixins import CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.observation import RawObservation
    from app.models.product import ProductCandidate
    from app.models.score import OpportunityScore


class SeedList(TimestampMixin, Base):
    __tablename__ = "seed_lists"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    keywords: Mapped[list["SeedKeyword"]] = relationship(
        back_populates="seed_list",
        cascade="all, delete-orphan",
    )
    discovery_runs: Mapped[list["DiscoveryRun"]] = relationship(back_populates="seed_list")


class SeedKeyword(TimestampMixin, Base):
    __tablename__ = "seed_keywords"
    __table_args__ = (
        UniqueConstraint("seed_list_id", "keyword", name="uq_seed_keywords_list_keyword"),
        Index("ix_seed_keywords_list_status", "seed_list_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    seed_list_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("seed_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    seed_list: Mapped[SeedList] = relationship(back_populates="keywords")


class DiscoveryRun(TimestampMixin, Base):
    __tablename__ = "discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    seed_list_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("seed_lists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_plugins: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    parameters: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    summary: Mapped[dict] = mapped_column(json_type(), default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    seed_list: Mapped[SeedList | None] = relationship(back_populates="discovery_runs")
    clusters: Mapped[list["CandidateCluster"]] = relationship(
        back_populates="discovery_run",
        cascade="all, delete-orphan",
    )
    results: Mapped[list["DiscoveryRunResult"]] = relationship(
        back_populates="discovery_run",
        cascade="all, delete-orphan",
    )
    origins: Mapped[list["CandidateOrigin"]] = relationship(
        back_populates="discovery_run",
        cascade="all, delete-orphan",
    )


class CandidateCluster(CreatedAtMixin, Base):
    __tablename__ = "candidate_clusters"
    __table_args__ = (
        UniqueConstraint(
            "discovery_run_id",
            "seed_keyword_id",
            "normalized_key",
            name="uq_candidate_clusters_run_seed_key",
        ),
        Index("ix_candidate_clusters_run", "discovery_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("discovery_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seed_keyword_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("seed_keywords.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_query: Mapped[str] = mapped_column(String(255), nullable=False)
    representative_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_observation_ids: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    discovery_run: Mapped[DiscoveryRun] = relationship(back_populates="clusters")


class DiscoveryRunResult(CreatedAtMixin, Base):
    __tablename__ = "discovery_run_results"
    __table_args__ = (
        UniqueConstraint(
            "discovery_run_id",
            "candidate_cluster_id",
            "product_id",
            name="uq_discovery_results_run_cluster_product",
        ),
        Index("ix_discovery_results_run_rank", "discovery_run_id", "rank_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("discovery_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seed_keyword_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("seed_keywords.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_cluster_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("candidate_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("opportunity_scores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False, index=True)
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(48), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    discovery_run: Mapped[DiscoveryRun] = relationship(back_populates="results")
    cluster: Mapped[CandidateCluster] = relationship()
    product: Mapped["ProductCandidate"] = relationship()
    score_snapshot: Mapped["OpportunityScore | None"] = relationship()


class CandidateOrigin(CreatedAtMixin, Base):
    __tablename__ = "candidate_origins"
    __table_args__ = (
        UniqueConstraint(
            "discovery_run_id",
            "seed_keyword_id",
            "product_id",
            "source_plugin",
            "source_external_id",
            name="uq_candidate_origins_source",
        ),
        Index("ix_candidate_origins_product", "product_id"),
        Index("ix_candidate_origins_run_seed", "discovery_run_id", "seed_keyword_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("product_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("discovery_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seed_keyword_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("seed_keywords.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("candidate_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_plugin: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_query: Mapped[str] = mapped_column(String(255), nullable=False)
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("raw_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_type(), default=dict, nullable=False)

    discovery_run: Mapped[DiscoveryRun] = relationship(back_populates="origins")
    cluster: Mapped[CandidateCluster | None] = relationship()
    product: Mapped["ProductCandidate"] = relationship()
    source_observation: Mapped["RawObservation | None"] = relationship()
